"""Tests for jai_governor — every rule branch, no database needed."""

from __future__ import annotations

from pathlib import Path

import pytest
from jai_governor import AWARD_GATE, INTAKE_GATE, Decision, Governor, load_policy
from jai_manifest import Actor, RunContext
from pydantic import ValidationError

POLICY_VERSION = "2026.06-1"


@pytest.fixture(scope="module")
def gov() -> Governor:
    return Governor()  # default <repo>/policies/procurement.yaml


def _ctx(role: str = "category_manager") -> RunContext:
    return RunContext(tenant_id="acme", actor=Actor(id="u1", name="Pat", role=role))


# ── loader ───────────────────────────────────────────────────────────────────


def test_default_policy_loads_with_version(gov: Governor) -> None:
    assert gov.version == POLICY_VERSION
    assert gov.policy_path.name == "procurement.yaml"


def test_explicit_policy_path(tmp_path: Path) -> None:
    p = tmp_path / "custom.yaml"
    p.write_text(
        "version: 'test-1'\n"
        "approval_thresholds_usd: {requester: 100}\n"
        "three_bid_rule: {min_bids: 2, exempt_below_usd: 50}\n"
        "sourcing: {create_roles: [cpo]}\n"
        "mandate: {hard_deny_over_pct: 1.0}\n"
    )
    gov = Governor(p)
    assert gov.version == "test-1"
    assert gov.check(_ctx("cpo"), "rfx.create", {}).allowed


