"""sourcing-events — a minimal RFx engine with a strict state machine.

Owns schema ``sourcing`` (events + bids). Lifecycle:

    draft → invited → bidding → scored → awarded

Wrong-state calls and forbidden roles return ``{"error": "..."}`` — never raise.
Buyer-side actions (create/invite/open/score/award) require the rfx-capable roles
(category_manager, cpo, system); ``submit_bid`` is the supplier-side action and
carries no buyer role.

TODO(P3): an HTTP deployment fills tenant_id/role from auth middleware — no real JWT at P2.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP
from psycopg.types.json import Jsonb

from jai_mcp.db import connect, ensure_schemas, jsonable

_SOURCING_ROLES = frozenset({"category_manager", "cpo", "system"})


def _forbidden(role: str) -> dict[str, str] | None:
    if role not in _SOURCING_ROLES:
        return {"error": f"forbidden: role '{role}' may not manage sourcing events"}
    return None


def _get(conn: Any, tenant_id: str, event_id: str) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT * FROM sourcing.events WHERE tenant_id = %s AND id = %s",
        (tenant_id, event_id),
    ).fetchone()


def _transition(
    tenant_id: str, role: str, event_id: str, from_status: str, to_status: str, **updates: Any
) -> dict[str, Any]:
    if err := _forbidden(role):
        return err
    with connect() as conn:
        event = _get(conn, tenant_id, event_id)
        if event is None:
            return {"error": f"event {event_id} not found"}
        if event["status"] != from_status:
            return {
                "error": f"event {event_id} is '{event['status']}', "
                f"expected '{from_status}' to move to '{to_status}'"
            }
        sets = ["status = %s"] + [f"{k} = %s" for k in updates]
        params = [to_status, *updates.values(), tenant_id, event_id]
        row = conn.execute(
            f"UPDATE sourcing.events SET {', '.join(sets)} "
            "WHERE tenant_id = %s AND id = %s RETURNING *",
            params,
        ).fetchone()
    return jsonable(row)


def create_event(
    tenant_id: str,
    role: str,
    title: str,
    category: str,
    line_items: list[dict[str, Any]],
    created_by: str,
) -> dict[str, Any]:
    """Create a sourcing event in status 'draft'."""
    if err := _forbidden(role):
        return err
    ensure_schemas()
    with connect() as conn:
        row = conn.execute(
            "INSERT INTO sourcing.events (id, tenant_id, title, category, line_items, created_by)"
            " VALUES ('EVT-' || lpad(nextval('sourcing.event_seq')::text, 4, '0'),"
            "         %s, %s, %s, %s, %s) RETURNING *",
            (tenant_id, title, category, Jsonb(line_items), created_by),
        ).fetchone()
    return jsonable(row)


def invite_suppliers(
    tenant_id: str, role: str, event_id: str, supplier_ids: list[str]
) -> dict[str, Any]:
    """Invite suppliers to a draft event (draft → invited)."""
    if not supplier_ids:
        return {"error": "supplier_ids must not be empty"}
    return _transition(
        tenant_id, role, event_id, "draft", "invited", invited=Jsonb(supplier_ids)
    )


def open_bidding(tenant_id: str, role: str, event_id: str) -> dict[str, Any]:
    """Open the event for bids (invited → bidding)."""
    return _transition(tenant_id, role, event_id, "invited", "bidding")


def submit_bid(
    tenant_id: str, event_id: str, supplier_id: str, total_usd: float, lead_time_days: int
) -> dict[str, Any]:
    """Supplier submits a bid; the event must be in status 'bidding'."""
    with connect() as conn:
        event = _get(conn, tenant_id, event_id)
        if event is None:
            return {"error": f"event {event_id} not found"}
        if event["status"] != "bidding":
            return {"error": f"event {event_id} is '{event['status']}', bids need 'bidding'"}
        if supplier_id not in (event["invited"] or []):
            return {"error": f"supplier {supplier_id} was not invited to {event_id}"}
        row = conn.execute(
            "INSERT INTO sourcing.bids (event_id, supplier_id, total_usd, lead_time_days)"
            " VALUES (%s, %s, %s, %s) RETURNING *",
            (event_id, supplier_id, total_usd, lead_time_days),
        ).fetchone()
    return jsonable(row)


def list_bids(tenant_id: str, role: str, event_id: str) -> list[dict[str, Any]] | dict[str, Any]:
    """List bids submitted to an event."""
    with connect() as conn:
        if _get(conn, tenant_id, event_id) is None:
            return {"error": f"event {event_id} not found"}
        rows = conn.execute(
            "SELECT * FROM sourcing.bids WHERE event_id = %s ORDER BY submitted_at, id",
            (event_id,),
        ).fetchall()
    return [jsonable(r) for r in rows]


def score_bids(
    tenant_id: str, role: str, event_id: str, price_weight: float = 0.7
) -> list[dict[str, Any]] | dict[str, Any]:
    """Rank bids by normalized price + lead time (bidding → scored).

    score = price_weight * (best_price / price) + (1 - price_weight) * (best_lead / lead).
    """
    if err := _forbidden(role):
        return err
    if not 0.0 <= price_weight <= 1.0:
        return {"error": "price_weight must be between 0 and 1"}
    with connect() as conn:
        event = _get(conn, tenant_id, event_id)
        if event is None:
            return {"error": f"event {event_id} not found"}
        if event["status"] != "bidding":
            return {"error": f"event {event_id} is '{event['status']}', scoring needs 'bidding'"}
        bids = conn.execute(
            "SELECT supplier_id, total_usd, lead_time_days FROM sourcing.bids"
            " WHERE event_id = %s ORDER BY id",
            (event_id,),
        ).fetchall()
        if not bids:
            return {"error": f"event {event_id} has no bids to score"}
        best_price = min(float(b["total_usd"]) for b in bids)
        best_lead = min(int(b["lead_time_days"]) for b in bids)
        ranked = []
        for b in bids:
            price_score = best_price / float(b["total_usd"]) if b["total_usd"] else 0.0
            lead_score = best_lead / int(b["lead_time_days"]) if b["lead_time_days"] else 0.0
            ranked.append(
                {
                    "supplier_id": b["supplier_id"],
                    "total_usd": float(b["total_usd"]),
                    "lead_time_days": int(b["lead_time_days"]),
                    "score": round(price_weight * price_score + (1 - price_weight) * lead_score, 4),
                }
            )
        ranked.sort(key=lambda r: (-r["score"], r["total_usd"]))
        conn.execute(
            "UPDATE sourcing.events SET status = 'scored' WHERE tenant_id = %s AND id = %s",
            (tenant_id, event_id),
        )
    return ranked


def award(
    tenant_id: str, role: str, event_id: str, supplier_id: str, approved_by: str
) -> dict[str, Any]:
    """Award the event to a supplier (scored → awarded); stamps award_total_usd
    from that supplier's bid. ``approved_by`` records the human approver (HITL)."""
    if err := _forbidden(role):
        return err
    with connect() as conn:
        event = _get(conn, tenant_id, event_id)
        if event is None:
            return {"error": f"event {event_id} not found"}
        if event["status"] != "scored":
            return {"error": f"event {event_id} is '{event['status']}', award needs 'scored'"}
        bid = conn.execute(
            "SELECT total_usd FROM sourcing.bids WHERE event_id = %s AND supplier_id = %s"
            " ORDER BY submitted_at DESC, id DESC LIMIT 1",
            (event_id, supplier_id),
        ).fetchone()
        if bid is None:
            return {"error": f"supplier {supplier_id} has no bid on {event_id}"}
        row = conn.execute(
            "UPDATE sourcing.events SET status = 'awarded', awarded_supplier_id = %s,"
            " award_total_usd = %s WHERE tenant_id = %s AND id = %s RETURNING *",
            (supplier_id, bid["total_usd"], tenant_id, event_id),
        ).fetchone()
        result = jsonable(row)
        result["approved_by"] = approved_by
    return result


def get_event(tenant_id: str, role: str, event_id: str) -> dict[str, Any] | None:
    """Fetch one sourcing event."""
    with connect() as conn:
        row = _get(conn, tenant_id, event_id)
    return jsonable(row) if row else None


TOOLS: dict[str, Callable[..., Any]] = {
    "create_event": create_event,
    "invite_suppliers": invite_suppliers,
    "open_bidding": open_bidding,
    "submit_bid": submit_bid,
    "list_bids": list_bids,
    "score_bids": score_bids,
    "award": award,
    "get_event": get_event,
}

server = FastMCP(
    "sourcing-events",
    instructions="RFx lifecycle: create → invite → bid → score → award, strictly in order.",
)
for _fn in TOOLS.values():
    server.tool()(_fn)
