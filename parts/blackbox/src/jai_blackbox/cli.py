"""CLI: `jai-blackbox verify` (exit 1 on a broken chain) and `jai-blackbox tail -n N`."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from jai_blackbox.chain import BlackBox


def _cmd_verify(box: BlackBox, args: argparse.Namespace) -> int:
    result = box.verify(run_id=args.run_id)
    scope = f" (run_id={args.run_id})" if args.run_id else ""
    if result.ok:
        print(f"chain OK — {result.checked} event(s) verified{scope}")
        return 0
    print(f"chain BROKEN at seq={result.broken_at_seq} — {result.checked} event(s) checked{scope}")
    return 1


def _format_row(row: dict[str, Any]) -> str:
    agent = row["agent"] or "-"
    return (
        f"{row['seq']:>6}  {row['ts'].isoformat()}  {row['tenant_id']}  "
        f"{row['actor_id']}/{row['actor_role']}  agent={agent}  "
        f"{row['action']} -> {row['outcome']}  {row['hash'][:12]}…"
    )


def _cmd_tail(box: BlackBox, args: argparse.Namespace) -> int:
    rows = box.tail(n=args.n, run_id=args.run_id)
    if not rows:
        print("no events")
        return 0
    for row in rows:
        print(_format_row(row))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jai-blackbox",
        description="The flight recorder: tamper-evident audit chain.",
    )
    parser.add_argument("--pg-url", default=None, help="Postgres URL (default: $POSTGRES_URL)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_verify = sub.add_parser("verify", help="walk the full chain; exit 1 if broken")
    p_verify.add_argument("--run-id", default=None, help="only count this run's rows in output")

    p_tail = sub.add_parser("tail", help="print the last N events")
    p_tail.add_argument("-n", type=int, default=10, help="number of events (default 10)")
    p_tail.add_argument("--run-id", default=None, help="filter to one run")

    args = parser.parse_args(argv)
    box = BlackBox(pg_url=args.pg_url)
    if args.command == "verify":
        return _cmd_verify(box, args)
    return _cmd_tail(box, args)


if __name__ == "__main__":
    sys.exit(main())
