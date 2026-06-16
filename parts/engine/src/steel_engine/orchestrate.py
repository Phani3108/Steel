"""The orchestrate pipeline: one intake becomes a fleet operation.

triage → (risk-sentinel ∥ spend-analyst over the mesh) → governed sourcing event.

Every hop runs under the SAME RunContext lineage — `ctx.child(agent=...)` preserves
tenant, run_id, and trace_id — so the whole operation is one run, one audit chain, one
cost rollup. The orchestrator imports no other part: it talks to specialists through the
injected mesh (A2A) and to sourcing through an injected compiled agent.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from steel_manifest import AgentManifest, RunContext, sha256_hex

from steel_engine.compile import BlackboxPort, _audit


class MeshPort(Protocol):
    def dispatch(self, ctx: RunContext, skill_id: str, input: dict[str, Any]) -> Any: ...


class SourcingPort(Protocol):
    def run(self, ctx: RunContext, input_text: str, *, thread_id: str | None = None) -> Any: ...


@dataclass(frozen=True)
class OrchestratorResult:
    status: str  # auto_approved | paused | denied | complete | killed
    text: str
    run_id: str
    trace_id: str
    hops: list[dict[str, Any]] = field(default_factory=list)
    memos: dict[str, Any] = field(default_factory=dict)
    event_id: str = ""
    thread_id: str = ""

    @property
    def total_cost_usd(self) -> float:
        return round(sum(float(h.get("cost_usd", 0.0)) for h in self.hops), 6)


@dataclass
class Orchestrator:
    manifest: AgentManifest
    mesh: MeshPort
    blackbox: BlackboxPort
    sourcing: SourcingPort
    # Below this estimated value an intake is auto-approved; at or above it needs sourcing.
    sourcing_threshold_usd: float = 10_000.0

    def run(self, ctx: RunContext, intake: dict[str, Any]) -> OrchestratorResult:
        ctx = ctx.child(agent=self.manifest.name)
        _audit(self.blackbox, ctx, action="run.start", outcome="ok",
               input_sha256=sha256_hex(json.dumps(intake, sort_keys=True)),
               detail={"intake": intake.get("title")})
        hops: list[dict[str, Any]] = []

        def hop(result: Any, summary: str) -> None:
            hops.append({
                "from_agent": ctx.agent, "to_agent": getattr(result, "agent", "?"),
                "skill_id": getattr(result, "skill_id", "?"), "ok": getattr(result, "ok", False),
                "cost_usd": getattr(result, "cost_usd", 0.0), "summary": summary,
            })
            _audit(self.blackbox, ctx, action="mesh.dispatch",
                   outcome="ok" if getattr(result, "ok", False) else "error",
                   detail={"skill": getattr(result, "skill_id", "?"),
                           "to": getattr(result, "agent", "?")})

        # 1. Triage routes the intake against policy.
        triage = self.mesh.dispatch(ctx, "intake.triage", {
            "title": intake.get("title"), "category": intake.get("category"),
            "est_value_usd": intake.get("est_value_usd"),
        })
        route = (triage.output or {}).get("route", "sourcing_required") if triage.ok else "error"
        hop(triage, (triage.output or {}).get("reason", triage.error or ""))

        if not triage.ok:
            _audit(self.blackbox, ctx, action="run.end", outcome="error",
                   detail={"stage": "triage"})
            return OrchestratorResult(status="denied",
                                      text=f"DENIED: triage failed: {triage.error}",
                                      run_id=ctx.run_id, trace_id=ctx.trace_id, hops=hops)

        if route != "sourcing_required":
            _audit(self.blackbox, ctx, action="run.end", outcome="ok",
                   detail={"route": route})
            return OrchestratorResult(status="auto_approved",
                                      text=f"AUTO-APPROVED: {intake.get('title')} "
                                           f"({(triage.output or {}).get('reason', '')})",
                                      run_id=ctx.run_id, trace_id=ctx.trace_id, hops=hops)

        # 2. Fan out to the specialists — same trace, independent reads.
        memos: dict[str, Any] = {}
        risk = self.mesh.dispatch(ctx, "risk.assess", {"category": intake.get("category")})
        memos["risk"] = risk.output if risk.ok else {"error": risk.error}
        hop(risk, (risk.output or {}).get("summary", risk.error or "")[:120])

        spend = self.mesh.dispatch(ctx, "spend.summary", {"category": intake.get("category")})
        memos["spend"] = spend.output if spend.ok else {"error": spend.error}
        hop(spend, (spend.output or {}).get("summary", spend.error or "")[:120])

        # 3. Run the governed sourcing event (durable; pauses at the publish gate).
        sourcing_input = json.dumps({
            "title": intake.get("title"), "category": intake.get("category"),
            "line_items": intake.get("line_items", []),
            "est_value_usd": intake.get("est_value_usd"),
            "requested_by": intake.get("requested_by", ctx.actor.id),
            "simulate_bids": intake.get("simulate_bids", 3),
        })
        sourcing = self.sourcing.run(ctx, sourcing_input)
        hops.append({
            "from_agent": ctx.agent, "to_agent": "agent-sourcing", "skill_id": "sourcing.run",
            "ok": sourcing.status in ("paused", "complete"), "cost_usd": 0.0,
            "summary": sourcing.text[:120],
        })
        _audit(self.blackbox, ctx, action="mesh.dispatch",
               outcome="ok" if sourcing.status in ("paused", "complete") else "error",
               detail={"skill": "sourcing.run", "to": "agent-sourcing",
                       "sourcing_status": sourcing.status})

        outcome = "ok" if sourcing.status in ("paused", "complete") else "denied"
        _audit(self.blackbox, ctx, action="run.end", outcome=outcome,
               detail={"sourcing_status": sourcing.status, "event_id": sourcing.event_id})
        return OrchestratorResult(
            status=sourcing.status,
            text=f"ORCHESTRATED: {intake.get('title')} → sourcing {sourcing.status}"
                 f" ({sourcing.text[:80]})",
            run_id=ctx.run_id, trace_id=ctx.trace_id, hops=hops, memos=memos,
            event_id=sourcing.event_id, thread_id=sourcing.thread_id,
        )


def compile_orchestrator(
    manifest: AgentManifest,
    *,
    mesh: MeshPort,
    blackbox: BlackboxPort,
    sourcing: SourcingPort,
    sourcing_threshold_usd: float = 10_000.0,
) -> Orchestrator:
    if manifest.pipeline != "orchestrate":
        raise ValueError(f"manifest {manifest.name!r} is pipeline {manifest.pipeline!r}")
    return Orchestrator(manifest=manifest, mesh=mesh, blackbox=blackbox, sourcing=sourcing,
                        sourcing_threshold_usd=sourcing_threshold_usd)


# A handler factory the assembler registers on the mesh. Kept here as the canonical
# signature; the real wiring (cortex/mcp/governor) lives in the assembler (apps/api).
Handler = Callable[[RunContext, dict[str, Any]], dict[str, Any]]
