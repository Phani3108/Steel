"""steel-mcp — DRIVETRAIN: five procurement MCP servers over the platform's data.

Public API: ``SERVERS`` (name → FastMCP) and ``in_process_tools(name)`` (name →
plain typed functions) — plus the five server modules themselves.
"""

from steel_mcp.registry import SERVERS, in_process_tools

__all__ = ["SERVERS", "in_process_tools"]
