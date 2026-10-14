#!/usr/bin/env python3
"""Compare recovery deadlines for RTC 04 (Python 3.9+, standard library only).

This is arithmetic on a synthetic receiver clock, not a network or codec test.
The sequence gap is noticed when packet 203 arrives. The playout scheduler can
request concealment without waiting for a higher sequence number.
"""

import argparse
import math


def nonnegative_ms(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("time must be finite and nonnegative")
    return number


def assess(next_ms=40.0, playout_ms=60.0, prepare_ms=5.0, feedback_ms=2.0,
           network_rtt_ms=20.0, lookup_ms=1.0, send_queue_ms=4.0,
           has_fec=True, cached=True):
    request_ms = next_ms + feedback_ms
    returned_ms = request_ms + network_rtt_ms + lookup_ms + send_queue_ms
    nack_ready_ms = returned_ms + prepare_ms
    fec_ready_ms = next_ms + prepare_ms
    return {
        "latest_input_ms": playout_ms - prepare_ms,
        "request_ms": request_ms,
        "retransmission_arrival_ms": returned_ms,
        "retransmission_ready_ms": nack_ready_ms,
        "retransmission_timely": cached and nack_ready_ms <= playout_ms,
        "fec_ready_ms": fec_ready_ms,
        "fec_timely": has_fec and fec_ready_ms <= playout_ms,
        "plc_start_ms": playout_ms - prepare_ms,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name, default in [("next-packet-ms", 40), ("playout-ms", 60),
                          ("prepare-ms", 5), ("feedback-ms", 2),
                          ("network-rtt-ms", 20), ("lookup-ms", 1),
                          ("send-queue-ms", 4)]:
        parser.add_argument("--" + name, type=nonnegative_ms, default=float(default))
    parser.add_argument("--no-fec", action="store_true")
    parser.add_argument("--cache-miss", action="store_true")
    args = parser.parse_args()
    if args.prepare_ms > args.playout_ms:
        parser.error("preparation starts before this model's time origin")
    result = assess(args.next_packet_ms, args.playout_ms, args.prepare_ms,
                    args.feedback_ms, args.network_rtt_ms, args.lookup_ms,
                    args.send_queue_ms, not args.no_fec, not args.cache_miss)
    print("MODEL ONLY: fixed 20 ms audio blocks; no real network or codec")
    print(f"Playout: {args.playout_ms:g} ms; preparation: {args.prepare_ms:g} ms")
    print(f"Latest usable input: {result['latest_input_ms']:g} ms")
    print(f"NACK request: {result['request_ms']:g} ms")
    if args.cache_miss:
        print("Retransmission: unavailable (sender has no cached original)")
    else:
        print(f"Retransmission arrives: {result['retransmission_arrival_ms']:g} ms; "
              f"ready: {result['retransmission_ready_ms']:g} ms")
        print("Retransmission: " + ("on time" if result['retransmission_timely']
                                     else "too late"))
    print(f"Next packet prepared: {result['fec_ready_ms']:g} ms; "
          f"redundancy assumed present: {not args.no_fec}")
    if args.no_fec:
        print("FEC recovery: unavailable (no recovery redundancy)")
    else:
        print("FEC recovery: " + ("on time" if result['fec_timely'] else "too late"))
    print(f"PLC: schedule local concealment at {result['plc_start_ms']:g} ms; "
          "no missing packet is received by doing this")


if __name__ == "__main__":
    main()
