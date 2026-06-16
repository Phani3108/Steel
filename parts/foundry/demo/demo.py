"""Standalone steel-foundry demo: forge the Borealis dataset into a temp dir and inspect it.

Run:  uv run python parts/foundry/demo/demo.py
No services required — generation is pure seeded templates, no LLM, no database.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from steel_foundry.generate import generate


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "seed"
        manifest = generate(out=out)

        print("steel-foundry — Borealis Manufacturing synthetic dataset")
        print(f"seed: {manifest['seed']}\n")
        print("entity counts:")
        for name, count in sorted(manifest["counts"].items()):
            print(f"  {name:<18} {count:>6}")

        lines = (out / "suppliers.jsonl").read_text().splitlines()
        print("\nsample suppliers:")
        for line in lines[:2]:
            s = json.loads(line)
            print(
                f"  {s['id']}  {s['name']} ({s['country']}) — {s['category']}, "
                f"tier {s['tier']}, risk {s['risk_score']}, red_flag={s['red_flag']}"
            )

        policy = json.loads((out / "policy_docs.jsonl").read_text().splitlines()[1])
        print(f"\npolicy doc excerpt — {policy['name']}")
        print("-" * 64)
        print("\n".join(policy["markdown"].splitlines()[:14]))
        print("  ...")


if __name__ == "__main__":
    main()