def test_invalid_policy_rejected(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("version: 'x'\nunexpected_key: true\n")
    with pytest.raises(ValidationError):
        load_policy(p)
    with pytest.raises(ValidationError):
        Governor(p)


# ── rfx.create ───────────────────────────────────────────────────────────────


def test_rfx_create_requester_denied(gov: Governor) -> None:
    d = gov.check(_ctx("requester"), "rfx.create", {})
    assert not d.allowed
    assert d.requires_gate is None
    assert any("sourcing.create_roles" in r for r in d.reasons)
    assert d.policy_version == POLICY_VERSION


@pytest.mark.parametrize("role", ["category_manager", "cpo", "system"])
def test_rfx_create_allowed_roles(gov: Governor, role: str) -> None:
    d = gov.check(_ctx(role), "rfx.create", {})
    assert d.allowed and d.requires_gate is None


# ── rfx.award: mandate rule ──────────────────────────────────────────────────


def test_award_over_mandate_cap_denied(gov: Governor) -> None:
    d = gov.check(
        _ctx(), "rfx.award", {"total_usd": 30_000, "n_bids": 4, "mandate_max_spend_usd": 25_000}
    )
    assert not d.allowed
    assert d.requires_gate is None
    assert any("mandate" in r and "DENY" in r for r in d.reasons)


def test_award_exactly_at_mandate_cap_allowed(gov: Governor) -> None:
    d = gov.check(
        _ctx(), "rfx.award", {"total_usd": 25_000, "n_bids": 3, "mandate_max_spend_usd": 25_000}
    )
    assert d.allowed
    assert d.requires_gate is None  # within cm ceiling too


def test_award_without_mandate_cap_rule_passes(gov: Governor) -> None:
    d = gov.check(_ctx(), "rfx.award", {"total_usd": 20_000, "n_bids": 3})
    assert d.allowed
    assert any("mandate" in r and "not applicable" in r for r in d.reasons)


# ── rfx.award: three-bid rule ────────────────────────────────────────────────


def test_award_two_bids_above_exemption_denied(gov: Governor) -> None:
    d = gov.check(_ctx(), "rfx.award", {"total_usd": 40_000, "n_bids": 2})
    assert not d.allowed
    assert any("three_bid_rule" in r and "DENY" in r for r in d.reasons)


def test_award_two_bids_below_exemption_allowed(gov: Governor) -> None:
    d = gov.check(_ctx(), "rfx.award", {"total_usd": 8_000, "n_bids": 2})
    assert d.allowed and d.requires_gate is None


def test_award_exactly_at_exemption_needs_bids(gov: Governor) -> None:
    # >= exempt_below_usd applies the rule: $10,000 with 2 bids is denied.
    d = gov.check(_ctx(), "rfx.award", {"total_usd": 10_000, "n_bids": 2})
    assert not d.allowed


def test_award_exactly_min_bids_passes(gov: Governor) -> None:
    d = gov.check(_ctx(), "rfx.award", {"total_usd": 45_000, "n_bids": 3})
    assert d.allowed and d.requires_gate is None


# ── rfx.award: approval threshold rule ───────────────────────────────────────


def test_award_above_role_threshold_requires_gate(gov: Governor) -> None:
    d = gov.check(_ctx("category_manager"), "rfx.award", {"total_usd": 120_000, "n_bids": 4})
    assert d.allowed
    assert d.requires_gate == AWARD_GATE


def test_award_exactly_at_threshold_no_gate(gov: Governor) -> None:
    d = gov.check(_ctx("category_manager"), "rfx.award", {"total_usd": 50_000, "n_bids": 3})
    assert d.allowed
    assert d.requires_gate is None


def test_award_cpo_threshold_edges(gov: Governor) -> None:
    at = gov.check(_ctx("cpo"), "rfx.award", {"total_usd": 250_000, "n_bids": 5})
    over = gov.check(_ctx("cpo"), "rfx.award", {"total_usd": 250_001, "n_bids": 5})
    assert at.allowed and at.requires_gate is None
    assert over.allowed and over.requires_gate == AWARD_GATE


def test_award_unknown_role_denied(gov: Governor) -> None:
    # 'system' has no approval threshold in the policy — deny-by-default.
    d = gov.check(_ctx("system"), "rfx.award", {"total_usd": 1_000, "n_bids": 3})
    assert not d.allowed
    assert any("no threshold" in r for r in d.reasons)


def test_award_reasons_cover_every_rule(gov: Governor) -> None:
    d = gov.check(
        _ctx(), "rfx.award", {"total_usd": 30_000, "n_bids": 2, "mandate_max_spend_usd": 25_000}
    )
    text = " ".join(d.reasons)
    assert "mandate" in text
    assert "three_bid_rule" in text
    assert "approval_thresholds_usd" in text
    assert len(d.reasons) == 3  # one reason per rule consulted, pass and fail


def test_award_missing_params_denied(gov: Governor) -> None:
    no_total = gov.check(_ctx(), "rfx.award", {"n_bids": 3})
    no_bids = gov.check(_ctx(), "rfx.award", {"total_usd": 1_000})
    bad_total = gov.check(_ctx(), "rfx.award", {"total_usd": "a lot", "n_bids": 3})
    assert not no_total.allowed and any("total_usd" in r for r in no_total.reasons)
    assert not no_bids.allowed and any("n_bids" in r for r in no_bids.reasons)
    assert not bad_total.allowed


def test_award_non_numeric_mandate_cap_denied(gov: Governor) -> None:
    d = gov.check(
        _ctx(), "rfx.award", {"total_usd": 1_000, "n_bids": 3, "mandate_max_spend_usd": "nope"}
    )
    assert not d.allowed


# ── intake.approve ───────────────────────────────────────────────────────────


def test_intake_within_threshold_no_gate(gov: Governor) -> None:
    d = gov.check(_ctx("requester"), "intake.approve", {"est_value_usd": 4_000})
    assert d.allowed and d.requires_gate is None


def test_intake_exactly_at_threshold_no_gate(gov: Governor) -> None:
    d = gov.check(_ctx("requester"), "intake.approve", {"est_value_usd": 5_000})
    assert d.allowed and d.requires_gate is None


def test_intake_above_threshold_requires_gate(gov: Governor) -> None:
    d = gov.check(_ctx("requester"), "intake.approve", {"est_value_usd": 6_000})
    assert d.allowed
    assert d.requires_gate == INTAKE_GATE


def test_intake_unknown_role_denied(gov: Governor) -> None:
    d = gov.check(_ctx("system"), "intake.approve", {"est_value_usd": 100})
    assert not d.allowed


def test_intake_missing_param_denied(gov: Governor) -> None:
    d = gov.check(_ctx("requester"), "intake.approve", {})
    assert not d.allowed
    assert any("est_value_usd" in r for r in d.reasons)


# ── deny-by-default ──────────────────────────────────────────────────────────


def test_unknown_action_denied(gov: Governor) -> None:
    d = gov.check(_ctx("cpo"), "po.create", {"total_usd": 1})
    assert not d.allowed
    assert d.requires_gate is None
    assert any("no policy for action" in r for r in d.reasons)
    assert d.policy_version == POLICY_VERSION


def test_decision_shape() -> None:
    d = Decision(allowed=True, reasons=["x"], policy_version="v")
    assert d.requires_gate is None
    assert d.model_dump() == {
        "allowed": True,
        "reasons": ["x"],
        "policy_version": "v",
        "requires_gate": None,
    }
