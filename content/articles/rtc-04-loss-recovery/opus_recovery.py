#!/usr/bin/env python3
"""Real libopus PLC/FEC demonstration for RTC 04. Python 3.9+.

Requires a shared libopus exporting opus_packet_has_lbrr (verified with 1.6.1).
No third-party Python packages, microphone, playback or network are used.
The next packet is already present in memory; this does not test arrival time.
"""

import argparse
import csv
import ctypes as C
from ctypes.util import find_library
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import struct
import sys
import wave

RATE = 16000
FRAME = 320
BLOCKS = 100
I16 = C.c_int16
U8 = C.c_ubyte


class Opus:
    def __init__(self, name):
        self.lib = C.CDLL(name)
        signatures = {
            "opus_get_version_string": ([], C.c_char_p),
            "opus_strerror": ([C.c_int], C.c_char_p),
            "opus_encoder_create": ([C.c_int32, C.c_int, C.c_int, C.POINTER(C.c_int)], C.c_void_p),
            "opus_encoder_destroy": ([C.c_void_p], None),
            "opus_encode": ([C.c_void_p, C.POINTER(I16), C.c_int, C.POINTER(U8), C.c_int32], C.c_int32),
            "opus_decoder_create": ([C.c_int32, C.c_int, C.POINTER(C.c_int)], C.c_void_p),
            "opus_decoder_destroy": ([C.c_void_p], None),
            "opus_decode": ([C.c_void_p, C.POINTER(U8), C.c_int32, C.POINTER(I16), C.c_int, C.c_int], C.c_int),
            "opus_packet_has_lbrr": ([C.POINTER(U8), C.c_int32], C.c_int),
        }
        try:
            for function, (arguments, result) in signatures.items():
                entry = getattr(self.lib, function)
                entry.argtypes, entry.restype = arguments, result
        except AttributeError as error:
            raise RuntimeError("libopus lacks a required API; use a build with opus_packet_has_lbrr") from error
        # The two fixed arguments of this variadic function must be declared,
        # including on Apple arm64; each following integer is explicitly typed.
        self.lib.opus_encoder_ctl.argtypes = [C.c_void_p, C.c_int]
        self.lib.opus_encoder_ctl.restype = C.c_int

    def check(self, result):
        if result < 0:
            message = self.lib.opus_strerror(result).decode()
            raise RuntimeError(f"libopus: {message} ({result})")
        return result

    def encode(self, samples, fec):
        error = C.c_int()
        encoder = self.lib.opus_encoder_create(RATE, 1, 2048, C.byref(error))
        self.check(error.value)
        if not encoder:
            raise RuntimeError("encoder allocation failed")
        packets = []
        try:
            # Requests and values are from the public opus_defines.h API:
            # bitrate, VOICE hint, max WIDEBAND, complexity, DTX, expected loss,
            # and in-band FEC. Expected loss does not drop any packets here.
            settings = [(4002, 24000), (4024, 3001), (4004, 1103),
                        (4010, 5), (4016, 0), (4014, 20), (4012, int(fec))]
            for request, value in settings:
                self.check(self.lib.opus_encoder_ctl(encoder, request, C.c_int(value)))
            for start in range(0, len(samples), FRAME):
                pcm = (I16 * FRAME)(*samples[start:start + FRAME])
                output = (U8 * 4000)()
                count = self.check(self.lib.opus_encode(encoder, pcm, FRAME, output, len(output)))
                packets.append(bytes(output[:count]))
        finally:
            self.lib.opus_encoder_destroy(encoder)
        return packets

    def has_lbrr(self, packet):
        data = (U8 * len(packet)).from_buffer_copy(packet)
        return self.check(self.lib.opus_packet_has_lbrr(data, len(packet)))

    def decode_path(self, packets, loss_index, mode):
        error = C.c_int()
        decoder = self.lib.opus_decoder_create(RATE, 1, C.byref(error))
        self.check(error.value)
        if not decoder:
            raise RuntimeError("decoder allocation failed")
        blocks, rows = [], []
        try:
            for index, packet in enumerate(packets):
                source_index, decode_fec, action = index, 0, "normal"
                lbrr = self.has_lbrr(packet)
                if index == loss_index and mode == "plc":
                    packet, source_index, lbrr, action = None, -1, 0, "plc"
                elif index == loss_index and mode == "fec_request":
                    source_index, decode_fec = index + 1, 1
                    packet = packets[source_index]
                    lbrr = self.has_lbrr(packet)
                    action = "fec_from_next" if lbrr else "fec_request_plc_fallback"
                data = (U8 * len(packet)).from_buffer_copy(packet) if packet else None
                output = (I16 * FRAME)()
                count = self.check(self.lib.opus_decode(
                    decoder, data, len(packet) if packet else 0, output, FRAME, decode_fec))
                if count != FRAME:
                    raise RuntimeError(f"expected {FRAME} samples, got {count}")
                blocks.append(struct.pack(f"<{count}h", *output[:count]))
                rows.append([mode, index, source_index, len(packet) if packet else 0, action, count, lbrr])
                # On the NEXT iteration, packet loss_index+1 is decoded normally
                # with this SAME state: its own audio has not been played yet.
        finally:
            self.lib.opus_decoder_destroy(decoder)
        return b"".join(blocks), rows


