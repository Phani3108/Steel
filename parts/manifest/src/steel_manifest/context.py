"""RunContext — the identity and budget envelope that travels with every action.

Every model call, tool call, retrieval, and A2A hop carries a RunContext. Permission
filtering, budget enforcement, audit attribution, and trace correlation all key off it.
An action without a RunContext is a bug by definition.
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["requester", "category_manager", "cpo", "system"]


class Actor(BaseModel):
    """Who is acting. Agents inherit the human actor's permissions and cannot exceed them."""

    id: str
    name: str = ""
    role: Role


class RunContext(BaseModel):
    tenant_id: str
    actor: Actor
    run_id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:16]}")
    trace_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    agent: str | None = None
    budget_usd_remaining: float | None = None

    def child(self, *, agent: str) -> RunContext:
        """Context handed to a sub-agent: same tenant, actor, trace and budget pool."""
        return self.model_copy(update={"agent": agent})

    def metadata_tags(self) -> dict[str, str]:
        """Tags attached to every gateway call for metering and tracing."""
        return {
            "tenant_id": self.tenant_id,
            "actor_id": self.actor.id,
            "actor_role": self.actor.role,
            "agent": self.agent or "-",
            "run_id": self.run_id,
            "trace_id": self.trace_id,
        }
