"""compile_manifest — the seam that turns an AgentManifest into a runnable agent.

The engine is the ONLY part that imports an orchestration framework (LangGraph 1.x,
ADR-001). Everything the runtime needs — model policy, prompt, guardrails — comes from
the manifest; everything a run produces — audit events, ledger rows — leaves through the
injected blackbox/meter ports. Swapping the runtime means writing another compile
function against the same manifest (ADR-004: the compile step is the swap point).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, TypedDict

from jai_gateway import GatewayResponse
from jai_manifest import AgentManifest, AuditEvent, Outcome, RunContext, sha256_hex
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

_DEFAULT_PG_URL = "postgresql://jai:jai@localhost:5433/jai"

# guard_in's deny-list: a deliberately tiny stub for jai-governor's real injection
# classifier. Matching is case-insensitive substring.
_INJECTION_MARKERS = ("ignore previous instructions", "system prompt:")

# Key inside the state's ctx dict where the run accrues spend. Extra keys are ignored
# by RunContext.model_validate, so the dict stays a valid RunContext payload.
_COST_KEY = "cost_usd_accrued"


class GuardrailViolation(Exception):
    """Input or output failed a manifest guardrail; the run stops, audited, not retried."""


class GatewayPort(Protocol):
    """The slice of jai_gateway.GatewayClient the engine calls."""

    def complete(
        self,
        ctx: RunContext,
        *,
        group: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 1024,
    ) -> GatewayResponse: ...


class BlackboxPort(Protocol):
    """The slice of jai_blackbox.BlackBox the engine calls."""

    def append(self, event: AuditEvent) -> str: ...


class MeterPort(Protocol):
    """The slice of jai_meter.Meter the engine calls."""

    def record(
        self,
        ctx: RunContext,
        *,
        action: str,
        model: str | None,
        model_group: str | None,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> int: ...


class EngineState(TypedDict):
    """The graph state: plain JSON-serializable values so checkpoints stay portable."""

    input: str
    output: str
    ctx: dict[str, Any]
    facts: list[dict[str, Any]]
    chunks: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    refused: bool


@dataclass(frozen=True)
class RunResult:
    """What one agent run returns to its caller."""

    text: str
    cost_usd: float
    run_id: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    refused: bool = False


class RetrieverPort(Protocol):
    """What a rag-pipeline retriever must return (duck-typed: jai-cortex satisfies it,
    but the engine never imports it — the assembler injects)."""

    def __call__(self, ctx: RunContext, query: str) -> Any: ...


def _audit(
    blackbox: BlackboxPort,
    ctx: RunContext,
    *,
    action: str,
    outcome: Outcome,
    input_sha256: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    blackbox.append(
        AuditEvent(
            tenant_id=ctx.tenant_id,
            actor_id=ctx.actor.id,
            actor_role=ctx.actor.role,
            agent=ctx.agent,
            run_id=ctx.run_id,
            trace_id=ctx.trace_id,
            action=action,
            outcome=outcome,
            input_sha256=input_sha256,
            detail=detail or {},
        )
    )


def _ctx_of(state: EngineState) -> RunContext:
    return RunContext.model_validate(state["ctx"])


def _postgres_checkpointer(pg_url: str | None = None) -> PostgresSaver | None:
    """The ONLY place durability touches infrastructure: a reachable Postgres yields a
    ready saver (ADR-004); anything else yields None so mock runs never need services."""
    import psycopg
    from psycopg.rows import dict_row

    url = pg_url or os.environ.get("POSTGRES_URL", _DEFAULT_PG_URL)
    try:
        conn = psycopg.connect(
            url,
            autocommit=True,  # PostgresSaver.setup() requires it
            prepare_threshold=0,
            row_factory=dict_row,
            connect_timeout=2,
        )
        saver = PostgresSaver(conn)  # type: ignore[arg-type]  # dict_row connection
        saver.setup()
    except Exception:
        return None
    return saver


@dataclass
class CompiledAgent:
    """A manifest compiled to a runnable graph, with the run() envelope around it."""

    manifest: AgentManifest
    system_prompt: str
    graph: CompiledStateGraph
    blackbox: BlackboxPort
    checkpointer: PostgresSaver | None = None

    def run(self, ctx: RunContext, input_text: str, *, thread_id: str | None = None) -> RunResult:
        ctx = ctx.child(agent=self.manifest.name)
        if ctx.budget_usd_remaining is None:
            ctx = ctx.model_copy(
                update={"budget_usd_remaining": self.manifest.model.budget_usd_per_task}
            )
        _audit(
            self.blackbox,
            ctx,
            action="run.start",
            outcome="ok",
            input_sha256=sha256_hex(input_text),
        )
        config: dict[str, Any] | None = None
        if self.checkpointer is not None:
            config = {"configurable": {"thread_id": thread_id or ctx.run_id}}
        state: EngineState = {
            "input": input_text,
            "output": "",
            "ctx": ctx.model_dump(mode="json"),
            "facts": [],
            "chunks": [],
            "citations": [],
            "refused": False,
        }
        try:
            final: EngineState = self.graph.invoke(state, config)
        except Exception as exc:
            _audit(
                self.blackbox,
                ctx,
                action="run.end",
                outcome="error",
                detail={"error": f"{type(exc).__name__}: {exc}"},
            )
            raise
        cost = float(final["ctx"].get(_COST_KEY, 0.0))
        _audit(self.blackbox, ctx, action="run.end", outcome="ok", detail={"cost_usd": cost})
        return RunResult(
            text=final["output"],
            cost_usd=cost,
            run_id=ctx.run_id,
            citations=list(final.get("citations", [])),
            refused=bool(final.get("refused", False)),
        )

    def close(self) -> None:
        """Release the checkpointer's Postgres connection, if one was opened."""
        if self.checkpointer is not None:
            conn = getattr(self.checkpointer, "conn", None)
            if conn is not None and hasattr(conn, "close"):
                conn.close()


