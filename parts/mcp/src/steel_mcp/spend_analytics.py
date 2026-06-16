"""spend-analytics — the spend cube and price benchmarks as a tool surface.

Read-only over foundry's published transactional tables (foundry.purchase_orders,
foundry.items, foundry.suppliers). Platform ACL: spend analytics is a
category_manager+ capability.

TODO(P3): an HTTP deployment fills tenant_id/role from auth middleware — no real JWT at P2.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

from steel_mcp.db import connect

_ANALYTICS_ROLES = frozenset({"category_manager", "cpo", "system"})

_CUBE_SQL = {
    "category": """
        SELECT i.category AS key, SUM(p.total)::float8 AS total_usd, COUNT(*)::int AS po_count
          FROM foundry.purchase_orders p
          JOIN foundry.items i ON i.id = p.item_id AND i.tenant_id = p.tenant_id
         WHERE p.tenant_id = %s
         GROUP BY 1 ORDER BY 2 DESC LIMIT %s
    """,
    "supplier": """
        SELECT s.name AS key, SUM(p.total)::float8 AS total_usd, COUNT(*)::int AS po_count
          FROM foundry.purchase_orders p
          JOIN foundry.suppliers s ON s.id = p.supplier_id AND s.tenant_id = p.tenant_id
         WHERE p.tenant_id = %s
         GROUP BY 1 ORDER BY 2 DESC LIMIT %s
    """,
}


def spend_cube(
    tenant_id: str, role: str, by: str = "category", limit: int = 10
) -> list[dict[str, Any]] | dict[str, Any]:
    """Aggregate PO spend by 'category' or 'supplier': total_usd + po_count per group."""
    if role not in _ANALYTICS_ROLES:
        return {"error": f"forbidden: role '{role}' may not read spend analytics"}
    sql = _CUBE_SQL.get(by)
    if sql is None:
        return {"error": "by must be 'category' or 'supplier'"}
    with connect() as conn:
        rows = conn.execute(sql, (tenant_id, limit)).fetchall()
    return [dict(r) for r in rows]


def price_benchmark(tenant_id: str, role: str, sku: str) -> dict[str, Any]:
    """Paid unit-price stats for one SKU across purchase orders."""
    if role not in _ANALYTICS_ROLES:
        return {"error": f"forbidden: role '{role}' may not read spend analytics"}
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*)::int AS n, AVG(p.unit_price)::float8 AS avg,"
            "       MIN(p.unit_price)::float8 AS min, MAX(p.unit_price)::float8 AS max"
            "  FROM foundry.purchase_orders p"
            "  JOIN foundry.items i ON i.id = p.item_id AND i.tenant_id = p.tenant_id"
            " WHERE p.tenant_id = %s AND i.sku = %s",
            (tenant_id, sku),
        ).fetchone()
    return {"sku": sku, **(row or {"n": 0, "avg": None, "min": None, "max": None})}


TOOLS: dict[str, Callable[..., Any]] = {
    "spend_cube": spend_cube,
    "price_benchmark": price_benchmark,
}

server = FastMCP(
    "spend-analytics",
    instructions="Spend cube by category/supplier and SKU price benchmarks (read-only).",
)
for _fn in TOOLS.values():
    server.tool()(_fn)
