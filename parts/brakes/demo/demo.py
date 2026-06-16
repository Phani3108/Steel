"""Standalone steel-brakes demo: an agent hits a HITL gate on a $12,400 PO (a requester
may only self-approve up to $5,000), a category manager decides, the run resumes by
reading the decision — then the kill switch stops the agent cold.

Requires Postgres (from the repo root: docker compose up -d postgres), or point
POSTGRES_URL at any Postgres you own.

Run: python parts/brakes/demo/demo.py
"""

from __future__ import annotations

import sys

from steel_brakes import Brakes
from steel_manifest import Actor, RunContext


def show(label: str, row: dict | None) -> None:
    if row is None:
        print(f"{label}: None")
        return
    print(
        f"{label}: #{row['id']} [{row['status']:<8}] gate={row['gate']} "
        f"thread={row['thread_id']} payload={row['payload']} "
        f"decided_by={row['decided_by']} note={row['note']!r}"
    )


def main() -> int:
    brakes = Brakes()
    try:
        brakes.ensure_schema()
    except Exception as exc:
        print(f"Cannot reach Postgres ({exc}).")
        print("Start it with: docker compose up -d postgres")
        return 1

    ctx = RunContext(
        tenant_id="acme",
        actor=Actor(id="u-req", name="Pat Requester", role="requester"),
        agent="agent-sourcing",
    )

    print("=== 1. agent hits a HITL gate: request approval ===")
    approval_id = brakes.request(
        ctx,
        gate="po-approval",
        thread_id="thread-demo-1",
        payload={"po_total_usd": 12_400, "supplier": "Veridian Metals", "items": 3},
    )
    print(f"requested approval #{approval_id} — run pauses here")

    print("\n=== 2. human inbox: list pending ===")
    for row in brakes.pending("acme"):
        show("pending", row)

    print("\n=== 3. category manager decides ===")
    decided = brakes.decide(
        approval_id, approver="u-cm", approve=True, note="within category budget"
    )
    show("decided", decided)

    try:
        brakes.decide(approval_id, approver="u-cm", approve=False)
    except ValueError as exc:
        print(f"second decide refused (write-once): {exc}")

    print("\n=== 4. run resumes: read the decision for (thread, gate) ===")
    show("decision_for", brakes.decision_for("thread-demo-1", "po-approval"))

    print("\n=== 5. kill switch ===")
    print(f"is_killed(agent-sourcing) = {brakes.is_killed('agent-sourcing')}")
    brakes.kill("agent-sourcing", by="u-cpo", reason="anomalous spend pattern")
    print(f"killed by u-cpo         -> {brakes.is_killed('agent-sourcing')}")
    brakes.revive("agent-sourcing", by="u-cpo")
    print(f"revived by u-cpo        -> {brakes.is_killed('agent-sourcing')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
