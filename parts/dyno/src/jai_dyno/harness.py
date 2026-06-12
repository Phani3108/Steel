"""Harness — run a suite against any callable target and produce a scorecard.

The target is framework-free by design (ADR-001): anything answering input -> output.
Manifests are evaluated through their runtime by the caller; the bench only sees the
callable.
"""

from __future__ import annotations

from collections.abc import Callable

from jai_gateway import GatewayClient
from jai_manifest import RunContext

from jai_dyno.graders import GradeResult, grade_contains, grade_exact, grade_llm_judge
from jai_dyno.scorecard import CaseFailure, Scorecard
from jai_dyno.suite import Case, Suite


def run_suite(
    suite: Suite,
    target: Callable[[str], str],
    *,
    agent_name: str,
    gateway: GatewayClient | None = None,
    ctx: RunContext | None = None,
) -> Scorecard:
    """Run every case in the suite against the target and score the results.

    gateway and ctx are required only when the suite contains llm_judge cases.
    """
    failures: list[CaseFailure] = []
    n_passed = 0
    for case in suite.cases:
        result = _run_case(case, target, gateway=gateway, ctx=ctx)
        if result.passed:
            n_passed += 1
        else:
            failures.append(CaseFailure(case_id=case.id, reason=result.reason))
    n_cases = len(suite.cases)
    return Scorecard(
        agent=agent_name,
        suite=suite.name,
        n_cases=n_cases,
        n_passed=n_passed,
        pass_rate=n_passed / n_cases,
        failures=failures,
    )


def _run_case(
    case: Case,
    target: Callable[[str], str],
    *,
    gateway: GatewayClient | None,
    ctx: RunContext | None,
) -> GradeResult:
    if case.grader == "llm_judge" and (gateway is None or ctx is None):
        raise ValueError(
            f"case {case.id!r} uses the llm_judge grader; run_suite needs gateway= and ctx="
        )
    try:
        output = target(case.input)
    except Exception as exc:
        # A crashing target is a failed case, not a crashed bench.
        return GradeResult(passed=False, reason=f"target raised {type(exc).__name__}: {exc}")
    if case.grader == "exact":
        return grade_exact(output=output, expected=case.expected or "")
    if case.grader == "contains":
        return grade_contains(output=output, expected=case.expected or "")
    assert gateway is not None and ctx is not None  # guarded above
    return grade_llm_judge(gateway, ctx, output=output, rubric=case.judge_rubric or "")
