"""jai-dyno standalone demo — no services required.

Runs the repo smoke suite (exact + contains graders) against the built-in echo target,
prints the scorecard, then shows the promotion gate on two sample manifests: one that
earns a level, one parked at the L4 automatic-promotion cap.

Run: python parts/dyno/demo/demo.py
"""

from __future__ import annotations

import json
from pathlib import Path

from jai_dyno import load_suite, promotion_gate, run_suite
from jai_manifest import AgentManifest, AutonomyLevel, PromptRef

REPO_ROOT = Path(__file__).resolve().parents[3]
SMOKE_SUITE = REPO_ROOT / "evals" / "suite0_smoke" / "smoke.yaml"


def echo(text: str) -> str:
    return text


def sample_manifest(level: AutonomyLevel) -> AgentManifest:
    return AgentManifest(
        name="agent-supplier-scout",
        description="Sample agent for the dyno demo",
        autonomy_level=level,
        prompt=PromptRef(path="prompts/supplier_scout.md"),
    )


def main() -> None:
    print(f"== jai-dyno demo: running {SMOKE_SUITE.relative_to(REPO_ROOT)} against echo ==\n")
    suite = load_suite(SMOKE_SUITE)
    scorecard = run_suite(suite, echo, agent_name="agent-supplier-scout")
    print(json.dumps(scorecard.model_dump(mode="json"), indent=2))

    print("\n== promotion gate: L1_SUGGEST manifest, default targets (pass rate >= 0.90) ==")
    decision = promotion_gate(sample_manifest(AutonomyLevel.L1_SUGGEST), scorecard)
    print(json.dumps(decision.model_dump(mode="json"), indent=2))

    print("\n== promotion gate: L4_SUPERVISED manifest — capped, L5 is a human decision ==")
    capped = promotion_gate(sample_manifest(AutonomyLevel.L4_SUPERVISED), scorecard)
    print(json.dumps(capped.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
