"""steel-cortex CLI: ingest the seed, ask ad-hoc questions with a role."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from steel_manifest import Actor, RunContext

from steel_cortex.cortex import Cortex


def main() -> None:
    parser = argparse.ArgumentParser(prog="steel-cortex")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ingest = sub.add_parser("ingest", help="ingest the seed dataset")
    p_ingest.add_argument("--from", dest="seed_dir", type=Path, default=Path("data/seed"))

    p_ask = sub.add_parser("ask", help="run a retrieval query as a role")
    p_ask.add_argument("query")
    p_ask.add_argument("--role", default="category_manager")
    p_ask.add_argument("--tenant", default="TEN-0001")

    args = parser.parse_args()
    cortex = Cortex()
    cortex.ensure_schema()

    if args.cmd == "ingest":
        counts = cortex.ingest_seed(args.seed_dir)
        print(json.dumps(counts, indent=2))
    elif args.cmd == "ask":
        ctx = RunContext(tenant_id=args.tenant, actor=Actor(id="cli", role=args.role))
        result = cortex.retrieve(ctx, args.query)
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
