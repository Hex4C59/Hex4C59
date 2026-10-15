#!/usr/bin/env python3
"""Python 3.9+: deterministic FIFO/pacing budget; no sockets or real-time waits."""
import argparse
import csv
from decimal import Decimal, localcontext
from fractions import Fraction
import math
from pathlib import Path


def amount(text):
    try:
        if not math.isfinite(float(text)):
            raise ValueError
        value = Fraction(text)
        if value < 0:
            raise ValueError
        return value
    except (ValueError, OverflowError, ZeroDivisionError):
        raise argparse.ArgumentTypeError("expected a finite, nonnegative number")


def positive(text):
    value = amount(text)
    if value == 0:
        raise argparse.ArgumentTypeError("expected a number greater than zero")
    return value


def count(text):
    try:
        value = int(text)
        if not 1 <= value <= 100000:
            raise ValueError
        return value
    except ValueError:
        raise argparse.ArgumentTypeError("expected an integer from 1 to 100000")


def nonnegative_int(text):
    try:
        value = int(text)
        if value < 0:
            raise ValueError
        return value
    except ValueError:
        raise argparse.ArgumentTypeError("expected a nonnegative integer")


def number(value):
    with localcontext() as context:
        context.prec = 28
        rendered = format(Decimal(value.numerator) / Decimal(value.denominator), ".6f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def simulate(payload_kbps, capacity_kbps, interval_ms, packets,
             overhead_bytes=40, initial_queue_bytes=Fraction(0), pacer_kbps=None):
    """Capacity and pacing rates count the selected IP-layer bytes, including headers.

    Initial work is at the bottleneck. A pacer releases its first packet
    immediately; later releases are spaced by packet_bits / pacer_rate.
    Bottleneck serialization is separate and cannot overlap for two packets.
    """
    payload_bytes = payload_kbps * interval_ms / 8
    if payload_bytes.denominator != 1:
        raise ValueError("fixed-size model requires an integer payload byte count")
    packet_bytes = payload_bytes + overhead_bytes
    service_ms = packet_bytes * 8 / capacity_kbps
    bottleneck_free = initial_queue_bytes * 8 / capacity_kbps
    pacer_free = Fraction(0)
    rows = []
    for index in range(packets):
        arrival = index * interval_ms
        release = arrival if pacer_kbps is None else max(arrival, pacer_free)
        if pacer_kbps is not None:
            pacer_free = release + packet_bytes * 8 / pacer_kbps
        start = max(release, bottleneck_free)
        finish = start + service_ms
        rows.append({
            "packet": index + 1,
            "arrival_ms": arrival,
            "pacer_release_ms": release,
            "pacer_wait_ms": release - arrival,
            "bottleneck_wait_ms": start - release,
            "total_wait_ms": start - arrival,
            "finish_ms": finish,
        })
        bottleneck_free = finish
    return packet_bytes, service_ms, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload-kbps", type=positive, default=Fraction(32))
    parser.add_argument("--capacity-kbps", type=positive, default=Fraction(40))
    parser.add_argument("--interval-ms", type=positive, default=Fraction(20))
    parser.add_argument("--packets", type=count, default=50)
    parser.add_argument("--overhead-bytes", type=nonnegative_int, default=40)
    parser.add_argument("--initial-queue-bytes", type=amount, default=Fraction(0))
    parser.add_argument("--pacer-kbps", type=positive)
    parser.add_argument("--csv", type=Path, help="create a new CSV file; refuse overwrite")
    args = parser.parse_args()
    try:
        packet_bytes, service_ms, rows = simulate(
            args.payload_kbps, args.capacity_kbps, args.interval_ms, args.packets,
            args.overhead_bytes, args.initial_queue_bytes, args.pacer_kbps)
    except ValueError as error:
        parser.error(str(error))
    if args.csv:
        try:
            with args.csv.open("x", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=list(rows[0]))
                writer.writeheader()
                for row in rows:
                    writer.writerow({key: number(value) for key, value in row.items()})
        except OSError as error:
            parser.error(str(error))
    print(f"IP packet: {number(packet_bytes)} bytes; service: {number(service_ms)} ms")
    print(f"Offered IP rate: {number(packet_bytes * 8 / args.interval_ms)} kbit/s")
    print(f"Capacity: {number(args.capacity_kbps)} kbit/s; "
          f"initial queue: {number(args.initial_queue_bytes)} bytes")
    print("packet  arrival_ms  pacer_wait_ms  bottleneck_wait_ms  total_wait_ms  finish_ms")
    for index in sorted({0, min(1, len(rows)-1), min(2, len(rows)-1), len(rows)-1}):
        row = rows[index]
        print("  ".join(number(row[key]) for key in
                        ["packet", "arrival_ms", "pacer_wait_ms",
                         "bottleneck_wait_ms", "total_wait_ms", "finish_ms"]))
    last = rows[-1]
    print(f"Last packet: pacer wait={number(last['pacer_wait_ms'])} ms; "
          f"bottleneck wait={number(last['bottleneck_wait_ms'])} ms; "
          f"total wait={number(last['total_wait_ms'])} ms")
    print("Waiting excludes bottleneck serialization, propagation, decoding, and playback.")


if __name__ == "__main__":
    main()
