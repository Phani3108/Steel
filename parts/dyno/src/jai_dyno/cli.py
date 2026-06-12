"""CLI — `jai-dyno run <suite.yaml> --target echo`: smoke-run a suite, print the scorecard.

Exit code is 1 only below the smoke threshold (pass_rate < 0.5); the scorecard JSON is
printed either way. Shipping decisions belong to promotion_gate, not to this exit code.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable

from jai_gateway import GatewayClient
from jai_manifest import Actor, RunContext

from jai_dyno.harness import run_suite
from jai_dyno.suite import load_suite

SMOKE_PASS_RATE_THRESHOLD = 0.5

# Built-in smoke targets. "echo" returns the input unchanged — the bench's known-good rig.
TARGETS: dict[str, Callable[[str], str]] = {
    "echo": lambda text: text,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jai-dyno", description="JAI test bench")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="run an eval suite against a built-in target")
    run_parser.add_argument("suite", help="path to a suite YAML file")
    run_parser.add_argument("--target", choices=sorted(TARGETS), default="echo")
    args = parser.parse_args(argv)

    suite = load_suite(args.suite)
    gateway: GatewayClient | None = None
    ctx: RunContext | None = None
    if any(case.grader == "llm_judge" for case in suite.cases):
        gateway = GatewayClient()
        ctx = RunContext(tenant_id="dyno", actor=Actor(id="jai-dyno", role="system"))

    scorecard = run_suite(
        suite, TARGETS[args.target], agent_name=args.target, gateway=gateway, ctx=ctx
    )
    print(json.dumps(scorecard.model_dump(mode="json"), indent=2))
    return 1 if scorecard.pass_rate < SMOKE_PASS_RATE_THRESHOLD else 0


if __name__ == "__main__":
    sys.exit(main())
