"""POST /chat — the one assembler-tier write path: runs agent-supplier-intel.

The control plane wires the parts together here (cortex retriever into the engine,
through the gateway) exactly like the demos do; everything else in jai-api stays
read-only.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[4]
AGENT_DIR = ROOT / "parts" / "agents" / "supplier_intel"

Role = Literal["requester", "category_manager", "cpo"]


class ChatRequest(BaseModel):
    message: str
    role: Role = "category_manager"
    tenant_id: str = "TEN-0001"


class ChatResponse(BaseModel):
    text: str
    citations: list[dict[str, Any]]
    refused: bool
    cost_usd: float
    run_id: str


@lru_cache(maxsize=1)
def _agent():
    # Imports live here so /health and the read-only routes never pay for (or fail on)
    # the agent assembly.
    from jai_blackbox import BlackBox
    from jai_cortex import Cortex
    from jai_engine.compile import compile_manifest
    from jai_gateway import GatewayClient
    from jai_manifest import load_manifest
    from jai_meter import Meter

    if not (AGENT_DIR / "manifest.yaml").exists():
        raise FileNotFoundError("supplier-intel agent not installed")
    blackbox = BlackBox()
    blackbox.ensure_schema()
    meter = Meter()
    meter.ensure_schema()
    cortex = Cortex()
    cortex.ensure_schema()
    if not cortex.is_ingested():
        cortex.ingest_seed(ROOT / "data" / "seed")
    return compile_manifest(
        load_manifest(AGENT_DIR / "manifest.yaml"),
        gateway=GatewayClient(),
        blackbox=blackbox,
        meter=meter,
        prompt_base=AGENT_DIR,
        retriever=cortex.retrieve,
    )


def run_chat(req: ChatRequest) -> ChatResponse:
    from jai_engine.compile import GuardrailViolation
    from jai_manifest import Actor, RunContext

    ctx = RunContext(tenant_id=req.tenant_id, actor=Actor(id="console", role=req.role))
    try:
        result = _agent().run(ctx, req.message)
    except GuardrailViolation as exc:
        return ChatResponse(
            text=f"REFUSED: {exc}", citations=[], refused=True, cost_usd=0.0, run_id=ctx.run_id
        )
    return ChatResponse(
        text=result.text,
        citations=result.citations,
        refused=result.refused,
        cost_usd=result.cost_usd,
        run_id=ctx.run_id,
    )
