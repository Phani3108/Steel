"""Tests for steel_brakes — require Postgres, skip cleanly when it is unavailable."""

from __future__ import annotations

import os

import psycopg
import pytest
from steel_brakes import Brakes
from steel_manifest import Actor, RunContext

POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://steel:steel@localhost:5433/steel")


@pytest.fixture
def brakes() -> Brakes:
    try:
        conn = psycopg.connect(POSTGRES_URL, connect_timeout=2)
    except Exception:
        pytest.skip("postgres unavailable")
    conn.close()
    b = Brakes(POSTGRES_URL)
    b.ensure_schema()
    with psycopg.connect(POSTGRES_URL) as conn:
        conn.execute("TRUNCATE brakes.approvals, brakes.kill_switch")
    return b


def _ctx(tenant_id: str = "acme", agent: str | None = "agent-sourcing") -> RunContext:
    return RunContext(
        tenant_id=tenant_id,
        actor=Actor(id="u-req", name="Pat", role="requester"),
        agent=agent,
    )


def test_request_pending_approve_flow(brakes: Brakes) -> None:
    ctx = _ctx()
    payload = {"po_total_usd": 12400, "supplier": "S-001"}
    approval_id = brakes.request(ctx, gate="po-approval", thread_id="t-1", payload=payload)
    assert isinstance(approval_id, int)

    rows = brakes.pending()
    assert [r["id"] for r in rows] == [approval_id]
    row = rows[0]
    assert row["tenant_id"] == "acme"
    assert row["gate"] == "po-approval"
    assert row["agent"] == "agent-sourcing"
    assert row["run_id"] == ctx.run_id
    assert row["thread_id"] == "t-1"
    assert row["requested_by"] == "u-req"
    assert row["payload"] == payload
    assert row["status"] == "pending"
    assert row["decided_by"] is None and row["decided_at"] is None
    assert row["ts"].tzinfo is not None

    decided = brakes.decide(approval_id, approver="u-cm", approve=True, note="within budget")
    assert decided["status"] == "approved"
    assert decided["decided_by"] == "u-cm"
    assert decided["decided_at"] is not None
    assert decided["note"] == "within budget"

    assert brakes.pending() == []
    got = brakes.get(approval_id)
    assert got is not None and got["status"] == "approved"


def test_reject_flow(brakes: Brakes) -> None:
    approval_id = brakes.request(_ctx(), gate="po-approval", thread_id="t-2", payload={})
    decided = brakes.decide(approval_id, approver="u-cm", approve=False, note="over threshold")
    assert decided["status"] == "rejected"
    assert decided["note"] == "over threshold"
    assert brakes.pending() == []


def test_double_decide_raises(brakes: Brakes) -> None:
    approval_id = brakes.request(_ctx(), gate="po-approval", thread_id="t-3", payload={})
    brakes.decide(approval_id, approver="u-cm", approve=True)
    with pytest.raises(ValueError, match="already decided"):
        brakes.decide(approval_id, approver="u-cm", approve=False)
    row = brakes.get(approval_id)
    assert row is not None and row["status"] == "approved"  # first decision stands


def test_decide_unknown_id_raises(brakes: Brakes) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        brakes.decide(999_999, approver="u-cm", approve=True)


def test_get_unknown_id_returns_none(brakes: Brakes) -> None:
    assert brakes.get(999_999) is None


def test_decision_for_returns_latest_for_thread_and_gate(brakes: Brakes) -> None:
    ctx = _ctx()
    assert brakes.decision_for("t-4", "po-approval") is None

    first = brakes.request(ctx, gate="po-approval", thread_id="t-4", payload={"try": 1})
    assert brakes.decision_for("t-4", "po-approval") is None  # pending does not count

    brakes.decide(first, approver="u-cm", approve=False, note="resubmit")
    second = brakes.request(ctx, gate="po-approval", thread_id="t-4", payload={"try": 2})
    brakes.decide(second, approver="u-cm", approve=True)

    latest = brakes.decision_for("t-4", "po-approval")
    assert latest is not None
    assert latest["id"] == second
    assert latest["status"] == "approved"

    # Other gates and threads stay isolated.
    assert brakes.decision_for("t-4", "other-gate") is None
    assert brakes.decision_for("t-other", "po-approval") is None


def test_pending_is_newest_first_and_filters_by_tenant(brakes: Brakes) -> None:
    a = brakes.request(_ctx("acme"), gate="g", thread_id="t-a", payload={})
    b = brakes.request(_ctx("globex"), gate="g", thread_id="t-b", payload={})
    c = brakes.request(_ctx("acme"), gate="g", thread_id="t-c", payload={})

    assert [r["id"] for r in brakes.pending()] == [c, b, a]
    assert [r["id"] for r in brakes.pending("acme")] == [c, a]
    assert [r["id"] for r in brakes.pending("globex")] == [b]
    assert brakes.pending("initech") == []


def test_kill_is_killed_revive(brakes: Brakes) -> None:
    assert brakes.is_killed("agent-sourcing") is False  # missing row -> False

    brakes.kill("agent-sourcing", by="u-cpo", reason="runaway spend")
    assert brakes.is_killed("agent-sourcing") is True
    assert brakes.is_killed("agent-intake") is False  # per-agent isolation

    with psycopg.connect(POSTGRES_URL) as conn:
        row = conn.execute(
            'SELECT killed, "by", reason, ts FROM brakes.kill_switch WHERE agent = %s',
            ("agent-sourcing",),
        ).fetchone()
    assert row is not None
    assert row[0] is True and row[1] == "u-cpo" and row[2] == "runaway spend"
    assert row[3].tzinfo is not None

    brakes.kill("agent-sourcing", by="u-cpo", reason="still bad")  # kill is idempotent upsert
    assert brakes.is_killed("agent-sourcing") is True

    brakes.revive("agent-sourcing", by="u-cpo")
    assert brakes.is_killed("agent-sourcing") is False

    with psycopg.connect(POSTGRES_URL) as conn:
        row = conn.execute(
            'SELECT killed, "by", reason FROM brakes.kill_switch WHERE agent = %s',
            ("agent-sourcing",),
        ).fetchone()
    assert row is not None
    assert row[0] is False and row[1] == "u-cpo" and row[2] is None
