#!/usr/bin/env python3
"""Generate and inspect synthetic audio for RTC 02. Python 3.9+.

PCM generation requires only the standard library. Optional --with-opus needs
ffmpeg (with libopus) and ffprobe on PATH. Files go to a new directory; existing
directories are refused. This program never records or plays audio.
"""

import argparse
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import wave

SAMPLE_RATE = 48000
CHANNELS = 1
SAMPLE_WIDTH = 2
DURATION_SECONDS = 1
FREQUENCY_HZ = 880
AMPLITUDE = 12000


def make_pcm():
    count = SAMPLE_RATE * DURATION_SECONDS
    samples = [round(AMPLITUDE * math.sin(2 * math.pi * FREQUENCY_HZ * n / SAMPLE_RATE))
               for n in range(count)]
    return struct.pack(f"<{count}h", *samples)


def write_wav(path, pcm, sample_rate=SAMPLE_RATE):
    with wave.open(str(path), "wb") as output:
        output.setnchannels(CHANNELS)
        output.setsampwidth(SAMPLE_WIDTH)
        output.setframerate(sample_rate)
        output.writeframes(pcm)


def read_wav(path):
    with wave.open(str(path), "rb") as source:
        channels = source.getnchannels()
        width = source.getsampwidth()
        rate = source.getframerate()
        count = source.getnframes()
        pcm = source.readframes(count)
    return channels, width, rate, count, pcm


def run(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "external command failed")
    return result.stdout


def encode_and_inspect(folder, original_pcm, ffmpeg, ffprobe):
    original = folder / "tone.wav"
    encoded = folder / "tone.opus"
    decoded = folder / "decoded.wav"
    print("\n" + run([ffmpeg, "-version"]).splitlines()[0])
    run([ffmpeg, "-hide_banner", "-loglevel", "error", "-n", "-i", str(original),
         "-c:a", "libopus", "-b:a", "32k", "-vbr", "off", "-frame_duration", "20",
         str(encoded)])
    packets = json.loads(run([
        ffprobe, "-v", "error", "-select_streams", "a:0", "-show_packets",
        "-show_entries", "packet=size,duration_time", "-of", "json", str(encoded)
    ]))["packets"]
    sizes = [int(packet["size"]) for packet in packets]
    print(f"Opus audio packets: {len(sizes)}; sizes: {sorted(set(sizes))} bytes")
    print(f"Opus audio payload total: {sum(sizes)} bytes")
    print(f"Ogg Opus file total: {encoded.stat().st_size} bytes")
    run([ffmpeg, "-hide_banner", "-loglevel", "error", "-n", "-i", str(encoded),
         "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1", str(decoded)])
    channels, width, rate, count, decoded_pcm = read_wav(decoded)
    if (channels, width, rate, count) != (1, 2, 48000, 48000):
        raise RuntimeError("unexpected decoded format or sample count")
    print(f"Decoded PCM: {count} samples/channel; {len(decoded_pcm)} bytes")
    print(f"PCM byte-identical: {original_pcm == decoded_pcm}")
    before = struct.unpack("<8h", original_pcm[:16])
    after = struct.unpack("<8h", decoded_pcm[:16])
    print(f"First 8 original samples: {before}")
    print(f"First 8 decoded samples:  {after}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("audio-lab"))
    parser.add_argument("--with-opus", action="store_true")
    args = parser.parse_args()
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if args.with_opus and (not ffmpeg or not ffprobe):
        parser.error("--with-opus requires ffmpeg and ffprobe on PATH")
    try:
        args.output_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("output directory already exists; choose a new --output-dir")
    pcm = make_pcm()
    path = args.output_dir / "tone.wav"
    write_wav(path, pcm)
    _, _, _, count, saved_pcm = read_wav(path)
    if saved_pcm != pcm:
        raise RuntimeError("PCM did not survive the WAV write/read")
    print(f"PCM: {SAMPLE_RATE} Hz; mono; 16-bit; {count} samples/channel")
    print(f"PCM data: {len(saved_pcm)} bytes; WAV file: {path.stat().st_size} bytes")
    wrong_rate = args.output_dir / "wrong-rate.wav"
    write_wav(wrong_rate, pcm, sample_rate=16000)
    _, _, wrong_hz, wrong_count, wrong_pcm = read_wav(wrong_rate)
    if wrong_pcm != pcm:
        raise RuntimeError("rate label demo changed the samples")
    print(f"Rate-label demo: same PCM at {wrong_hz} Hz lasts "
          f"{wrong_count / wrong_hz:g} s; frequency becomes "
          f"{FREQUENCY_HZ * wrong_hz / SAMPLE_RATE:g} Hz")
    for duration_ms, label in [(10, "callback"), (20, "encoder input")]:
        samples_per_channel = SAMPLE_RATE * duration_ms // 1000
        size = samples_per_channel * CHANNELS * SAMPLE_WIDTH
        print(f"{duration_ms} ms {label}: {samples_per_channel} "
              f"samples/channel; {size} bytes")
    if args.with_opus:
        encode_and_inspect(args.output_dir, pcm, ffmpeg, ffprobe)


if __name__ == "__main__":
    main()
