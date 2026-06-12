"""jai-governor engine — deterministic pre-action policy checks.

The governor never reasons and never calls a model: it evaluates fixed rules from a
versioned YAML policy against a ``RunContext`` and action params. Every rule consulted
leaves one human-readable reason — pass or fail — so the caller can audit exactly why
an action was allowed, gated, or denied. Unknown actions and unknown roles are denied:
deny-by-default is the point.
"""

from __future__ import annotations

from pathlib import Path

from jai_manifest import RunContext
from pydantic import BaseModel

from jai_governor.policy import PolicyFile, default_policy_path, load_policy

AWARD_GATE = "award_approval"
INTAKE_GATE = "intake_escalation"


class Decision(BaseModel):
    """The auditable outcome of one policy check."""

    allowed: bool
    reasons: list[str]  # human-readable, one per rule evaluated
    policy_version: str
    requires_gate: str | None = None  # HITL gate name that must approve before proceeding


def _number(params: dict, key: str) -> tuple[float | None, str | None]:
    """Pull a required numeric param. Returns (value, error_reason)."""
    value = params.get(key)
    if value is None:
        return None, f"params: required numeric '{key}' missing — denied by default"
    try:
        return float(value), None
    except (TypeError, ValueError):
        return None, f"params: '{key}'={value!r} is not a number — denied by default"


class Governor:
    """Versioned policy engine. Construct once, call ``check`` before every action."""

    def __init__(self, policy_path: str | Path | None = None) -> None:
        path = Path(policy_path) if policy_path is not None else default_policy_path()
        self._policy: PolicyFile = load_policy(path)
        self._policy_path = path

    @property
    def version(self) -> str:
        return self._policy.version

    @property
    def policy_path(self) -> Path:
        return self._policy_path

    def check(self, ctx: RunContext, action: str, params: dict) -> Decision:
        """Evaluate every rule the policy has for ``action``. Deny-by-default."""
        if action == "rfx.create":
            return self._check_rfx_create(ctx)
        if action == "rfx.award":
            return self._check_rfx_award(ctx, params)
        if action == "intake.approve":
            return self._check_intake_approve(ctx, params)
        return self._decision(
            allowed=False,
            reasons=[f"no policy for action '{action}' — denied by default"],
        )

    # ── rules ────────────────────────────────────────────────────────────────

    def _check_rfx_create(self, ctx: RunContext) -> Decision:
        roles = self._policy.sourcing.create_roles
        role = ctx.actor.role
        if role in roles:
            return self._decision(
                allowed=True,
                reasons=[f"sourcing.create_roles: role '{role}' may create sourcing events — pass"],
            )
        return self._decision(
            allowed=False,
            reasons=[
                f"sourcing.create_roles: role '{role}' not in {roles} — DENY"
            ],
        )

    def _check_rfx_award(self, ctx: RunContext, params: dict) -> Decision:
        total, err = _number(params, "total_usd")
        if err or total is None:
            return self._decision(allowed=False, reasons=[err or "params: bad total_usd"])
        n_bids, err = _number(params, "n_bids")
        if err or n_bids is None:
            return self._decision(allowed=False, reasons=[err or "params: bad n_bids"])

        reasons: list[str] = []
        denied = False
        gate: str | None = None

        # Rule 1 — mandate: a hard cap the agent carries; over it is denied outright.
        cap_raw = params.get("mandate_max_spend_usd")
        if cap_raw is None:
            reasons.append("mandate: no mandate cap on this run — rule not applicable, pass")
        else:
            try:
                cap = float(cap_raw)
            except (TypeError, ValueError):
                denied = True
                reasons.append(
                    f"mandate: mandate_max_spend_usd={cap_raw!r} is not a number — DENY"
                )
            else:
                pct = self._policy.mandate.hard_deny_over_pct
                limit = cap * pct
                if total > limit:
                    denied = True
                    reasons.append(
                        f"mandate: total ${total:,.2f} exceeds mandate cap ${cap:,.2f} "
                        f"(hard deny over {pct:.0%} of cap) — DENY"
                    )
                else:
                    reasons.append(
                        f"mandate: total ${total:,.2f} within mandate cap ${cap:,.2f} — pass"
                    )

        # Rule 2 — three-bid: competitive bidding floor above the exemption.
        tb = self._policy.three_bid_rule
        if total < tb.exempt_below_usd:
            reasons.append(
                f"three_bid_rule: total ${total:,.2f} below ${tb.exempt_below_usd:,.2f} "
                "exemption — pass"
            )
        elif n_bids >= tb.min_bids:
            reasons.append(
                f"three_bid_rule: {int(n_bids)} bids >= required {tb.min_bids} — pass"
            )
        else:
            denied = True
            reasons.append(
                f"three_bid_rule: only {int(n_bids)} bids for ${total:,.2f} "
                f"(>= ${tb.exempt_below_usd:,.2f} needs {tb.min_bids}) — DENY"
            )

        # Rule 3 — approval threshold: above the actor's ceiling a human gate signs.
        thresholds = self._policy.approval_thresholds_usd
        role = ctx.actor.role
        if role not in thresholds:
            denied = True
            reasons.append(
                f"approval_thresholds_usd: no threshold defined for role '{role}' — DENY"
            )
        else:
            ceiling = thresholds[role]
            if total > ceiling:
                gate = AWARD_GATE
                reasons.append(
                    f"approval_thresholds_usd: total ${total:,.2f} exceeds role '{role}' "
                    f"ceiling ${ceiling:,.2f} — requires gate '{AWARD_GATE}'"
                )
            else:
                reasons.append(
                    f"approval_thresholds_usd: total ${total:,.2f} within role '{role}' "
                    f"ceiling ${ceiling:,.2f} — pass, no gate"
                )

        if denied:
            return self._decision(allowed=False, reasons=reasons)
        return self._decision(allowed=True, reasons=reasons, requires_gate=gate)

    def _check_intake_approve(self, ctx: RunContext, params: dict) -> Decision:
        est, err = _number(params, "est_value_usd")
        if err or est is None:
            return self._decision(allowed=False, reasons=[err or "params: bad est_value_usd"])

        thresholds = self._policy.approval_thresholds_usd
        role = ctx.actor.role
        if role not in thresholds:
            return self._decision(
                allowed=False,
                reasons=[
                    f"approval_thresholds_usd: no threshold defined for role '{role}' — DENY"
                ],
            )
        ceiling = thresholds[role]
        if est <= ceiling:
            return self._decision(
                allowed=True,
                reasons=[
                    f"approval_thresholds_usd: estimated ${est:,.2f} within role '{role}' "
                    f"ceiling ${ceiling:,.2f} — pass, no gate"
                ],
            )
        return self._decision(
            allowed=True,
            reasons=[
                f"approval_thresholds_usd: estimated ${est:,.2f} exceeds role '{role}' "
                f"ceiling ${ceiling:,.2f} — requires gate '{INTAKE_GATE}'"
            ],
            requires_gate=INTAKE_GATE,
        )

    # ── plumbing ─────────────────────────────────────────────────────────────

    def _decision(
        self, *, allowed: bool, reasons: list[str], requires_gate: str | None = None
    ) -> Decision:
        return Decision(
            allowed=allowed,
            reasons=reasons,
            policy_version=self._policy.version,
            requires_gate=requires_gate,
        )
