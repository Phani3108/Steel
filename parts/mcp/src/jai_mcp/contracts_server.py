"""contracts — contract metadata + clause search as a tool surface.

Read-only over cortex.contracts (metadata, title ILIKE) and cortex.chunks
(doc_type='contract', Postgres FTS over the indexed tsvector). Platform ACL:
``contract`` is visible to category_manager, cpo and system only.

TODO(P3): an HTTP deployment fills tenant_id/role from auth middleware — no real JWT at P2.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

from jai_mcp.db import connect, jsonable

_CONTRACT_ROLES = frozenset({"category_manager", "cpo", "system"})
_MAX_CONTRACTS = 10
_MAX_CLAUSES = 5


def search_contracts(tenant_id: str, role: str, query: str) -> dict[str, Any]:
    """Search contracts by title and by clause full-text; returns matched contract
    metadata plus the top matching clause excerpts."""
    if role not in _CONTRACT_ROLES:
        return {"error": f"forbidden role: '{role}' may not read contracts"}
    with connect() as conn:
        contracts = conn.execute(
            "SELECT id, tenant_id, supplier_id, title, category, start_date, end_date,"
            "       value_usd, payment_terms_days"
            "  FROM cortex.contracts WHERE tenant_id = %s AND title ILIKE %s"
            " ORDER BY value_usd DESC LIMIT %s",
            (tenant_id, f"%{query}%", _MAX_CONTRACTS),
        ).fetchall()
        clauses = conn.execute(
            "SELECT source_id AS contract_id, chunk_id, text AS excerpt,"
            "       ts_rank(ts, plainto_tsquery('english', %s)) AS rank"
            "  FROM cortex.chunks"
            " WHERE tenant_id = %s AND doc_type = 'contract'"
            "   AND ts @@ plainto_tsquery('english', %s)"
            " ORDER BY rank DESC LIMIT %s",
            (query, tenant_id, query, _MAX_CLAUSES),
        ).fetchall()
        # Clause hits may point at contracts the title match missed — pull their meta in.
        missing = {c["contract_id"] for c in clauses} - {c["id"] for c in contracts}
        if missing:
            extra = conn.execute(
                "SELECT id, tenant_id, supplier_id, title, category, start_date, end_date,"
                "       value_usd, payment_terms_days"
                "  FROM cortex.contracts WHERE tenant_id = %s AND id = ANY(%s)",
                (tenant_id, sorted(missing)),
            ).fetchall()
            contracts = contracts + extra
    return {
        "query": query,
        "contracts": [jsonable(c) for c in contracts],
        "clauses": [jsonable(c) for c in clauses],
    }


TOOLS: dict[str, Callable[..., Any]] = {"search_contracts": search_contracts}

server = FastMCP(
    "contracts",
    instructions="Contract repository: metadata + clause full-text search (read-only).",
)
for _fn in TOOLS.values():
    server.tool()(_fn)
