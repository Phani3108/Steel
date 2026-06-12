"""Command-line interface: ``jai-foundry generate`` / ``jai-foundry load``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jai_foundry.generate import DEFAULT_SEED, generate
from jai_foundry.load import load


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jai-foundry",
        description="Borealis Manufacturing synthetic-data factory (deterministic, no LLM)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="generate the dataset as JSONL files + manifest.json")
    gen.add_argument("--out", type=Path, required=True, help="output directory, e.g. data/seed")
    gen.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"default {DEFAULT_SEED}")

    ld = sub.add_parser("load", help="load a generated dataset into Postgres (schema: foundry)")
    ld.add_argument("--from", dest="from_dir", type=Path, required=True,
                    help="directory previously written by `jai-foundry generate`")
    ld.add_argument("--pg-url", default=None,
                    help="Postgres URL; defaults to $POSTGRES_URL")

    args = parser.parse_args(argv)
    if args.command == "generate":
        manifest = generate(seed=args.seed, out=args.out)
        print(json.dumps({"seed": manifest["seed"], "counts": manifest["counts"]},
                         indent=2, sort_keys=True))
    else:
        counts = load(args.from_dir, pg_url=args.pg_url)
        print(json.dumps(counts, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