def synthetic_samples():
    samples, phase = [], 0.0
    for index in range(RATE * 2):
        t = index / RATE
        phase += 2 * math.pi * (120 + 25 * math.sin(2 * math.pi * 1.3 * t)) / RATE
        envelope = 0.55 + 0.35 * math.sin(2 * math.pi * 2.1 * t) ** 2
        value = round(envelope * (7000 * math.sin(phase) + 2200 * math.sin(2 * phase)
                                  + 900 * math.sin(3 * phase)))
        samples.append(value)
    return samples


def write_wav(path, pcm):
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(pcm)


def discover_library():
    name = find_library("opus")
    if name:
        return name
    # Some Python builds do not search a package manager's library directory.
    # pkg-config is optional; --opus-library works without it.
    if shutil.which("pkg-config"):
        result = subprocess.run(["pkg-config", "--variable=libdir", "opus"],
                                capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            folder = Path(result.stdout.strip())
            for filename in ["libopus.dylib", "libopus.so", "opus.dll", "libopus-0.dll"]:
                candidate = folder / filename
                if candidate.is_file():
                    return str(candidate)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("opus-recovery"))
    parser.add_argument("--opus-library", help="explicit shared-library path if discovery fails")
    parser.add_argument("--loss-index", type=int, default=12)
    parser.add_argument("--disable-fec", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.loss_index < BLOCKS - 1:
        parser.error("loss-index must be 0..98; a following packet is required")
    name = args.opus_library or discover_library()
    if not name:
        parser.error("shared libopus not found; install it or supply --opus-library")
    try:
        opus = Opus(name)
    except (OSError, RuntimeError) as error:
        parser.error(str(error))
    try:
        args.output_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("output directory exists; choose a new --output-dir")

    samples = synthetic_samples()
    pcm = struct.pack(f"<{len(samples)}h", *samples)
    packets = opus.encode(samples, not args.disable_fec)
    reference = opus.encode(samples, False)
    streams, rows = {}, []
    for mode in ["normal", "plc", "fec_request"]:
        streams[mode], path_rows = opus.decode_path(packets, args.loss_index, mode)
        rows.extend(path_rows)
        if len(streams[mode]) != len(pcm):
            raise RuntimeError("decoded duration mismatch")
        write_wav(args.output_dir / (mode + ".wav"), streams[mode])
    write_wav(args.output_dir / "input.wav", pcm)
    with (args.output_dir / "frames.csv").open("x", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["path", "block_index", "input_packet_index", "input_bytes", "action",
                         "samples_per_channel", "input_has_lbrr"])
        writer.writerows(rows)
    start, end = args.loss_index * FRAME * 2, (args.loss_index + 1) * FRAME * 2
    lbrr = opus.has_lbrr(packets[args.loss_index + 1])
    equal = streams["fec_request"][start:end] == streams["plc"][start:end]
    report = {
        "scope": "one local missing packet; next packet already in memory; no timing or quality test",
        "runtime_version": opus.lib.opus_get_version_string().decode(),
        "python": platform.python_version(), "platform": platform.system(),
        "machine": platform.machine(), "sample_rate_hz": RATE, "channels": 1,
        "frame_samples": FRAME, "frames": BLOCKS, "loss_index": args.loss_index,
        "settings": {"target_bitrate_bit_s": 24000, "application": "VOIP",
                     "complexity": 5, "signal": "VOICE", "max_bandwidth": "WIDEBAND",
                     "dtx": False, "expected_loss_percent": 20,
                     "inband_fec": not args.disable_fec},
        "selected_stream_bytes": sum(map(len, packets)),
        "fec_disabled_reference_bytes": sum(map(len, reference)),
        "next_packet_has_lbrr": lbrr, "missing_fec_equals_plc": equal,
        "input_sha256": hashlib.sha256(pcm).hexdigest(),
        "outputs": {key: {"samples_per_channel": len(data) // 2,
                          "sha256": hashlib.sha256(data).hexdigest()}
                    for key, data in streams.items()},
    }
    (args.output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Runtime: {report['runtime_version']}")
    print(f"Encoder FEC enabled: {not args.disable_fec}")
    print(f"Selected stream: {report['selected_stream_bytes']} bytes; "
          f"FEC-disabled reference: {report['fec_disabled_reference_bytes']} bytes")
    print(f"Packet {args.loss_index + 1} has LBRR: {lbrr}")
    print("Missing-block action: " + ("fec_from_next" if lbrr else "fec_request_plc_fallback"))
    print(f"All paths: {len(pcm) // 2} samples/channel")
    print(f"Missing block FEC-request equals PLC: {equal}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
