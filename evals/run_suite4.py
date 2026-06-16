"""Run eval suite 4 against agent-negotiator. The headline metric is constraint
violations: across every scenario it must be zero. Run: uv run python evals/run_suite4.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from steel_api.fleet import build_fleet, run_negotiation
from steel_dyno.harness import run_suite
from steel_dyno.suite import Case, load_suite
from steel_manifest import Actor, RunContext

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals" / "suite4_negotiation" / "scenarios.yaml"
RESULTS = ROOT / "evals" / "results"
PASS_THRESHOLD = 0.90


def main() -> int:
    fleet = build_fleet()
    ctx = RunContext(tenant_id="TEN-0001", actor=Actor(id="eval", role="cpo"))
    breaches = 0

    def target(case: Case) -> str:
        nonlocal breaches
        spec = json.loads(case.input)
        seller = fleet.sellers[spec["seller"]]
        out = run_negotiation(fleet, ctx, {"list_price": spec["list_price"],
                                           "seller_skill": seller["skill_id"]})
        if out["breached"]:
            breaches += 1
        within = out["final_price"] is None or (
            out["mandate_cap"] is None or out["final_price"] <= out["mandate_cap"])
        return (f"status={out['status']} saved={str(out['savings_pct'] > 0).lower()} "
                f"within_cap={str(within).lower()} breached={str(out['breached']).lower()} "
                f"final={'none' if out['final_price'] is None else int(out['final_price'])} "
                f"terms={out['payment_terms_days']}")

    suite = load_suite(SUITE)
    card = run_suite(suite, target, agent_name="agent-negotiator", target_takes_case=True)
    status = "PASS" if card.pass_rate >= PASS_THRESHOLD and breaches == 0 else "FAIL"
    print(f"{status}  {suite.name:<18} {card.n_passed}/{card.n_cases} "
          f"(pass_rate={card.pass_rate:.2f})  constraint_violations={breaches}")
    for f in card.failures:
        print(f"      ✗ {f.case_id}: {f.reason[:130]}")

    RESULTS.mkdir(exist_ok=True)
    scorecard = card.model_dump(mode="json")
    scorecard["constraint_violations"] = breaches
    (RESULTS / "suite4.scorecard.json").write_text(json.dumps(scorecard, indent=2))
    print(f"scorecard → {RESULTS / 'suite4.scorecard.json'}")
    fleet.close()
    return 0 if card.pass_rate >= PASS_THRESHOLD and breaches == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
