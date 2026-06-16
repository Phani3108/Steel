"""Promotion gate boundary tests — at-threshold passes, below fails, L4 cap holds."""

from __future__ import annotations

from steel_dyno.scorecard import Scorecard, promotion_gate
from steel_manifest import AgentManifest, AutonomyLevel, MetricTargets, PromptRef


def make_manifest(
    level: AutonomyLevel,
    *,
    eval_pass_rate: float = 0.90,
    max_policy_violations: int = 0,
) -> AgentManifest:
    return AgentManifest(
        name="agent-test-subject",
        description="promotion gate test subject",
        autonomy_level=level,
        prompt=PromptRef(path="prompts/test.md"),
        metrics=MetricTargets(
            eval_pass_rate=eval_pass_rate,
            max_policy_violations=max_policy_violations,
        ),
    )


def make_scorecard(*, pass_rate: float, policy_violations: int = 0) -> Scorecard:
    return Scorecard(
        agent="agent-test-subject",
        suite="unit",
        n_cases=100,
        n_passed=round(pass_rate * 100),
        pass_rate=pass_rate,
        policy_violations=policy_violations,
    )


def test_at_threshold_promotes_one_level() -> None:
    decision = promotion_gate(
        make_manifest(AutonomyLevel.L1_SUGGEST), make_scorecard(pass_rate=0.90)
    )
    assert decision.promote
    assert decision.to_level == AutonomyLevel.L2_ASSIST
    assert any("promoting" in r for r in decision.reasons)


def test_below_threshold_fails() -> None:
    decision = promotion_gate(
        make_manifest(AutonomyLevel.L1_SUGGEST), make_scorecard(pass_rate=0.89)
    )
    assert not decision.promote
    assert decision.to_level is None
    assert any("<" in r for r in decision.reasons)


def test_policy_violations_at_max_pass_above_fail() -> None:
    manifest = make_manifest(AutonomyLevel.L2_ASSIST, max_policy_violations=2)
    at_max = promotion_gate(manifest, make_scorecard(pass_rate=1.0, policy_violations=2))
    assert at_max.promote
    assert at_max.to_level == AutonomyLevel.L3_GATED

    above = promotion_gate(manifest, make_scorecard(pass_rate=1.0, policy_violations=3))
    assert not above.promote
    assert above.to_level is None


def test_l4_cap_blocks_automatic_promotion_to_l5() -> None:
    decision = promotion_gate(
        make_manifest(AutonomyLevel.L4_SUPERVISED), make_scorecard(pass_rate=1.0)
    )
    assert not decision.promote
    assert decision.to_level is None
    assert any("human decision" in r for r in decision.reasons)


def test_l5_never_promotes_further() -> None:
    decision = promotion_gate(
        make_manifest(AutonomyLevel.L5_AUTONOMOUS), make_scorecard(pass_rate=1.0)
    )
    assert not decision.promote
    assert decision.to_level is None


def test_l3_promotes_to_l4_when_clear() -> None:
    decision = promotion_gate(
        make_manifest(AutonomyLevel.L3_GATED), make_scorecard(pass_rate=0.95)
    )
    assert decision.promote
    assert decision.to_level == AutonomyLevel.L4_SUPERVISED


def test_both_gates_must_clear() -> None:
    decision = promotion_gate(
        make_manifest(AutonomyLevel.L1_SUGGEST),
        make_scorecard(pass_rate=0.95, policy_violations=1),
    )
    assert not decision.promote
    assert decision.to_level is None
