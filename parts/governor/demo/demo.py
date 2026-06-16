"""Standalone steel-governor demo: seven pre-action checks against the versioned
procurement policy. Pure Python + YAML — no database, no model, no network.

Run: python parts/governor/demo/demo.py
"""

from __future__ import annotations

from steel_governor import Governor
from steel_manifest import Actor, RunContext

CHECKS: list[tuple[str, str, str, dict]] = [
    # label-role, role, action, params
    ("requester opens an RFx", "requester", "rfx.create", {}),
    ("category manager opens an RFx", "category_manager", "rfx.create", {}),
    (
        "award $8,000 with 2 bids (below three-bid exemption)",
        "category_manager",
        "rfx.award",
        {"total_usd": 8_000, "n_bids": 2},
    ),
    (
        "award $40,000 with 2 bids",
        "category_manager",
        "rfx.award",
        {"total_usd": 40_000, "n_bids": 2},
    ),
    (
        "award $45,000 with 3 bids as category manager",
        "category_manager",
        "rfx.award",
        {"total_usd": 45_000, "n_bids": 3},
    ),
    (
        "award $120,000 with 4 bids as category manager",
        "category_manager",
        "rfx.award",
        {"total_usd": 120_000, "n_bids": 4},
    ),
    (
        "award $30,000 under a $25,000 agent mandate",
        "category_manager",
        "rfx.award",
        {"total_usd": 30_000, "n_bids": 4, "mandate_max_spend_usd": 25_000},
    ),
]


def main() -> int:
    gov = Governor()
    print(f"steel-governor — policy {gov.policy_path} (version {gov.version})\n")

    for label, role, action, params in CHECKS:
        ctx = RunContext(tenant_id="acme", actor=Actor(id="u1", name="Pat", role=role))
        d = gov.check(ctx, action, params)
        verdict = "ALLOWED" if d.allowed else "DENIED"
        if d.requires_gate:
            verdict += f" (gate: {d.requires_gate})"
        print(f"{verdict:<32} {action:<15} {label}")
        for reason in d.reasons:
            print(f"    - {reason}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
