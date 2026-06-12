"""intake — the purchase-request front door with inline triage.

Owns schema ``intake``. Triage rule (canonical P2 role thresholds — requester
self-service limit is $5,000): est_value_usd <= 5000 → 'auto_approved', anything
above → 'sourcing_required' (hand-off to sourcing-events).

TODO(P3): an HTTP deployment fills tenant_id/role from auth middleware — no real JWT at P2.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

from jai_mcp.db import connect, ensure_schemas, jsonable

AUTO_APPROVE_LIMIT_USD = 5_000.0  # requester threshold


def submit_request(
    tenant_id: str,
    role: str,
    requested_by: str,
    title: str,
    description: str,
    category: str,
    est_value_usd: float,
) -> dict[str, Any]:
    """Submit a purchase request; triaged inline against the requester threshold."""
    if est_value_usd < 0:
        return {"error": "est_value_usd must be >= 0"}
    status = "auto_approved" if est_value_usd <= AUTO_APPROVE_LIMIT_USD else "sourcing_required"
    ensure_schemas()
    with connect() as conn:
        row = conn.execute(
            "INSERT INTO intake.requests"
            " (id, tenant_id, requested_by, title, description, category, est_value_usd, status)"
            " VALUES ('REQ-' || lpad(nextval('intake.request_seq')::text, 4, '0'),"
            "         %s, %s, %s, %s, %s, %s, %s) RETURNING *",
            (tenant_id, requested_by, title, description, category, est_value_usd, status),
        ).fetchone()
    return jsonable(row)


def list_requests(tenant_id: str, role: str, status: str = "") -> list[dict[str, Any]]:
    """List purchase requests for the tenant, optionally filtered by status."""
    sql = "SELECT * FROM intake.requests WHERE tenant_id = %s"
    params: list[Any] = [tenant_id]
    if status:
        sql += " AND status = %s"
        params.append(status)
    sql += " ORDER BY created_at DESC, id DESC LIMIT 100"
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [jsonable(r) for r in rows]


def get_request(tenant_id: str, role: str, request_id: str) -> dict[str, Any] | None:
    """Fetch one purchase request by id, tenant-scoped."""
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM intake.requests WHERE tenant_id = %s AND id = %s",
            (tenant_id, request_id),
        ).fetchone()
    return jsonable(row) if row else None


TOOLS: dict[str, Callable[..., Any]] = {
    "submit_request": submit_request,
    "list_requests": list_requests,
    "get_request": get_request,
}

server = FastMCP(
    "intake",
    instructions="Purchase-request intake with inline triage against the $5k requester limit.",
)
for _fn in TOOLS.values():
    server.tool()(_fn)
