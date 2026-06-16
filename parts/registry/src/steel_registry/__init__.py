"""steel-registry — the fleet roster.

The live catalog of every agent: its card, autonomy level, status, and latest
scorecard, so the console and the orchestrator can see the whole fleet at a glance.
"""

from __future__ import annotations

from steel_registry.store import AgentRecord, Registry

__all__ = ["AgentRecord", "Registry"]
