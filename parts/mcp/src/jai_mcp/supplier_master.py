"""supplier-master — the vendor master file as a tool surface.

Read-only over cortex.suppliers (cortex's published table contract). All roles may
read suppliers (platform ACL: ``supplier`` is requester-visible).

Identity travels explicitly: every tool takes ``tenant_id`` and ``role``.
TODO(P3): an HTTP deployment fills both from auth middleware (JWT claims) — at P2
they are plain trusted parameters, no real JWT.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

from jai_mcp.db import connect, jsonable

_COLUMNS = (
    "id, tenant_id, name, category, tier, country, certifications, "
    "annual_revenue_usd, risk_score, red_flag, payment_terms_days"
)
_MAX_ROWS = 25


def search_suppliers(
    tenant_id: str,
    role: str,
    query: str = "",
    category: str = "",
    min_tier: int = 3,
    only_certified: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Search the supplier master. ``min_tier`` is the worst acceptable tier (1 is best);
    ``only_certified`` keeps suppliers holding ALL the named certifications."""
    sql = (
        f"SELECT {_COLUMNS} FROM cortex.suppliers "
        "WHERE tenant_id = %s AND tier <= %s"
    )
    params: list[Any] = [tenant_id, min_tier]
    if query:
        sql += " AND name ILIKE %s"
        params.append(f"%{query}%")
    if category:
        sql += " AND category ILIKE %s"
        params.append(f"%{category}%")
    for cert in only_certified or []:
        sql += " AND certifications @> %s::jsonb"
        params.append(f'["{cert}"]')
    sql += " ORDER BY tier, risk_score, id LIMIT %s"
    params.append(_MAX_ROWS)
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [jsonable(r) for r in rows]


def get_supplier(tenant_id: str, role: str, supplier_id: str) -> dict[str, Any] | None:
    """Fetch one supplier record by id, tenant-scoped."""
    with connect() as conn:
        row = conn.execute(
            f"SELECT {_COLUMNS} FROM cortex.suppliers WHERE tenant_id = %s AND id = %s",
            (tenant_id, supplier_id),
        ).fetchone()
    return jsonable(row) if row else None


TOOLS: dict[str, Callable[..., Any]] = {
    "search_suppliers": search_suppliers,
    "get_supplier": get_supplier,
}

server = FastMCP(
    "supplier-master",
    instructions="Vendor master file: search and fetch supplier records (read-only).",
)
for _fn in TOOLS.values():
    server.tool()(_fn)
