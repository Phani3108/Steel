"""steel-mcp standalone demo — a full sourcing lifecycle, in-process.

A category manager creates an event, invites three suppliers found through
supplier-master, opens bidding, collects three bids, scores them, and awards the
winner. Then: top-5 spend categories, and an intake auto-approve/escalation pair.

Run (Postgres from `docker compose up -d postgres`, cortex/foundry seeded):

    make demo-part-mcp        # or: uv run python parts/mcp/demo/demo.py
"""

from __future__ import annotations

import json

from steel_mcp import in_process_tools
from steel_mcp.db import ensure_schemas

TENANT = "TEN-0001"
CM = "category_manager"


def show(label: str, payload: object) -> None:
    print(f"\n── {label} " + "─" * max(0, 70 - len(label)))
    print(json.dumps(payload, indent=2, default=str))


def main() -> None:
    ensure_schemas()
    suppliers = in_process_tools("supplier-master")
    sourcing = in_process_tools("sourcing-events")
    spend = in_process_tools("spend-analytics")
    intake = in_process_tools("intake")

    # 1. Find three suppliers worth inviting (bearings first, topped up from the master).
    found = suppliers["search_suppliers"](TENANT, CM, category="Bearings", min_tier=3)
    if len(found) < 3:
        seen = {s["id"] for s in found}
        found += [s for s in suppliers["search_suppliers"](TENANT, CM) if s["id"] not in seen]
    found = found[:3]
    ids = [s["id"] for s in found]
    show("supplier-master: three suppliers to invite", [(s["id"], s["name"]) for s in found])

    # 2. Sourcing lifecycle: draft → invited → bidding → scored → awarded.
    event = sourcing["create_event"](
        TENANT,
        CM,
        title="FY26 spindle bearings restock",
        category="Bearings & Bushings",
        line_items=[{"sku": "BRG-00001", "qty": 500}],
        created_by="cm-1",
    )
    eid = event["id"]
    show("sourcing-events: created", event)

    sourcing["invite_suppliers"](TENANT, CM, eid, ids)
    sourcing["open_bidding"](TENANT, CM, eid)
    for sid, total, lead in zip(ids, (92_000, 88_500, 97_250), (21, 35, 14), strict=True):
        sourcing["submit_bid"](TENANT, eid, sid, total, lead)

    ranked = sourcing["score_bids"](TENANT, CM, eid, price_weight=0.7)
    show("sourcing-events: scored (price 70% / lead time 30%)", ranked)

    awarded = sourcing["award"](TENANT, CM, eid, ranked[0]["supplier_id"], approved_by="cm-1")
    show("sourcing-events: awarded", awarded)

    # 3. Spend cube: top-5 categories by PO spend.
    show("spend-analytics: top-5 categories", spend["spend_cube"](TENANT, CM, "category", 5))

    # 4. Intake triage: one auto-approve, one escalation to sourcing.
    small = intake["submit_request"](
        TENANT, "requester", "req-7", "Lab gloves", "nitrile, boxes", "MRO & Spares", 1_800
    )
    big = intake["submit_request"](
        TENANT, "requester", "req-7", "CNC retrofit", "5-axis upgrade", "Machined Components",
        120_000,
    )
    show("intake: triage pair", [
        {k: r[k] for k in ("id", "title", "est_value_usd", "status")} for r in (small, big)
    ])


if __name__ == "__main__":
    main()
