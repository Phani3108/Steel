"""Run eval suite 1 against agent-supplier-intel and write its scorecard.

Keyless by design: in mock mode the rag pipeline's deterministic synthesis renders
retrieved facts verbatim, so these suites measure retrieval + permission correctness.
With real keys, phrasing quality rides on top (llm_judge suites come later).

Run:  uv run python evals/run_suite1.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jai_blackbox import BlackBox
from jai_cortex import Cortex  # assembler-tier glue, like the demos
from jai_dyno.harness import run_suite
from jai_dyno.suite import Case, load_suite
from jai_engine.compile import GuardrailViolation, compile_manifest
from jai_gateway import GatewayClient
from jai_manifest import Actor, RunContext, load_manifest
from jai_meter import Meter

ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "parts" / "agents" / "supplier_intel"
SUITE_DIR = ROOT / "evals" / "suite1_supplier_intel"
RESULTS = ROOT / "evals" / "results"
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
    agent = compile_manifest(
        manifest,
        gateway=GatewayClient(),
        blackbox=blackbox,
        meter=meter,
        prompt_base=AGENT_DIR,
        retriever=cortex.retrieve,
    )
    default_tenant = "TEN-0001"

    def target(case: Case) -> str:
        ctx = RunContext(
            tenant_id=case.tenant_id or default_tenant,
            actor=Actor(id="eval", role=case.role),
        )
        try:
            result = agent.run(ctx, case.input)
        except GuardrailViolation as exc:
            return f"REFUSED: {exc}"  # guard blocks surface as refusals to the bench
        return result.text

    scorecards = []
    worst = 1.0
    for suite_path in sorted(SUITE_DIR.glob("*.yaml")):
        suite = load_suite(suite_path)
        card = run_suite(suite, target, agent_name=manifest.name, target_takes_case=True)
        worst = min(worst, card.pass_rate)
        scorecards.append(card.model_dump(mode="json"))
        status = "PASS" if card.pass_rate >= PASS_THRESHOLD else "FAIL"
        print(f"{status}  {suite.name:<22} {card.n_passed}/{card.n_cases} "
              f"(pass_rate={card.pass_rate:.2f})")
        for f in card.failures[:5]:
            print(f"      ✗ {f.case_id}: {f.reason[:110]}")

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "suite1.scorecard.json"
    out.write_text(json.dumps(scorecards, indent=2))
    print(f"\nscorecards → {out}")
    agent.close()
    return 0 if worst >= PASS_THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(main())
