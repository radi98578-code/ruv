#!/usr/bin/env python3
"""
UDP fan-out for RuView CSI on Windows.

ESP32 nodes send ADR-018 CSI to a single UDP port. Multiple consumers
(recorder, rf-scan, snn-processor) each need their own listen socket, so
this relay receives once and re-emits copies to localhost downstream ports.

Usage:
    python scripts/udp-fanout.py
    python scripts/udp-fanout.py --listen-port 5555 --forward-ports 5006,5007,5008
"""

from __future__ import annotations

import argparse
import socket
import sys
import time


def run_fanout(
    listen_host: str,
    listen_port: int,
    forward_host: str,
    forward_ports: list[int],
    stats_interval: float,
    verbose: bool,
) -> int:
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        rx.bind((listen_host, listen_port))
    except OSError as exc:
        print(
            f"udp-fanout: failed to bind {listen_host}:{listen_port}: {exc}",
            file=sys.stderr,
        )
        if listen_port == 5005:
            print(
                "udp-fanout: port 5005 is often taken by Windows Media Player "
                "(wmpnetwk). Use --listen-port 5555 and reprovision the ESP32, "
                "or disable the 'Windows Media Player Network Sharing Service'.",
                file=sys.stderr,
            )
        return 1

    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    targets = [(forward_host, port) for port in forward_ports]

    print(
        f"udp-fanout: listening on {listen_host}:{listen_port} "
        f"-> {', '.join(f'{forward_host}:{p}' for p in forward_ports)}"
    )

    sources: dict[tuple[str, int], int] = {}
    total = 0
    last_stats = time.monotonic()

    try:
        while True:
            data, src = rx.recvfrom(65535)
            for target in targets:
                try:
                    tx.sendto(data, target)
                except OSError as exc:
                    if verbose:
                        print(f"udp-fanout: forward to {target} failed: {exc}",
                              file=sys.stderr)

            total += 1
            sources[src] = sources.get(src, 0) + 1

            if verbose:
                print(
                    f"udp-fanout: {src[0]}:{src[1]} -> "
                    f"{len(forward_ports)} port(s) ({len(data)}B)"
                )

            now = time.monotonic()
            if now - last_stats >= stats_interval:
                print(
                    f"udp-fanout: forwarded {total} pkts from "
                    f"{len(sources)} source(s) in last {stats_interval:.0f}s"
                )
                sources.clear()
                total = 0
                last_stats = now
    except KeyboardInterrupt:
        print("udp-fanout: stopping")
        return 0
    finally:
        rx.close()
        tx.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--listen-host",
        default="0.0.0.0",
        help="Interface to bind (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=5555,
        help="Port ESP32 CSI packets arrive on (default: 5555)",
    )
    parser.add_argument(
        "--forward-host",
        default="127.0.0.1",
        help="Host for downstream consumers (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--forward-ports",
        default="5006,5007,5008",
        help="Comma-separated downstream UDP ports (default: 5006,5007,5008)",
    )
    parser.add_argument(
        "--stats-interval",
        type=float,
        default=10.0,
        help="Seconds between stats lines (default: 10)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log every forwarded packet",
    )
    args = parser.parse_args()

    forward_ports = [int(p.strip()) for p in args.forward_ports.split(",") if p.strip()]
    if not forward_ports:
        print("udp-fanout: no forward ports specified", file=sys.stderr)
        return 1

    return run_fanout(
        args.listen_host,
        args.listen_port,
        args.forward_host,
        forward_ports,
        args.stats_interval,
        args.verbose,
    )


if __name__ == "__main__":
    raise SystemExit(main())
