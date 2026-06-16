"""The drivetrain catalog: five servers, two faces each.

Every server is (a) a module of plain typed functions — the in-process API other
parts get injected with — and (b) a FastMCP object registering those same functions
as MCP tools. ``in_process_tools()`` is THE seam steel-engine consumes next phase:
manifests reference tools by ``server.tool`` name, the engine resolves them here.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

from steel_mcp import contracts_server, intake, sourcing_events, spend_analytics, supplier_master

_MODULES = {
    "supplier-master": supplier_master,
    "sourcing-events": sourcing_events,
    "contracts": contracts_server,
    "spend-analytics": spend_analytics,
    "intake": intake,
}

SERVERS: dict[str, FastMCP] = {name: mod.server for name, mod in _MODULES.items()}


def in_process_tools(server_name: str) -> dict[str, Callable[..., Any]]:
    """The plain typed functions behind one server, keyed by tool name."""
    mod = _MODULES.get(server_name)
    if mod is None:
        raise KeyError(f"unknown server '{server_name}' (have: {', '.join(sorted(_MODULES))})")
    return dict(mod.TOOLS)
