"""A2A-shaped data contracts for the mesh.

These are a deliberately small, A2A-conformant subset of the agent-card / task model:
enough to describe an agent, the skills it serves, and the result of one dispatch. The
real A2A agent-card JSON (the ``.well-known/agent.json`` shape) is produced by
``to_a2a_json`` so an in-process card can be served over HTTP unchanged tomorrow.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Skill(BaseModel):
    """One capability an agent advertises. ``id`` is the dispatch key on the mesh."""

    id: str
    name: str
    description: str = ""


class AgentCard(BaseModel):
    """An A2A-conformant subset of the agent card — who the agent is and what it serves."""

    name: str
    description: str = ""
    url: str = ""
    version: str = "0.1.0"
    skills: list[Skill] = Field(default_factory=list)
    capabilities: dict = Field(default_factory=lambda: {"streaming": False})


class TaskResult(BaseModel):
    """The outcome of one dispatch: structured output, surfaced cost, and ok/error."""

    skill_id: str
    agent: str
    ok: bool
    output: dict = Field(default_factory=dict)
    error: str | None = None
    cost_usd: float = 0.0


class Hop(BaseModel):
    """One dispatch edge, emitted for observability and the console network view."""

    from_agent: str
    to_agent: str
    skill_id: str
    ok: bool
    cost_usd: float = 0.0


def to_a2a_json(card: AgentCard) -> dict:
    """Render an :class:`AgentCard` as the real A2A agent-card JSON.

    This is the ``.well-known/agent.json`` shape an A2A client expects, so a card the
    mesh dispatches in-process today can be served verbatim over HTTP tomorrow.
    """
    return {
        "name": card.name,
        "description": card.description,
        "url": card.url,
        "version": card.version,
        "capabilities": card.capabilities,
        "skills": [
            {"id": s.id, "name": s.name, "description": s.description} for s in card.skills
        ],
    }
