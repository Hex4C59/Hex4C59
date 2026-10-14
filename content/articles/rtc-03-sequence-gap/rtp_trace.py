#!/usr/bin/env python3
"""Synthetic RTP trace for RTC 03. Python 3.9+, standard library only.

This reads teaching headers, not audio payloads or a network capture. It models
one validated source, a short sequence window and a fixed playout schedule.
"""

import argparse
import math
import struct
from dataclasses import dataclass
from typing import Optional

SSRC = 0x11223344
PAYLOAD_TYPE = 111  # Assumed to have been negotiated as Opus in this example.
CLOCK_RATE = 48000
BASE_SEQUENCE = 200
BASE_TIMESTAMP = 8000
TIMESTAMP_STEP = 960  # 20 ms at 48 kHz.
EXPECTED_SEQUENCES = range(200, 206)
PREPARE_MS = 5.0


@dataclass(frozen=True)
class Header:
    marker: int
    payload_type: int
    sequence: int
    timestamp: int
    ssrc: int


def parse_teaching_header(data: bytes) -> Header:
    """Accept exactly a 12-byte V=2 header with P=X=CC=0.

    Reject other formats rather than guessing where their payload starts.
    A complete RTP parser must also handle CSRCs, extensions and padding.
    """
    if len(data) != 12:
        raise ValueError("this example requires exactly 12 header bytes")
    first, second, sequence, timestamp, ssrc = struct.unpack("!BBHII", data)
    if first != 0x80:
        raise ValueError("this example requires V=2 and P=X=CC=0")
    return Header(second >> 7, second & 0x7F, sequence, timestamp, ssrc)


def extend_sequence(sequence: int, highest: Optional[int]) -> int:
    """Use the closest 16-bit cycle; assume a distance of less than 32768.

    This does not validate a new source or detect a sender restart. See
    RFC 3550 Appendix A.1 for source validation and large-jump handling.
    """
    if not 0 <= sequence <= 0xFFFF:
        raise ValueError("sequence must fit in 16 bits")
    if highest is None:
        return sequence
    delta = ((sequence - (highest & 0xFFFF) + 32768) % 65536) - 32768
    if delta == -32768:
        raise ValueError("a half-cycle jump is ambiguous")
    return highest + delta


def teaching_trace():
    # The sender is known to have sent sequences 200 through 205. Packet 204
    # never appears in this synthetic receiver trace. The second 201 is a copy.
    for arrival_ms, sequence in [(0, 200), (20, 201), (40, 203),
                                 (42, 201), (58, 202), (95, 205)]:
        timestamp = BASE_TIMESTAMP + (sequence - BASE_SEQUENCE) * TIMESTAMP_STEP
        data = struct.pack("!BBHII", 0x80, PAYLOAD_TYPE, sequence, timestamp, SSRC)
        yield float(arrival_ms), parse_teaching_header(data)


def playout_ms(timestamp: int, start_ms: float) -> float:
    # All fixture timestamps are after the base, within one short clock window.
    return start_ms + (timestamp - BASE_TIMESTAMP) * 1000 / CLOCK_RATE


def analyse(start_ms: float, observe_until_ms: float):
    highest = None
    first_arrivals = {}
    events = []
    duplicates = 0
    reordered = 0
    for arrival_ms, header in teaching_trace():
        if arrival_ms > observe_until_ms:
            break
        if header.ssrc != SSRC or header.payload_type != PAYLOAD_TYPE:
            raise ValueError("a packet does not belong to the configured stream")
        extended = extend_sequence(header.sequence, highest)
        if extended in first_arrivals:
            kind = "duplicate"
            duplicates += 1
        else:
            if highest is not None and extended < highest:
                kind = "reordered"
                reordered += 1
            elif highest is not None and extended > highest + 1:
                kind = "gap opened"
            else:
                kind = "in order"
            first_arrivals[extended] = (arrival_ms, header.timestamp)
            highest = extended if highest is None else max(highest, extended)
        gaps = [seq for seq in range(BASE_SEQUENCE, highest + 1)
                if seq not in first_arrivals]
        events.append((arrival_ms, header.sequence, kind, gaps))

    counts = {"on time": 0, "late": 0, "missing": 0, "pending": 0}
    packets = []
    for sequence in EXPECTED_SEQUENCES:
        timestamp = BASE_TIMESTAMP + (sequence - BASE_SEQUENCE) * TIMESTAMP_STEP
        deadline = playout_ms(timestamp, start_ms)
        arrival = first_arrivals.get(sequence)
        if deadline > observe_until_ms:
            state = "pending"
        elif arrival is None:
            state = "missing"
        elif arrival[0] + PREPARE_MS <= deadline:
            state = "on time"
        else:
            state = "late"
        counts[state] += 1
        packets.append((sequence, deadline, arrival[0] if arrival else None, state))
    return events, packets, counts, duplicates, reordered


def nonnegative_ms(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("time must be finite and nonnegative")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--playout-start-ms", type=nonnegative_ms, default=20.0)
    parser.add_argument("--observe-until-ms", type=nonnegative_ms, default=160.0)
    args = parser.parse_args()
    header = parse_teaching_header(bytes.fromhex("80 6f 00 ca 00 00 26 c0 11 22 33 44"))
    print(f"Header: PT={header.payload_type} seq={header.sequence} "
          f"timestamp={header.timestamp} SSRC=0x{header.ssrc:08x}")
    print(f"Playout start={args.playout_start_ms:g} ms; "
          f"prepare={PREPARE_MS:g} ms; observe until={args.observe_until_ms:g} ms")
    events, packets, counts, duplicates, reordered = analyse(
        args.playout_start_ms, args.observe_until_ms)
    print("\nArrival events (gaps are current sequence gaps):")
    for arrival, sequence, kind, gaps in events:
        print(f"{arrival:5g} ms  seq={sequence}  {kind:10s}  gaps={gaps}")
    print("\nPlayout assessment:")
    for sequence, deadline, arrival, state in packets:
        arrival_text = "--" if arrival is None else f"{arrival:g}"
        print(f"seq={sequence}  arrival={arrival_text:>2s} ms  "
              f"playout={deadline:5g} ms  {state}")
    print(f"\nArrival events: {len(events)}; unique packets: "
          f"{len(events) - duplicates}; duplicates: {duplicates}; "
          f"reordered first arrivals: {reordered}")
    print("Schedule: " + ", ".join(f"{key}={value}" for key, value in counts.items()))
    print("\nSequence wrap demo (independent of the audio trace):")
    highest = None
    seen = set()
    for sequence in [65534, 65535, 0, 1, 65535]:
        extended = extend_sequence(sequence, highest)
        kind = "duplicate" if extended in seen else "new"
        print(f"seq={sequence:5d} -> extended={extended:5d} ({kind})")
        seen.add(extended)
        highest = extended if highest is None else max(highest, extended)


if __name__ == "__main__":
    main()
