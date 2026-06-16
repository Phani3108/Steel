"""Scorecard — the published result of a dyno run, and the autonomy promotion gate.

An agent is promoted when it proves itself on the bench, never by editing its manifest:
one level up, only if the scorecard clears the manifest's metric targets, and never
above L4 automatically — the jump to L5 is a human decision by definition.
"""

from __future__ import annotations

from datetime import UTC, datetime

from steel_manifest import AgentManifest, AutonomyLevel
from pydantic import BaseModel, Field


class CaseFailure(BaseModel):
    case_id: str
    reason: str


class Scorecard(BaseModel):
    """What a suite run proved about an agent. No scorecard, no ship."""

    agent: str
    suite: str
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    n_cases: int
    n_passed: int
    pass_rate: float
    failures: list[CaseFailure] = Field(default_factory=list)
    policy_violations: int = 0
    cost_usd_total: float = 0.0


class PromotionDecision(BaseModel):
    promote: bool
    to_level: AutonomyLevel | None
    reasons: list[str]


# Automatic promotion never exceeds this level; L5 requires a human decision.
AUTO_PROMOTION_CAP = AutonomyLevel.L4_SUPERVISED


def promotion_gate(manifest: AgentManifest, scorecard: Scorecard) -> PromotionDecision:
    """Decide whether the scorecard earns the agent one autonomy level."""
    targets = manifest.metrics
    reasons: list[str] = []
    cleared = True

    if scorecard.pass_rate >= targets.eval_pass_rate:
        reasons.append(
            f"pass_rate {scorecard.pass_rate:.4f} >= target {targets.eval_pass_rate:.4f}"
        )
    else:
        cleared = False
        reasons.append(
            f"pass_rate {scorecard.pass_rate:.4f} < target {targets.eval_pass_rate:.4f}"
        )

    if scorecard.policy_violations <= targets.max_policy_violations:
        reasons.append(
            f"policy_violations {scorecard.policy_violations}"
            f" <= max {targets.max_policy_violations}"
        )
    else:
        cleared = False
        reasons.append(
            f"policy_violations {scorecard.policy_violations}"
            f" > max {targets.max_policy_violations}"
        )

    current = manifest.autonomy_level
    if current >= AUTO_PROMOTION_CAP:
        reasons.append(
            f"{current.name} is at or above the {AUTO_PROMOTION_CAP.name} automatic"
            " promotion cap; promotion to L5 is a human decision"
        )
        return PromotionDecision(promote=False, to_level=None, reasons=reasons)

    if not cleared:
        return PromotionDecision(promote=False, to_level=None, reasons=reasons)

    to_level = AutonomyLevel(current + 1)
    reasons.append(f"promoting {current.name} -> {to_level.name}")
    return PromotionDecision(promote=True, to_level=to_level, reasons=reasons)
