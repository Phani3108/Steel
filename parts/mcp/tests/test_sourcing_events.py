"""sourcing-events: state machine, role gate, deterministic scoring math."""

from __future__ import annotations

import pytest
from jai_mcp import sourcing_events as se

TENANT = "TEN-TEST"
CM = "category_manager"


def _event(role: str = CM) -> dict:
    return se.create_event(
        TENANT, role, "Bearings RFQ", "Bearings & Bushings",
        [{"sku": "BRG-00001", "qty": 100}], created_by="cm-1",
    )


def test_happy_path_full_lifecycle(pg: str) -> None:
    event = _event()
    assert event["id"].startswith("EVT-")
    assert event["status"] == "draft"

    invited = se.invite_suppliers(TENANT, CM, event["id"], ["SUP-A", "SUP-B"])
    assert invited["status"] == "invited"
    assert invited["invited"] == ["SUP-A", "SUP-B"]

    assert se.open_bidding(TENANT, CM, event["id"])["status"] == "bidding"
    assert "error" not in se.submit_bid(TENANT, event["id"], "SUP-A", 1000, 10)
    assert "error" not in se.submit_bid(TENANT, event["id"], "SUP-B", 2000, 5)
    assert len(se.list_bids(TENANT, CM, event["id"])) == 2

    ranked = se.score_bids(TENANT, CM, event["id"])
    assert se.get_event(TENANT, CM, event["id"])["status"] == "scored"

    awarded = se.award(TENANT, CM, event["id"], ranked[0]["supplier_id"], approved_by="cm-1")
    assert awarded["status"] == "awarded"
    assert awarded["awarded_supplier_id"] == ranked[0]["supplier_id"]
    assert awarded["award_total_usd"] == ranked[0]["total_usd"]
    assert awarded["approved_by"] == "cm-1"


def test_wrong_state_calls_return_errors(pg: str) -> None:
    event = _event()
    eid = event["id"]
    # draft: cannot open bidding, bid, score, or award
    assert "error" in se.open_bidding(TENANT, CM, eid)
    assert "error" in se.submit_bid(TENANT, eid, "SUP-A", 1000, 10)
    assert "error" in se.score_bids(TENANT, CM, eid)
    assert "error" in se.award(TENANT, CM, eid, "SUP-A", approved_by="cm-1")
    # invited: cannot re-invite; uninvited supplier cannot bid once open
    se.invite_suppliers(TENANT, CM, eid, ["SUP-A"])
    assert "error" in se.invite_suppliers(TENANT, CM, eid, ["SUP-B"])
    se.open_bidding(TENANT, CM, eid)
    assert "error" in se.submit_bid(TENANT, eid, "SUP-NOT-INVITED", 900, 9)
    # unknown event
    assert se.get_event(TENANT, CM, "EVT-9999") is None
    assert "error" in se.open_bidding(TENANT, CM, "EVT-9999")


def test_forbidden_role_on_create(pg: str) -> None:
    assert _event(role="requester") == {
        "error": "forbidden: role 'requester' may not manage sourcing events"
    }
    assert "error" not in _event(role="system")


def test_scoring_math_deterministic_ranking(pg: str) -> None:
    event = _event()
    eid = event["id"]
    se.invite_suppliers(TENANT, CM, eid, ["S1", "S2", "S3"])
    se.open_bidding(TENANT, CM, eid)
    se.submit_bid(TENANT, eid, "S1", 1000, 10)  # cheapest
    se.submit_bid(TENANT, eid, "S2", 2000, 5)   # fastest
    se.submit_bid(TENANT, eid, "S3", 4000, 20)  # worst on both

    ranked = se.score_bids(TENANT, CM, eid, price_weight=0.7)
    assert [r["supplier_id"] for r in ranked] == ["S1", "S2", "S3"]
    # S1: 0.7*1.0 + 0.3*0.5 = 0.85 · S2: 0.7*0.5 + 0.3*1.0 = 0.65 · S3: 0.25*(0.7+0.3) = 0.25
    assert [r["score"] for r in ranked] == [0.85, 0.65, 0.25]


def test_scoring_weight_zero_ranks_by_lead_time(pg: str) -> None:
    event = _event()
    eid = event["id"]
    se.invite_suppliers(TENANT, CM, eid, ["S1", "S2"])
    se.open_bidding(TENANT, CM, eid)
    se.submit_bid(TENANT, eid, "S1", 1000, 10)
    se.submit_bid(TENANT, eid, "S2", 2000, 5)
    ranked = se.score_bids(TENANT, CM, eid, price_weight=0.0)
    assert [r["supplier_id"] for r in ranked] == ["S2", "S1"]
    assert ranked[0]["score"] == 1.0


@pytest.mark.parametrize("bad_weight", [-0.1, 1.1])
def test_scoring_rejects_bad_weight(pg: str, bad_weight: float) -> None:
    event = _event()
    assert "error" in se.score_bids(TENANT, CM, event["id"], price_weight=bad_weight)


def test_tenant_isolation(pg: str) -> None:
    event = _event()
    assert se.get_event("TEN-OTHER", CM, event["id"]) is None
    assert "error" in se.invite_suppliers("TEN-OTHER", CM, event["id"], ["SUP-A"])
