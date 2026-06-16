"""The sourcing pipeline: a durable, gated RFx workflow compiled from a manifest.

intake → policy(create) → draft+invite → GATE rfx_publish → bids → score →
policy(award) → [GATE award_approval] → award

Hard rails, in order of authority: the kill switch (checked at every node), the
governor (pre-action policy checks the agent cannot reason around), human gates
(durable interrupts — steel-brakes is the source of truth for decisions, the LangGraph
resume value is only a wake-up), and the manifest's mandate (a hard spend cap).

Durability: every node boundary is a Postgres checkpoint; a `kill -9` between any two
steps loses nothing — `resume()` continues from the last checkpoint. All collaborators
are duck-typed ports injected by the assembler; the engine imports no other part.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, TypedDict

from steel_manifest import AgentManifest, RunContext, sha256_hex
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from steel_engine.compile import BlackboxPort, _audit, _postgres_checkpointer

ToolMap = dict[str, dict[str, Callable[..., Any]]]


class GovernorPort(Protocol):
    def check(self, ctx: RunContext, action: str, params: dict[str, Any]) -> Any: ...


class BrakesPort(Protocol):
    def request(self, ctx: RunContext, *, gate: str, thread_id: str, payload: dict) -> int: ...
    def pending(self, tenant_id: str | None = None) -> list[dict[str, Any]]: ...
    def decision_for(self, thread_id: str, gate: str) -> dict[str, Any] | None: ...
    def is_killed(self, agent: str) -> bool: ...


class SourcingState(TypedDict):
    input: str
    ctx: dict[str, Any]
    thread_id: str
    intake: dict[str, Any]
    event_id: str
    n_bids: int
    best: dict[str, Any]
    status: str  # running | denied | rejected | killed | complete (paused is derived)
    gate: str
    output: str


@dataclass(frozen=True)
class SourcingResult:
    status: str  # complete | paused | denied | rejected | killed
    text: str
    run_id: str
    thread_id: str
    event_id: str = ""
    gate: str = ""


@dataclass
class SourcingAgent:
    manifest: AgentManifest
    graph: CompiledStateGraph
    blackbox: BlackboxPort
    checkpointer: Any

    def run(
        self, ctx: RunContext, input_text: str, *, thread_id: str | None = None
    ) -> SourcingResult:
        ctx = ctx.child(agent=self.manifest.name)
        thread = thread_id or ctx.run_id
        _audit(self.blackbox, ctx, action="run.start", outcome="ok",
               input_sha256=sha256_hex(input_text), detail={"thread_id": thread})
        state: SourcingState = {
            "input": input_text, "ctx": ctx.model_dump(mode="json"), "thread_id": thread,
            "intake": {}, "event_id": "", "n_bids": 0, "best": {},
            "status": "running", "gate": "", "output": "",
        }
        final = self.graph.invoke(state, self._config(thread))
        return self._conclude(ctx, thread, final)

    def resume(self, ctx: RunContext, *, thread_id: str) -> SourcingResult:
        """Continue a paused/killed run from its checkpoint (brakes decisions are read
        inside the gate nodes — the resume value is only a wake-up signal)."""
        ctx = ctx.child(agent=self.manifest.name)
        _audit(self.blackbox, ctx, action="run.resume", outcome="ok",
               detail={"thread_id": thread_id})
        final = self.graph.invoke(Command(resume="wake"), self._config(thread_id))
        return self._conclude(ctx, thread_id, final)

    def _config(self, thread_id: str) -> dict[str, Any]:
        return {"configurable": {"thread_id": thread_id}}

    def _conclude(self, ctx: RunContext, thread: str, final: dict[str, Any]) -> SourcingResult:
        if "__interrupt__" in final:
            # Node-local updates are lost on interrupt; the gate name travels in the
            # interrupt payload instead.
            payload = getattr(final["__interrupt__"][0], "value", {}) or {}
            gate = str(payload.get("gate") or final.get("gate", ""))
            _audit(self.blackbox, ctx, action="run.pause", outcome="pending_approval",
                   detail={"thread_id": thread, "gate": gate})
            return SourcingResult(status="paused", text=f"PAUSED: awaiting gate {gate!r}",
                                  run_id=ctx.run_id, thread_id=thread,
                                  event_id=str(final.get("event_id", "")), gate=gate)
        status = str(final.get("status", "complete"))
        outcome = "ok" if status == "complete" else "denied"
        _audit(self.blackbox, ctx, action="run.end", outcome=outcome,
               detail={"thread_id": thread, "status": status})
        return SourcingResult(status=status, text=str(final.get("output", "")),
                              run_id=ctx.run_id, thread_id=thread,
                              event_id=str(final.get("event_id", "")),
                              gate=str(final.get("gate", "")))

    def close(self) -> None:
        conn = getattr(self.checkpointer, "conn", None)
        if conn is not None:
            conn.close()


def compile_sourcing(
    manifest: AgentManifest,
    *,
    blackbox: BlackboxPort,
    governor: GovernorPort,
    brakes: BrakesPort,
    tools: ToolMap,
    personas: list[dict[str, Any]] | None = None,
    prompt_base: Path | None = None,  # noqa: ARG001 — manifest contract; prompt unused at P2
) -> SourcingAgent:
    """Compile a pipeline-"sourcing" manifest. Requires a Postgres checkpointer —
    a gated workflow without durability would lose runs at every approval."""
    if manifest.pipeline != "sourcing":
        raise ValueError(f"manifest {manifest.name!r} is pipeline {manifest.pipeline!r}")
    for server in ("sourcing-events", "supplier-master"):
        if server not in tools:
            raise ValueError(f"tools[{server!r}] is required")
    checkpointer = _postgres_checkpointer()
    if checkpointer is None:
        raise RuntimeError("sourcing pipeline requires Postgres (checkpointer unavailable)")
    personas = personas or _DEFAULT_PERSONAS
    se = tools["sourcing-events"]
    sm = tools["supplier-master"]

    def _ctx(state: SourcingState) -> RunContext:
        return RunContext.model_validate(state["ctx"])

    def _killed(state: SourcingState) -> dict[str, Any] | None:
        if brakes.is_killed(manifest.name):
            ctx = _ctx(state)
            _audit(blackbox, ctx, action="kill_switch", outcome="denied",
                   detail={"agent": manifest.name})
            return {"status": "killed", "output": f"KILLED: {manifest.name} kill switch engaged"}
        return None

    def _tool_audit(state: SourcingState, name: str, result: Any) -> None:
        failed = isinstance(result, dict) and "error" in result
        _audit(blackbox, _ctx(state), action="tool.call",
               outcome="error" if failed else "ok",
               detail={"tool": name, "error": result.get("error") if failed else None})

    def parse_intake(state: SourcingState) -> dict[str, Any]:
        if killed := _killed(state):
            return killed
        try:
            intake = json.loads(state["input"])
            for key in ("title", "category", "line_items", "est_value_usd", "requested_by"):
                if key not in intake:
                    raise KeyError(key)
        except (json.JSONDecodeError, KeyError) as exc:
            return {"status": "denied", "output": f"DENIED: invalid intake ({exc})"}
        decision = governor.check(_ctx(state), "rfx.create", {})
        _audit(blackbox, _ctx(state), action="policy.check",
               outcome="ok" if decision.allowed else "denied",
               policy_version=decision.policy_version,
               detail={"action": "rfx.create", "reasons": decision.reasons})
        if not decision.allowed:
            return {"status": "denied", "output": "DENIED: " + "; ".join(decision.reasons)}
        return {"intake": intake}

    def draft(state: SourcingState) -> dict[str, Any]:
        if killed := _killed(state):
            return killed
        ctx, intake = _ctx(state), state["intake"]
        event = se["create_event"](ctx.tenant_id, ctx.actor.role, intake["title"],
                                   intake["category"], intake["line_items"],
                                   intake["requested_by"])
        _tool_audit(state, "sourcing-events.create_event", event)
        if "error" in event:
            return {"status": "denied", "output": f"DENIED: {event['error']}"}
        suppliers = sm["search_suppliers"](ctx.tenant_id, ctx.actor.role,
                                           category=intake["category"])
        ids = [s["id"] for s in suppliers[:4]]
        if len(ids) < 4:  # thin category: top up from the general pool (3-bid rule needs ≥3)
            pool = sm["search_suppliers"](ctx.tenant_id, ctx.actor.role)
            ids += [s["id"] for s in pool if s["id"] not in ids][: 4 - len(ids)]
        invited = se["invite_suppliers"](ctx.tenant_id, ctx.actor.role, event["id"], ids)
        _tool_audit(state, "sourcing-events.invite_suppliers", invited)
        return {"event_id": event["id"]}

    def _gate(state: SourcingState, gate_name: str) -> dict[str, Any]:
        """The durable gate pattern: brakes is the source of truth; interrupt only
        parks the thread. Node re-runs wholly on resume — idempotency lives in brakes."""
        ctx = _ctx(state)
        decision = brakes.decision_for(state["thread_id"], gate_name)
        if decision is None:
            already_pending = any(
                p["thread_id"] == state["thread_id"] and p["gate"] == gate_name
                for p in brakes.pending(ctx.tenant_id)
            )
            if not already_pending:
                approval_id = brakes.request(
                    ctx, gate=gate_name, thread_id=state["thread_id"],
                    payload={"event_id": state["event_id"],
                             "title": state["intake"].get("title", ""),
                             "est_value_usd": state["intake"].get("est_value_usd"),
                             "best_bid": state["best"] or None},
                )
                _audit(blackbox, ctx, action="approval.request", outcome="pending_approval",
                       detail={"gate": gate_name, "approval_id": approval_id})
            interrupt({"gate": gate_name})
            decision = brakes.decision_for(state["thread_id"], gate_name)
            if decision is None:  # woken without a decision: park again
                interrupt({"gate": gate_name})
                return {"status": "rejected", "output": "REJECTED: gate woke undecided"}
        approved = decision["status"] == "approved"
        _audit(blackbox, ctx, action="approval.decision",
               outcome="ok" if approved else "denied",
               detail={"gate": gate_name, "decided_by": decision.get("decided_by"),
                       "note": decision.get("note")})
        if not approved:
            return {"status": "rejected",
                    "output": f"REJECTED: gate {gate_name!r} by {decision.get('decided_by')}"}
        return {"gate": ""}

    def gate_publish(state: SourcingState) -> dict[str, Any]:
        if killed := _killed(state):
            return killed
        # merge order: an approval's {"gate": ""} clears the marker; a rejection keeps it
        return {"gate": "rfx_publish"} | _gate(state, "rfx_publish")

    def collect_bids(state: SourcingState) -> dict[str, Any]:
        if killed := _killed(state):
            return killed
        ctx, intake = _ctx(state), state["intake"]
        opened = se["open_bidding"](ctx.tenant_id, ctx.actor.role, state["event_id"])
        _tool_audit(state, "sourcing-events.open_bidding", opened)
        event = se["get_event"](ctx.tenant_id, ctx.actor.role, state["event_id"])
        invited = event.get("invited", []) if event else []
        est = float(intake["est_value_usd"])
        n_target = int(intake.get("simulate_bids", min(len(invited), 3)))
        for i, supplier_id in enumerate(invited[:n_target]):
            persona = personas[i % len(personas)]
            floor = float(persona["price_floor_pct"])
            if floor > 3:  # seed personas store percentages (95.0), defaults store fractions
                floor /= 100
            total = round(est * floor * (1 + 0.05 * i), 2)
            lead = 14 + 7 * ((i + len(persona["name"])) % 3)
            bid = se["submit_bid"](ctx.tenant_id, state["event_id"], supplier_id, total, lead)
            _tool_audit(state, "sourcing-events.submit_bid", bid)
        return {"n_bids": min(n_target, len(invited))}

    def score(state: SourcingState) -> dict[str, Any]:
        if killed := _killed(state):
            return killed
        ctx = _ctx(state)
        ranked = se["score_bids"](ctx.tenant_id, ctx.actor.role, state["event_id"])
        _tool_audit(state, "sourcing-events.score_bids", ranked)
        if isinstance(ranked, dict) or not ranked:
            return {"status": "denied", "output": "DENIED: no scoreable bids"}
        decision = governor.check(ctx, "rfx.award", {
            "total_usd": ranked[0]["total_usd"], "n_bids": len(ranked),
            "mandate_max_spend_usd": manifest.mandate.max_spend_usd,
        })
        _audit(blackbox, ctx, action="policy.check",
               outcome="ok" if decision.allowed else "denied",
               policy_version=decision.policy_version,
               detail={"action": "rfx.award", "reasons": decision.reasons,
                       "requires_gate": decision.requires_gate})
        if not decision.allowed:
            return {"status": "denied", "output": "DENIED: " + "; ".join(decision.reasons),
                    "best": ranked[0], "n_bids": len(ranked)}
        return {"best": ranked[0], "n_bids": len(ranked),
                "gate": decision.requires_gate or ""}

    def gate_award(state: SourcingState) -> dict[str, Any]:
        if killed := _killed(state):
            return killed
        if state["gate"] != "award_approval":
            return {}  # within threshold — no human gate needed
        return {"gate": "award_approval"} | _gate(state, "award_approval")

    def do_award(state: SourcingState) -> dict[str, Any]:
        if killed := _killed(state):
            return killed
        ctx, best = _ctx(state), state["best"]
        approver = "governor:within-threshold"
        decision = brakes.decision_for(state["thread_id"], "award_approval")
        if decision is not None:
            approver = str(decision.get("decided_by"))
        awarded = se["award"](ctx.tenant_id, ctx.actor.role, state["event_id"],
                              best["supplier_id"], approver)
        _tool_audit(state, "sourcing-events.award", awarded)
        if "error" in awarded:
            return {"status": "denied", "output": f"DENIED: {awarded['error']}"}
        return {"status": "complete",
                "output": (f"AWARDED:{best['supplier_id']} event={state['event_id']} "
                           f"total=${best['total_usd']} bids={state['n_bids']} "
                           f"approver={approver}")}

    def _route(state: SourcingState) -> str:
        return "halt" if state["status"] != "running" else "next"

    builder: StateGraph = StateGraph(SourcingState)
    builder.add_node("parse_intake", parse_intake)
    builder.add_node("draft", draft)
    builder.add_node("gate_publish", gate_publish)
    builder.add_node("collect_bids", collect_bids)
    builder.add_node("score", score)
    builder.add_node("gate_award", gate_award)
    builder.add_node("do_award", do_award)
    builder.add_edge(START, "parse_intake")
    order = ["parse_intake", "draft", "gate_publish", "collect_bids", "score",
             "gate_award", "do_award"]
    for here, there in zip(order, order[1:], strict=False):
        builder.add_conditional_edges(here, _route, {"halt": END, "next": there})
    builder.add_edge("do_award", END)

    graph = builder.compile(checkpointer=checkpointer)
    return SourcingAgent(manifest=manifest, graph=graph, blackbox=blackbox,
                         checkpointer=checkpointer)


# Used when the assembler passes no personas (tests); seeded personas come from
# data/seed/seller_personas.jsonl in demos and evals.
_DEFAULT_PERSONAS: list[dict[str, Any]] = [
    {"name": "baseline", "price_floor_pct": 0.92},
    {"name": "aggressive", "price_floor_pct": 0.85},
    {"name": "premium", "price_floor_pct": 1.02},
]
