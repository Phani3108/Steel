"""Run eval suite 2 against agent-sourcing — full lifecycle per case, real parts.

The runner plays the human: when a run pauses at a gate it decides per the case spec
("approve" unless the case says otherwise) and resumes, until the run is terminal.
Keyless and deterministic: the sourcing pipeline is procedural and the seller personas
are seeded.

Run:  uv run python evals/run_suite2.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jai_blackbox import BlackBox
from jai_brakes import Brakes
from jai_dyno.harness import run_suite
from jai_dyno.suite import Case, load_suite
from jai_engine.sourcing import compile_sourcing
from jai_governor import Governor
from jai_manifest import Actor, RunContext, load_manifest
from jai_mcp.registry import in_process_tools

ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "parts" / "agents" / "sourcing"
SUITE = ROOT / "evals" / "suite2_sourcing" / "scenarios.yaml"
RESULTS = ROOT / "evals" / "results"
PASS_THRESHOLD = 0.90
TENANT = "TEN-0001"


def main() -> int:
    blackbox = BlackBox()
    blackbox.ensure_schema()
    brakes = Brakes()
    brakes.ensure_schema()
    personas = [json.loads(line) for line in
                (ROOT / "data" / "seed" / "seller_personas.jsonl").read_text().splitlines()]
    manifest = load_manifest(AGENT_DIR / "manifest.yaml")
    agent = compile_sourcing(
        manifest,
        blackbox=blackbox,
        governor=Governor(),
        brakes=brakes,
        tools={n: in_process_tools(n) for n in ("sourcing-events", "supplier-master")},
        personas=personas,
    )

    def target(case: Case) -> str:
        spec = json.loads(case.input)
        gates: dict[str, str] = spec.get("gates", {})
        if spec.get("kill"):
            brakes.kill(manifest.name, by="eval", reason="scenario s-10")
        try:
            ctx = RunContext(tenant_id=case.tenant_id or TENANT,
                             actor=Actor(id="eval", role=case.role))
            result = agent.run(ctx, json.dumps(spec["intake"]))
            for _ in range(4):  # a run has at most two gates; 4 is a safe ceiling
                if result.status != "paused":
                    break
                decision = gates.get(result.gate, "approve")
                pend = [p for p in brakes.pending(ctx.tenant_id)
                        if p["thread_id"] == result.thread_id and p["gate"] == result.gate]
                if pend:
                    brakes.decide(pend[0]["id"], approver="eval",
                                  approve=decision == "approve", note="suite2")
                result = agent.resume(ctx, thread_id=result.thread_id)
            return result.text
        finally:
            if spec.get("kill"):
                brakes.revive(manifest.name, by="eval")

    suite = load_suite(SUITE)
    card = run_suite(suite, target, agent_name=manifest.name, target_takes_case=True)
    status = "PASS" if card.pass_rate >= PASS_THRESHOLD else "FAIL"
    print(f"{status}  {suite.name:<18} {card.n_passed}/{card.n_cases} "
          f"(pass_rate={card.pass_rate:.2f})")
    for f in card.failures:
        print(f"      ✗ {f.case_id}: {f.reason[:120]}")

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "suite2.scorecard.json").write_text(
        json.dumps(card.model_dump(mode="json"), indent=2))
    print(f"scorecard → {RESULTS / 'suite2.scorecard.json'}")
    agent.close()
    return 0 if card.pass_rate >= PASS_THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(main())
