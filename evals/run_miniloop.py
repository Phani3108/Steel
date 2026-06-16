"""Portability proof — run eval suite 1 through the miniloop runtime.

agent-supplier-intel passes suite 1 at 80/80 on the LangGraph runtime (run_suite1.py).
Here the SAME manifest, prompts, retriever, and suite run on the plain-Python miniloop
runtime. Same agent, two runtimes, same evals — the manifest is the contract (ADR-001).

Run:  uv run python evals/run_miniloop.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from steel_blackbox import BlackBox
from steel_cortex import Cortex
from steel_dyno.harness import run_suite
from steel_dyno.suite import Case, load_suite
from steel_engine.compile import GuardrailViolation
from steel_engine.miniloop import compile_miniloop
from steel_gateway import GatewayClient
from steel_manifest import Actor, RunContext, load_manifest
from steel_meter import Meter

ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "parts" / "agents" / "supplier_intel"
SUITE_DIR = ROOT / "evals" / "suite1_supplier_intel"
PASS_THRESHOLD = 0.90


def main() -> int:
    blackbox = BlackBox()
    blackbox.ensure_schema()
    meter = Meter()
    meter.ensure_schema()
    cortex = Cortex()
    cortex.ensure_schema()
    if not cortex.is_ingested():
        cortex.ingest_seed(ROOT / "data" / "seed")

    manifest = load_manifest(AGENT_DIR / "manifest.yaml")
    agent = compile_miniloop(manifest, gateway=GatewayClient(), blackbox=blackbox, meter=meter,
                             prompt_base=AGENT_DIR, retriever=cortex.retrieve)

    def target(case: Case) -> str:
        ctx = RunContext(tenant_id=case.tenant_id or "TEN-0001",
                         actor=Actor(id="eval", role=case.role))
        try:
            return agent.run(ctx, case.input).text
        except GuardrailViolation as exc:
            return f"REFUSED: {exc}"

    print("runtime: miniloop (plain Python, no LangGraph)")
    worst = 1.0
    for suite_path in sorted(SUITE_DIR.glob("*.yaml")):
        suite = load_suite(suite_path)
        card = run_suite(suite, target, agent_name=manifest.name, target_takes_case=True)
        worst = min(worst, card.pass_rate)
        status = "PASS" if card.pass_rate >= PASS_THRESHOLD else "FAIL"
        print(f"{status}  {suite.name:<22} {card.n_passed}/{card.n_cases} "
              f"(pass_rate={card.pass_rate:.2f})")
        for f in card.failures[:5]:
            print(f"      ✗ {f.case_id}: {f.reason[:110]}")
    print("\nsame agent, two runtimes, same evals." if worst >= PASS_THRESHOLD
          else "\nportability regression!")
    return 0 if worst >= PASS_THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(main())
