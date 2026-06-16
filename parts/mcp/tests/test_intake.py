"""intake: triage thresholds (the $5,000 requester limit, boundary inclusive)."""

from __future__ import annotations

from steel_mcp import intake

TENANT = "TEN-TEST"


def _submit(value: float) -> dict:
    return intake.submit_request(
        TENANT, "requester", "req-1", "Test req", "desc", "MRO & Spares", value
    )


def test_triage_threshold_edge_5000_exactly_auto_approves(pg: str) -> None:
    assert _submit(5000)["status"] == "auto_approved"
    assert _submit(5000.01)["status"] == "sourcing_required"
    assert _submit(0)["status"] == "auto_approved"
    assert "error" in _submit(-1)


def test_request_ids_and_listing(pg: str) -> None:
    a = _submit(100)
    b = _submit(99_000)
    assert a["id"].startswith("REQ-") and b["id"].startswith("REQ-")
    assert a["id"] != b["id"]

    all_reqs = intake.list_requests(TENANT, "requester")
    assert {r["id"] for r in all_reqs} >= {a["id"], b["id"]}
    escalated = intake.list_requests(TENANT, "requester", status="sourcing_required")
    assert [r["id"] for r in escalated] == [b["id"]]

    fetched = intake.get_request(TENANT, "requester", a["id"])
    assert fetched["est_value_usd"] == 100
    assert intake.get_request("TEN-OTHER", "requester", a["id"]) is None
