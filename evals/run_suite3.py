"""Run eval suite 3 against agent-orchestrator — the whole fleet, per case.

The target runs one orchestration (auto-clearing gates) and emits a compact status
string capturing what the network did: route, final status, hop count, how many agents
the single run touched, the award, and each specialist's outcome. Keyless and
deterministic. Run:  uv run python evals/run_suite3.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from steel_api.fleet import build_fleet, run_orchestration
from steel_blackbox import BlackBox
from steel_dyno.harness import run_suite
from steel_dyno.suite import Case, load_suite
from steel_manifest import Actor, RunContext

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals" / "suite3_network" / "scenarios.yaml"
RESULTS = ROOT / "evals" / "results"
PASS_THRESHOLD = 0.90


def main() -> int:
    fleet = build_fleet()
    blackbox = BlackBox()

    def target(case: Case) -> str:
        spec = json.loads(case.input)
        ctx = RunContext(tenant_id=spec.get("tenant_id", "TEN-0001"),
                         actor=Actor(id="eval", role=spec.get("role", "cpo")))
        intake = {
            "title": spec["title"], "category": spec["category"],
            "est_value_usd": spec["est_value_usd"],
            "line_items": [{"sku": "REQ", "qty": 1}], "requested_by": "eval",
            "simulate_bids": 3,
        }
        out = run_orchestration(fleet, ctx, intake, auto_approve=True)
        memos = out["memos"]
        risk_memo = memos.get("risk", {})
        spend_memo = memos.get("spend", {})
        risk = "refused" if risk_memo.get("refused") else ("ok" if "summary" in risk_memo else "-")
        spend = "unavailable" if "unavailable" in str(spend_memo.get("summary", "")) else (
            "ok" if "summary" in spend_memo else "-")
        route = "sourcing_required" if out["status"] != "auto_approved" else "auto_approved"
        agents = {e["agent"] for e in blackbox.tail(n=60, run_id=out["run_id"]) if e["agent"]}
        award = out["award"]["supplier_id"] if out["award"] else "none"
        return (f"status={out['status']} route={route} hops={len(out['hops'])} "
                f"agents={len(agents)} award={award} risk={risk} spend={spend}")

    suite = load_suite(SUITE)
    card = run_suite(suite, target, agent_name="agent-orchestrator", target_takes_case=True)
    status = "PASS" if card.pass_rate >= PASS_THRESHOLD else "FAIL"
    print(f"{status}  {suite.name:<18} {card.n_passed}/{card.n_cases} "
          f"(pass_rate={card.pass_rate:.2f})")
    for f in card.failures:
        print(f"      ✗ {f.case_id}: {f.reason[:130]}")

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "suite3.scorecard.json").write_text(
        json.dumps(card.model_dump(mode="json"), indent=2))
    print(f"scorecard → {RESULTS / 'suite3.scorecard.json'}")
    fleet.close()
    return 0 if card.pass_rate >= PASS_THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(main())
