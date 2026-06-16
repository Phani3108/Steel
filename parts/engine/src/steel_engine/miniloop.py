"""miniloop — a second runtime, to prove the manifest is the contract (ADR-001).

The whole platform bets on protocols and hedges on frameworks: agents are defined by a
framework-free manifest, and the orchestration framework is supposed to be a swappable
detail. This file is the proof. It compiles the SAME AgentManifest as the LangGraph
runtime — same prompts, same guardrails, same retriever, same gateway/audit/meter ports —
but with ~120 lines of plain Python and no graph engine at all. agent-supplier-intel runs
on it and passes the identical eval suite: same agent, two runtimes, same evals.

Supports the "direct" and "rag" pipelines (the stateless agents). Durable, gated pipelines
(sourcing/orchestrate/negotiate) stay on their own runtimes — durability is the langgraph
runtime's job, not the portability proof's.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from steel_manifest import AgentManifest, RunContext, sha256_hex

from steel_engine.compile import (
    _COST_KEY,
    _INJECTION_MARKERS,
    BlackboxPort,
    GatewayPort,
    GuardrailViolation,
    MeterPort,
    RetrieverPort,
    RunResult,
    _audit,
)


@dataclass
class MiniAgent:
    """A manifest compiled to a plain control loop — the runtime-agnostic twin."""

    manifest: AgentManifest
    gateway: GatewayPort
    blackbox: BlackboxPort
    meter: MeterPort
    system_prompt: str
    retriever: RetrieverPort | None = None

    runtime = "miniloop"

    def run(self, ctx: RunContext, input_text: str, *, thread_id: str | None = None) -> RunResult:
        ctx = ctx.child(agent=self.manifest.name)
        _audit(self.blackbox, ctx, action="run.start", outcome="ok",
               input_sha256=sha256_hex(input_text), detail={"runtime": self.runtime})
        cost = 0.0
        try:
            self._guard_in(ctx, input_text)
            if self.manifest.pipeline == "rag":
                text, citations, refused, cost = self._rag(ctx, input_text)
            else:
                text, cost = self._direct(ctx, input_text)
                citations, refused = [], False
            self._guard_out(text)
        except Exception as exc:
            _audit(self.blackbox, ctx, action="run.end", outcome="error",
                   detail={"error": f"{type(exc).__name__}: {exc}"})
            raise
        _audit(self.blackbox, ctx, action="run.end", outcome="ok", detail={"cost_usd": cost})
        return RunResult(text=text, cost_usd=cost, run_id=ctx.run_id,
                         citations=citations, refused=refused)

    def close(self) -> None:  # parity with CompiledAgent; nothing to release
        return None

    # ── nodes, as ordinary methods ──
    def _guard_in(self, ctx: RunContext, text: str) -> None:
        if not self.manifest.guardrails.input_screening:
            return
        low = text.lower()
        if any(marker in low for marker in _INJECTION_MARKERS):
            _audit(self.blackbox, ctx, action="guard_in", outcome="denied",
                   detail={"reason": "injection marker"})
            raise GuardrailViolation("input rejected by guardrail")

    def _guard_out(self, text: str) -> None:
        if self.manifest.guardrails.output_validation and not text.strip():
            raise GuardrailViolation("empty output rejected by guardrail")

    def _direct(self, ctx: RunContext, text: str) -> tuple[str, float]:
        response = self.gateway.complete(
            ctx, group=self.manifest.model.group,
            messages=[{"role": "system", "content": self.system_prompt},
                      {"role": "user", "content": text}],
            max_tokens=self.manifest.model.max_tokens,
        )
        self._account(ctx, response)
        return response.text, response.cost_usd

    def _rag(self, ctx: RunContext, text: str) -> tuple[str, list[dict[str, Any]], bool, float]:
        assert self.retriever is not None
        result = self.retriever(ctx, text)
        refused = bool(getattr(result, "refused", False))
        facts = list(getattr(result, "facts", []))
        chunks = [c.model_dump() if hasattr(c, "model_dump") else dict(c)
                  for c in getattr(result, "chunks", [])]
        citations = [c.model_dump() if hasattr(c, "model_dump") else dict(c)
                     for c in getattr(result, "citations", [])]
        _audit(self.blackbox, ctx, action="retrieve",
               outcome="denied" if refused else "ok", input_sha256=sha256_hex(text),
               detail={"n_facts": len(facts), "n_chunks": len(chunks), "refused": refused})
        if refused:
            reason = getattr(result, "refusal_reason", None) or "not permitted"
            return f"REFUSED: {reason}", [], True, 0.0

        if os.environ.get("STEEL_MOCK", "1") == "1":
            lines = [f"Based on {len(facts) + len(chunks)} sources:"]
            for f in facts:
                lines.append("- " + "; ".join(f"{k}={v}" for k, v in f.items()))
            for c in chunks:
                lines.append(f"- [{c['doc_type']}:{c['source_id']}] {c['text'][:200]}")
            return "\n".join(lines), citations, False, 0.0

        context_lines = ["CONTEXT — answer only from this:",
                         *(f"FACT {f}" for f in facts),
                         *(f"EXCERPT [{c['doc_type']}:{c['source_id']}] {c['text']}"
                           for c in chunks)]
        response = self.gateway.complete(
            ctx, group=self.manifest.model.group,
            messages=[{"role": "system",
                       "content": self.system_prompt + "\n\n" + "\n".join(context_lines)},
                      {"role": "user", "content": text}],
            max_tokens=self.manifest.model.max_tokens,
        )
        self._account(ctx, response)
        return response.text, citations, False, response.cost_usd

    def _account(self, ctx: RunContext, response: Any) -> None:
        _audit(self.blackbox, ctx, action="model.call", outcome="ok",
               detail={"model": response.model, "group": response.group,
                       "input_tokens": response.input_tokens,
                       "output_tokens": response.output_tokens, _COST_KEY: response.cost_usd})
        self.meter.record(ctx, action="model.call", model=response.model,
                          model_group=response.group, input_tokens=response.input_tokens,
                          output_tokens=response.output_tokens, cost_usd=response.cost_usd)


def compile_miniloop(
    manifest: AgentManifest,
    *,
    gateway: GatewayPort,
    blackbox: BlackboxPort,
    meter: MeterPort,
    prompt_base: Path,
    retriever: RetrieverPort | None = None,
) -> MiniAgent:
    """Compile a stateless manifest to the plain-Python runtime."""
    if manifest.pipeline not in ("direct", "rag"):
        raise ValueError(
            f"miniloop runs 'direct'/'rag' pipelines; {manifest.name!r} is {manifest.pipeline!r}"
        )
    if manifest.pipeline == "rag" and retriever is None:
        raise ValueError(f"manifest {manifest.name!r} is pipeline 'rag'; pass retriever=")
    system_prompt = (Path(prompt_base) / manifest.prompt.path).read_text()
    return MiniAgent(manifest=manifest, gateway=gateway, blackbox=blackbox, meter=meter,
                     system_prompt=system_prompt, retriever=retriever)
