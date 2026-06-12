"""Harness tests — fake targets, crash containment, llm_judge wiring. Zero network."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from jai_dyno.harness import run_suite
from jai_dyno.suite import Case, Suite
from jai_manifest import Actor, RunContext


def make_suite(*cases: Case) -> Suite:
    return Suite(name="unit", description="unit suite", cases=list(cases))


def test_run_suite_scores_mixed_results() -> None:
    suite = make_suite(
        Case(id="ok-exact", input="a", expected="A", grader="exact"),
        Case(id="ok-contains", input="b", expected="B", grader="contains"),
        Case(id="bad", input="c", expected="nope", grader="exact"),
        Case(id="ok-exact-2", input="d", expected="D", grader="exact"),
    )
    scorecard = run_suite(suite, str.upper, agent_name="agent-upper")
    assert scorecard.agent == "agent-upper"
    assert scorecard.suite == "unit"
    assert (scorecard.n_cases, scorecard.n_passed) == (4, 3)
    assert scorecard.pass_rate == pytest.approx(0.75)
    assert [f.case_id for f in scorecard.failures] == ["bad"]
    assert "'nope'" in scorecard.failures[0].reason
    assert scorecard.policy_violations == 0
    assert scorecard.cost_usd_total == 0.0


def test_crashing_target_is_a_failed_case_not_a_crashed_run() -> None:
    def target(text: str) -> str:
        if text == "boom":
            raise RuntimeError("kaput")
        return text

    suite = make_suite(
        Case(id="fine", input="x", expected="x", grader="exact"),
        Case(id="crash", input="boom", expected="boom", grader="exact"),
    )
    scorecard = run_suite(suite, target, agent_name="agent-flaky")
    assert (scorecard.n_cases, scorecard.n_passed) == (2, 1)
    assert scorecard.failures[0].case_id == "crash"
    assert "RuntimeError" in scorecard.failures[0].reason
    assert "kaput" in scorecard.failures[0].reason


def test_llm_judge_case_without_gateway_raises() -> None:
    suite = make_suite(
        Case(id="judged", input="x", grader="llm_judge", judge_rubric="be terse")
    )
    with pytest.raises(ValueError, match="llm_judge"):
        run_suite(suite, lambda s: s, agent_name="agent-x")


def test_llm_judge_case_runs_through_fake_gateway() -> None:
    class FakeGateway:
        mock = False

        def complete(self, ctx: RunContext, **kwargs: Any) -> SimpleNamespace:
            return SimpleNamespace(text="PASS: terse enough")

    ctx = RunContext(tenant_id="t1", actor=Actor(id="u1", role="system"))
    suite = make_suite(
        Case(id="judged", input="x", grader="llm_judge", judge_rubric="be terse")
    )
    scorecard = run_suite(
        suite, lambda s: s, agent_name="agent-x", gateway=FakeGateway(), ctx=ctx
    )
    assert (scorecard.n_passed, scorecard.failures) == (1, [])