def compile_manifest(
    manifest: AgentManifest,
    *,
    gateway: GatewayPort,
    blackbox: BlackboxPort,
    meter: MeterPort,
    prompt_base: Path,
    retriever: RetrieverPort | None = None,
) -> CompiledAgent:
    """Compile a manifest into a LangGraph agent.

    pipeline "direct": guard_in -> model -> guard_out
    pipeline "rag":    guard_in -> retrieve -> synthesize -> guard_out (needs retriever)
    """
    if manifest.pipeline == "rag" and retriever is None:
        raise ValueError(f"manifest {manifest.name!r} has pipeline 'rag'; pass retriever=")
    system_prompt = (Path(prompt_base) / manifest.prompt.path).read_text()

    def guard_in(state: EngineState) -> dict[str, Any]:
        if not manifest.guardrails.input_screening:
            return {}
        lowered = state["input"].lower()
        for marker in _INJECTION_MARKERS:
            if marker in lowered:
                _audit(
                    blackbox,
                    _ctx_of(state),
                    action="guardrail.input",
                    outcome="denied",
                    input_sha256=sha256_hex(state["input"]),
                    detail={"marker": marker},
                )
                raise GuardrailViolation(f"input rejected: contains {marker!r}")
        return {}

    def model(state: EngineState) -> dict[str, Any]:
        ctx = _ctx_of(state)
        response = gateway.complete(
            ctx,
            group=manifest.model.group,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": state["input"]},
            ],
            max_tokens=manifest.model.max_tokens,
        )
        _audit(
            blackbox,
            ctx,
            action="model.call",
            outcome="ok",
            input_sha256=sha256_hex(state["input"]),
            detail={
                "model": response.model,
                "group": response.group,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
            },
        )
        meter.record(
            ctx,
            action="model.call",
            model=response.model,
            model_group=response.group,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.cost_usd,
        )
        new_ctx = dict(state["ctx"])
        new_ctx[_COST_KEY] = float(new_ctx.get(_COST_KEY, 0.0)) + response.cost_usd
        if new_ctx.get("budget_usd_remaining") is not None:
            new_ctx["budget_usd_remaining"] = max(
                0.0, float(new_ctx["budget_usd_remaining"]) - response.cost_usd
            )
        return {"output": response.text, "ctx": new_ctx}

    def guard_out(state: EngineState) -> dict[str, Any]:
        if manifest.guardrails.output_validation and not state["output"].strip():
            _audit(
                blackbox,
                _ctx_of(state),
                action="guardrail.output",
                outcome="denied",
                detail={"reason": "empty output"},
            )
            raise GuardrailViolation("output rejected: empty")
        return {}

    def retrieve(state: EngineState) -> dict[str, Any]:
        ctx = _ctx_of(state)
        assert retriever is not None  # guarded at compile time
        result = retriever(ctx, state["input"])
        refused = bool(getattr(result, "refused", False))
        facts = list(getattr(result, "facts", []))
        chunks = [
            c.model_dump() if hasattr(c, "model_dump") else dict(c)
            for c in getattr(result, "chunks", [])
        ]
        citations = [
            c.model_dump() if hasattr(c, "model_dump") else dict(c)
            for c in getattr(result, "citations", [])
        ]
        _audit(
            blackbox,
            ctx,
            action="retrieve",
            outcome="denied" if refused else "ok",
            input_sha256=sha256_hex(state["input"]),
            detail={"n_facts": len(facts), "n_chunks": len(chunks), "refused": refused},
        )
        if refused:
            reason = getattr(result, "refusal_reason", None) or "not permitted"
            return {"refused": True, "citations": [], "output": f"REFUSED: {reason}"}
        return {"facts": facts, "chunks": chunks, "citations": citations}

    def synthesize(state: EngineState) -> dict[str, Any]:
        if state["refused"]:
            return {}  # refusal text already set by retrieve
        ctx = _ctx_of(state)
        if os.environ.get("JAI_MOCK", "1") == "1":
            # Keyless determinism: render the retrieved context verbatim so eval
            # graders measure retrieval correctness, not mock-string phrasing.
            n = len(state["facts"]) + len(state["chunks"])
            lines = [f"Based on {n} sources:"]
            for f in state["facts"]:
                lines.append("- " + "; ".join(f"{k}={v}" for k, v in f.items()))
            for c in state["chunks"]:
                lines.append(f"- [{c['doc_type']}:{c['source_id']}] {c['text'][:200]}")
            return {"output": "\n".join(lines)}
        context_lines = [
            "CONTEXT — answer only from this:",
            *(f"FACT {f}" for f in state["facts"]),
            *(f"EXCERPT [{c['doc_type']}:{c['source_id']}] {c['text']}" for c in state["chunks"]),
        ]
        response = gateway.complete(
            ctx,
            group=manifest.model.group,
            messages=[
                {"role": "system", "content": system_prompt + "\n\n" + "\n".join(context_lines)},
                {"role": "user", "content": state["input"]},
            ],
            max_tokens=manifest.model.max_tokens,
        )
        _audit(
            blackbox,
            ctx,
            action="model.call",
            outcome="ok",
            input_sha256=sha256_hex(state["input"]),
            detail={
                "model": response.model,
                "group": response.group,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
            },
        )
        meter.record(
            ctx,
            action="model.call",
            model=response.model,
            model_group=response.group,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.cost_usd,
        )
        new_ctx = dict(state["ctx"])
        new_ctx[_COST_KEY] = float(new_ctx.get(_COST_KEY, 0.0)) + response.cost_usd
        return {"output": response.text, "ctx": new_ctx}

    builder: StateGraph = StateGraph(EngineState)
    builder.add_node("guard_in", guard_in)
    builder.add_node("guard_out", guard_out)
    builder.add_edge(START, "guard_in")
    if manifest.pipeline == "rag":
        builder.add_node("retrieve", retrieve)
        builder.add_node("synthesize", synthesize)
        builder.add_edge("guard_in", "retrieve")
        builder.add_edge("retrieve", "synthesize")
        builder.add_edge("synthesize", "guard_out")
    else:
        builder.add_node("model", model)
        builder.add_edge("guard_in", "model")
        builder.add_edge("model", "guard_out")
    builder.add_edge("guard_out", END)

    checkpointer = _postgres_checkpointer()
    graph = builder.compile(checkpointer=checkpointer)
    return CompiledAgent(
        manifest=manifest,
        system_prompt=system_prompt,
        graph=graph,
        blackbox=blackbox,
        checkpointer=checkpointer,
    )
