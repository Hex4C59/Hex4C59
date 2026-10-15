#!/usr/bin/env python3
"""Python 3.9+: synthetic matched send/receive records; no network or clock capture."""
import argparse
import csv
from decimal import Decimal, localcontext
from fractions import Fraction
import math
from pathlib import Path

CASES = ("growing", "steady", "spike", "reorder", "sender-queue")


def finite(text):
    try:
        if not math.isfinite(float(text)):
            raise ValueError
        return Fraction(text)
    except (ValueError, OverflowError, ZeroDivisionError):
        raise argparse.ArgumentTypeError("expected a finite number")


def packet_count(text):
    try:
        value = int(text)
        if not 3 <= value <= 10001:
            raise ValueError
        return value
    except ValueError:
        raise argparse.ArgumentTypeError("expected an integer from 3 to 10001")


def number(value):
    if value is None:
        return "-"
    with localcontext() as context:
        context.prec = 28
        rendered = format(Decimal(value.numerator) / Decimal(value.denominator), ".6f")
    return rendered.rstrip("0").rstrip(".")


def make_trace(case, packets=6, receiver_offset=Fraction(0), receiver_ppm=Fraction(0)):
    """The receiver clock is an affine transform of a constructed log.

    Its offset says nothing about the unknown baseline one-way delay.
    Clock-rate errors are injected independently of the selected timing case.
    """
    if case not in CASES:
        raise ValueError("unknown timing case")
    factor = 1 + receiver_ppm / 1000000
    if factor <= 0:
        raise ValueError("receiver clock rate must stay positive")
    trace = []
    for index in range(packets):
        media = Fraction(index * 20)
        sent = Fraction(index * (30 if case == "sender-queue" else 20))
        received = sent + 1000
        if case == "growing":
            received += 3 * index
        elif case == "spike" and index == 2:
            received += 15
        elif case == "reorder" and index == 1:
            received += 25
        trace.append({"seq": 300 + index, "ip_bytes": 120,
                      "media_ms": media, "sent_ms": sent,
                      "received_ms": received * factor + receiver_offset})
    return trace


def analyze(trace):
    """Pair by the already matched send order, retaining signed receive gaps.

    These rows are arithmetic observations, not congestion classifications.
    Reversed receive pairs are explicitly marked rather than hidden by sorting.
    """
    first = trace[0]
    rows = []
    for index, packet in enumerate(trace):
        previous = trace[index - 1] if index else None
        send_gap = packet["sent_ms"] - previous["sent_ms"] if previous else None
        receive_gap = packet["received_ms"] - previous["received_ms"] if previous else None
        change = receive_gap - send_gap if previous else None
        relative = ((packet["received_ms"] - first["received_ms"])
                    - (packet["sent_ms"] - first["sent_ms"]))
        rows.append({**packet, "send_gap_ms": send_gap,
                     "receive_gap_ms": receive_gap, "change_ms": change,
                     "relative_ms": relative,
                     "order": "receive_reversal" if previous and receive_gap < 0 else "ordered"})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, default="growing")
    parser.add_argument("--packets", type=packet_count, default=6)
    parser.add_argument("--receiver-offset-ms", type=finite, default=Fraction(0))
    parser.add_argument("--receiver-ppm", type=finite, default=Fraction(0))
    parser.add_argument("--csv", type=Path, help="create a new CSV file; refuse overwrite")
    args = parser.parse_args()
    try:
        trace = make_trace(args.case, args.packets, args.receiver_offset_ms, args.receiver_ppm)
    except ValueError as error:
        parser.error(str(error))
    rows = analyze(trace)
    if args.csv:
        try:
            with args.csv.open("x", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=list(rows[0]))
                writer.writeheader()
                for row in rows:
                    writer.writerow({key: (value if isinstance(value, str) else
                                           "" if value is None else number(value))
                                     for key, value in row.items()})
        except OSError as error:
            parser.error(str(error))
    print(f"Case: {args.case}; matched packets: {len(rows)}")
    print("seq  media_ms  sent_ms  received_ms  send_gap_ms  receive_gap_ms  change_ms  relative_ms")
    keys = ["seq", "media_ms", "sent_ms", "received_ms", "send_gap_ms",
            "receive_gap_ms", "change_ms", "relative_ms"]
    for index in sorted(set(range(min(6, len(rows)))) | {len(rows) - 1}):
        if index >= 6:
            print("... intermediate rows omitted; use --csv for the full trace")
        print("  ".join(number(rows[index][key]) for key in keys))
    first, last = rows[0], rows[-1]
    send_span = last["sent_ms"] - first["sent_ms"]
    receive_span = last["received_ms"] - first["received_ms"]
    changes = [row["change_ms"] for row in rows[1:]]
    print(f"Send span: {number(send_span)} ms; receive span: {number(receive_span)} ms")
    print(f"Last relative delay change: {number(last['relative_ms'])} ms")
    print(f"Sum of signed changes: {number(sum(changes))} ms; "
          f"sum of absolute changes: {number(sum(abs(value) for value in changes))} ms")
    reversals = sum(row["order"] == "receive_reversal" for row in rows)
    print(f"Adjacent receive reversals in send order: {reversals}")
    if len(rows) <= 12:
        arrival_order = sorted(rows, key=lambda row: (row["received_ms"], row["seq"]))
        print("Arrival order: " + ", ".join(str(row["seq"]) for row in arrival_order))
    print("Absolute one-way delay: unknown; this program is not a bandwidth estimator.")


if __name__ == "__main__":
    main()
