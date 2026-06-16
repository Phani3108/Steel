"""Standalone steel-meter demo: record a handful of actions across two tenants and two
agents, then print a small cost report per dimension.

Requires Postgres (from the repo root: docker compose up -d postgres), or point
POSTGRES_URL at any Postgres you own.

Run: python parts/meter/demo/demo.py
"""

from __future__ import annotations

import sys

from steel_manifest import Actor, RunContext
from steel_meter import Dimension, Meter

ACTIONS: list[tuple[str, str, str, str, str, int, int, float]] = [
    # tenant, agent, action, model, model_group, in_tokens, out_tokens, cost_usd
    ("acme", "agent-sourcing", "model.call", "gpt-5o", "reasoning", 1200, 350, 0.042000),
    ("acme", "agent-sourcing", "tool.call", "", "", 0, 0, 0.000000),
    ("acme", "agent-intake", "model.call", "gpt-5o-mini", "fast", 400, 80, 0.001200),
    ("globex", "agent-sourcing", "model.call", "gpt-5o", "reasoning", 2400, 900, 0.098765),
    ("globex", "agent-intake", "model.call", "gpt-5o-mini", "fast", 150, 30, 0.000450),
    ("globex", "agent-intake", "model.call", "gpt-5o", "reasoning", 800, 220, 0.031000),
]


def main() -> int:
    meter = Meter()
    try:
        meter.ensure_schema()
    except Exception as exc:
        print(f"Cannot reach Postgres ({exc}).")
        print("Start it with: docker compose up -d postgres")
        return 1

    runs: dict[str, RunContext] = {}
    for tenant, agent, action, model, group, tin, tout, cost in ACTIONS:
        ctx = runs.setdefault(
            f"{tenant}/{agent}",
            RunContext(tenant_id=tenant, actor=Actor(id="u-demo", role="system"), agent=agent),
        )
        row_id = meter.record(
            ctx,
            action=action,
            model=model or None,
            model_group=group or None,
            input_tokens=tin,
            output_tokens=tout,
            cost_usd=cost,
            detail={"demo": True},
        )
        print(f"recorded #{row_id}: {tenant:<7} {agent:<15} {action:<11} ${cost:.6f}")

    for key, ctx in runs.items():
        print(f"\nrun total {key} ({ctx.run_id}): ${meter.run_total(ctx.run_id)}")

    dimensions: list[Dimension] = ["tenant_id", "agent", "run_id", "model_group"]
    for dim in dimensions:
        print(f"\n=== costs by {dim} ===")
        print(f"{'key':<28} {'calls':>5} {'in_tok':>8} {'out_tok':>8} {'cost_usd':>12}")
        for row in meter.costs_by(dim):
            print(
                f"{row.key:<28} {row.calls:>5} {row.input_tokens:>8}"
                f" {row.output_tokens:>8} {row.cost_usd:>12}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
