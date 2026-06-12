"""Refusal-contract and case-aware-target grading."""

from jai_dyno.harness import run_suite
from jai_dyno.suite import Case, Suite


def _suite(cases: list[Case]) -> Suite:
    return Suite(name="s", cases=cases)


def test_expect_refusal_passes_on_refused_output():
    suite = _suite([Case(id="r1", input="forbidden question", expect_refusal=True)])
    card = run_suite(suite, lambda _: "REFUSED: role 'requester' may not", agent_name="a")
    assert card.pass_rate == 1.0


def test_expect_refusal_fails_on_answer():
    suite = _suite([Case(id="r1", input="forbidden question", expect_refusal=True)])
    card = run_suite(suite, lambda _: "Here is the contract…", agent_name="a")
    assert card.pass_rate == 0.0
    assert "expected refusal" in card.failures[0].reason


def test_target_takes_case_receives_role_and_tenant():
    seen: list[tuple[str, str | None]] = []

    def target(case: Case) -> str:
        seen.append((case.role, case.tenant_id))
        return case.input

    suite = _suite(
        [Case(id="c1", input="hello", expected="hello", grader="exact",
              role="cpo", tenant_id="TEN-0002")]
    )
    card = run_suite(suite, target, agent_name="a", target_takes_case=True)
    assert card.pass_rate == 1.0
    assert seen == [("cpo", "TEN-0002")]
