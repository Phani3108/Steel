"""steel-brakes — the brakes: HITL approval gates and the agent kill switch.

SAFETY system part. Durable Postgres state (owned schema namespace `brakes`)
for request → pending → human decision → resume approval flows, plus a
per-agent kill switch every runtime must check before acting. Brakes is the
single handle; Approvals and KillSwitch are also usable standalone.
"""

from __future__ import annotations

from steel_manifest import RunContext

from steel_brakes.approvals import Approvals
from steel_brakes.killswitch import KillSwitch

__version__ = "0.1.0"

__all__ = ["Approvals", "Brakes", "KillSwitch"]


class Brakes:
    """The brake pedal: one handle over the approval gates and the kill switch."""

    def __init__(self, pg_url: str | None = None) -> None:
        self.approvals = Approvals(pg_url)
        self.killswitch = KillSwitch(pg_url)

    def ensure_schema(self) -> None:
        """Idempotently create the brakes schema, both tables, and indexes."""
        self.approvals.ensure_schema()
        self.killswitch.ensure_schema()

    # ── HITL approval gates ──────────────────────────────────────────────────

    def request(self, ctx: RunContext, *, gate: str, thread_id: str, payload: dict) -> int:
        """File one pending approval attributed from ctx; returns the approval id."""
        return self.approvals.request(ctx, gate=gate, thread_id=thread_id, payload=payload)

    def pending(self, tenant_id: str | None = None) -> list[dict]:
        """All pending approvals, newest first, optionally for one tenant."""
        return self.approvals.pending(tenant_id)

    def get(self, approval_id: int) -> dict | None:
        """One approval row by id, or None."""
        return self.approvals.get(approval_id)

    def decide(self, approval_id: int, *, approver: str, approve: bool, note: str = "") -> dict:
        """Record the human decision; write-once — ValueError if already decided."""
        return self.approvals.decide(approval_id, approver=approver, approve=approve, note=note)

    def decision_for(self, thread_id: str, gate: str) -> dict | None:
        """Latest decided row for (thread_id, gate), or None while pending/unknown."""
        return self.approvals.decision_for(thread_id, gate)

    # ── Kill switch ──────────────────────────────────────────────────────────

    def kill(self, agent: str, *, by: str, reason: str = "") -> None:
        """Stop the agent: every runtime must refuse to run it until revived."""
        self.killswitch.kill(agent, by=by, reason=reason)

    def revive(self, agent: str, *, by: str) -> None:
        """Clear the kill flag (records who revived)."""
        self.killswitch.revive(agent, by=by)

    def is_killed(self, agent: str) -> bool:
        """True iff the agent is currently killed; missing row means not killed."""
        return self.killswitch.is_killed(agent)
