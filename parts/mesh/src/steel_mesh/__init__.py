"""steel-mesh — the CAN bus of the STEEL platform.

Lets agents call each other over A2A-shaped contracts with the run context (tenant,
budget, trace) propagated across every hop — in-process today, real A2A-HTTP-ready by
design. No database; pure transport. Imports ``steel_manifest`` only (RunContext).

``a2a-sdk`` is the drop-in for real cross-host A2A serving; ``httpx`` is already a
dependency for the future HTTP transport (see ``HttpTransport``).
"""

from steel_mesh.cards import AgentCard, Hop, Skill, TaskResult
from steel_mesh.mesh import HttpTransport, Mesh

__version__ = "0.1.0"

__all__ = [
    "AgentCard",
    "Hop",
    "HttpTransport",
    "Mesh",
    "Skill",
    "TaskResult",
]
