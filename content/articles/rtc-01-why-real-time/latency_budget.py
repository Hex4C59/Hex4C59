#!/usr/bin/env python3
"""Fixed teaching model for RTC 01; Python 3.9+, no third-party dependencies.

All times use one synthetic clock. This is neither a network benchmark nor an
adaptive jitter buffer. It has no audio input, playback or network access.
"""

import argparse
import math

FRAME_MS = 20.0
EXTRA_NETWORK_MS = [0, 0, 35, 0, 0]


def nonnegative_ms(value):
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise argparse.ArgumentTypeError("time must be finite and nonnegative")
    return result


def calculate(buffer_ms=30.0, sender_queue_ms=6.0):
    stages = [
        ("capture accumulation", FRAME_MS),
        ("processing / encoding / packetization", 9.0),
        ("sender queue", sender_queue_ms),
        ("one-way network", 35.0),
        ("receiver buffer", buffer_ms),
        ("decode", 3.0),
        ("output path", 17.0),
    ]
    receive_ms = sum(duration for _, duration in stages[:4])
    baseline_ms = sum(duration for _, duration in stages)
    prepare_ms = sum(duration for _, duration in stages[-2:])
    blocks = []
    for index, extra_ms in enumerate(EXTRA_NETWORK_MS):
        media_ms = index * FRAME_MS
        arrival_ms = receive_ms + media_ms + extra_ms
        earliest_output_ms = arrival_ms + prepare_ms
        scheduled_ms = baseline_ms + media_ms
        blocks.append((chr(ord("A") + index), arrival_ms, earliest_output_ms,
                       scheduled_ms, earliest_output_ms <= scheduled_ms))
    return stages, baseline_ms, blocks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--buffer-ms", type=nonnegative_ms, default=30.0)
    parser.add_argument("--sender-queue-ms", type=nonnegative_ms, default=6.0)
    parser.add_argument("--target-ms", type=nonnegative_ms, default=150.0)
    args = parser.parse_args()
    stages, baseline, blocks = calculate(args.buffer_ms, args.sender_queue_ms)
    elapsed = 0.0
    print("Stages for the first sample (one synthetic clock):")
    for name, duration in stages:
        elapsed += duration
        print(f"{name:38s} {duration:5g} ms; cumulative={elapsed:5g} ms")
    print(f"\nBaseline delay: {baseline:g} ms")
    print(f"Margin to teaching target {args.target_ms:g} ms: "
          f"{args.target_ms - baseline:g} ms")
    print("\nFive blocks; only C has an extra 35 ms network delay:")
    for name, arrival, ready, scheduled, timely in blocks:
        result = "on time" if timely else f"late by {ready - scheduled:g} ms"
        print(f"{name}: arrival={arrival:g} ms; earliest output={ready:g} ms; "
              f"scheduled={scheduled:g} ms; {result}")
    print(f"On-time original blocks: {sum(row[4] for row in blocks)}/{len(blocks)}")


if __name__ == "__main__":
    main()
