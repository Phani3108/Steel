"""The platform permission model: which source types each role may read.

Enforcement happens in SQL (tenant filter + role check) below the LLM — an agent
inherits the human actor's role through RunContext and cannot exceed it.
"""

from __future__ import annotations

ALL_TYPES = frozenset({"supplier", "item", "contract", "rfx", "policy", "news"})

ROLE_TYPES: dict[str, frozenset[str]] = {
    "requester": frozenset({"supplier", "item"}),
    "category_manager": frozenset({"supplier", "item", "contract", "rfx", "policy"}),
    "cpo": ALL_TYPES,
    "system": ALL_TYPES,
}


def allowed_types(role: str) -> frozenset[str]:
    return ROLE_TYPES.get(role, frozenset())
