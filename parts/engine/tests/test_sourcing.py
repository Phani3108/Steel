"""Sourcing pipeline tests with fake governor/brakes/tools — Postgres needed only for
the checkpointer (connect-or-skip)."""

import json
import os
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest
from engine_fakes import FakeBlackBox
from jai_engine.sourcing import compile_sourcing
from jai_manifest import Actor, RunContext, load_manifest

AGENT_DIR = Path(__file__).resolve().parents[2] / "agents" / "sourcing"
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://jai:jai@localhost:5433/jai")

def _pg() -> bool:
    try:
        psycopg.connect(POSTGRES_URL, connect_timeout=2).close()
        return True
    except (psycopg.Error, OSError):
        return False


pytestmark = pytest.mark.skipif(
    not _pg(), reason="postgres unavailable (sourcing needs the checkpointer)"
)


class FakeGovernor:
    def __init__(self, *, allow=True, gate=None):
        self.allow, self.gate = allow, gate
        self.checked: list[str] = []

    def check(self, ctx, action, params):
        self.checked.append(action)
        return SimpleNamespace(allowed=self.allow, reasons=[f"fake:{action}"],
                               policy_version="test-1", requires_gate=self.gate)


class FakeBrakes:
    def __init__(self):
        self.requests: list[dict] = []
        self.decisions: dict[tuple[str, str], dict] = {}
        self.killed: set[str] = set()

    def request(self, ctx, *, gate, thread_id, payload):
        self.requests.append({"gate": gate, "thread_id": thread_id, "tenant_id": ctx.tenant_id,
                              "id": len(self.requests) + 1, "payload": payload})
        return len(self.requests)

    def pending(self, tenant_id=None):
        return [r for r in self.requests
                if (r["thread_id"], r["gate"]) not in self.decisions]

    def decision_for(self, thread_id, gate):
        return self.decisions.get((thread_id, gate))

    def approve(self, thread_id, gate, by="tester"):
        self.decisions[(thread_id, gate)] = {"status": "approved", "decided_by": by}

    def reject(self, thread_id, gate, by="tester"):
        self.decisions[(thread_id, gate)] = {"status": "rejected", "decided_by": by}

    def is_killed(self, agent):
        return agent in self.killed


def _fake_tools():
    events: dict[str, dict] = {}
    bids: dict[str, list[dict]] = {}

    def create_event(tenant_id, role, title, category, line_items, created_by):
        eid = f"EVT-T{len(events) + 1}"
        events[eid] = {"id": eid, "status": "draft", "invited": []}
        return events[eid]

    def invite(tenant_id, role, event_id, supplier_ids):
        events[event_id].update(status="invited", invited=supplier_ids)
        return events[event_id]

    def open_bidding(tenant_id, role, event_id):
        events[event_id]["status"] = "bidding"
        return events[event_id]

    def submit_bid(tenant_id, event_id, supplier_id, total_usd, lead_time_days):
        bids.setdefault(event_id, []).append(
            {"supplier_id": supplier_id, "total_usd": total_usd,
             "lead_time_days": lead_time_days})
        return {"ok": True}

    def score(tenant_id, role, event_id, price_weight=0.7):
        ranked = sorted(bids.get(event_id, []), key=lambda b: b["total_usd"])
        events[event_id]["status"] = "scored"
        return ranked

    def award(tenant_id, role, event_id, supplier_id, approved_by):
        events[event_id].update(status="awarded", awarded_supplier_id=supplier_id)
        return events[event_id]

    def get_event(tenant_id, role, event_id):
        return events.get(event_id)

    return {
        "sourcing-events": {"create_event": create_event, "invite_suppliers": invite,
                            "open_bidding": open_bidding, "submit_bid": submit_bid,
                            "score_bids": score, "award": award, "get_event": get_event},
        "supplier-master": {"search_suppliers": lambda tenant_id, role, **kw: [
            {"id": f"SUP-T{i}"} for i in range(1, 5)]},
    }


INTAKE = json.dumps({"title": "t", "category": "c", "line_items": [], "est_value_usd": 1000.0,
                     "requested_by": "u"})


def _ctx(role="category_manager"):
    return RunContext(tenant_id="TEN-T", actor=Actor(id="t", role=role))


def _agent(governor=None, brakes=None):
    blackbox = FakeBlackBox()
    agent = compile_sourcing(
        load_manifest(AGENT_DIR / "manifest.yaml"),
        blackbox=blackbox, governor=governor or FakeGovernor(),
        brakes=brakes or FakeBrakes(), tools=_fake_tools(),
    )
    return agent, blackbox


def test_full_lifecycle_with_both_gates():
    governor = FakeGovernor(gate="award_approval")
    brakes = FakeBrakes()
    agent, blackbox = _agent(governor, brakes)
    try:
        r1 = agent.run(_ctx(), INTAKE)
        assert r1.status == "paused" and r1.gate == "rfx_publish"
        assert brakes.requests[-1]["gate"] == "rfx_publish"

        brakes.approve(r1.thread_id, "rfx_publish")
        r2 = agent.resume(_ctx(), thread_id=r1.thread_id)
        assert r2.status == "paused" and r2.gate == "award_approval"

        brakes.approve(r1.thread_id, "award_approval")
        r3 = agent.resume(_ctx(), thread_id=r1.thread_id)
        assert r3.status == "complete" and r3.text.startswith("AWARDED:")
        assert governor.checked == ["rfx.create", "rfx.award"]
        assert "run.pause" in blackbox.actions() and "run.end" in blackbox.actions()
    finally:
        agent.close()


def test_gate_rejection_halts():
    brakes = FakeBrakes()
    agent, _ = _agent(FakeGovernor(), brakes)
    try:
        r1 = agent.run(_ctx(), INTAKE)
        brakes.reject(r1.thread_id, "rfx_publish")
        r2 = agent.resume(_ctx(), thread_id=r1.thread_id)
        assert r2.status == "rejected" and "rfx_publish" in r2.text
    finally:
        agent.close()


def test_governor_denial_short_circuits():
    agent, blackbox = _agent(FakeGovernor(allow=False))
    try:
        result = agent.run(_ctx(), INTAKE)
        assert result.status == "denied" and result.text.startswith("DENIED:")
        assert ("run.end", "denied") in [(e.action, e.outcome) for e in blackbox.events]
    finally:
        agent.close()


def test_kill_switch_stops_run():
    brakes = FakeBrakes()
    brakes.killed.add("agent-sourcing")
    agent, blackbox = _agent(FakeGovernor(), brakes)
    try:
        result = agent.run(_ctx(), INTAKE)
        assert result.status == "killed"
        assert "kill_switch" in blackbox.actions()
    finally:
        agent.close()


def test_invalid_intake_denied():
    agent, _ = _agent()
    try:
        result = agent.run(_ctx(), "not json at all")
        assert result.status == "denied" and "invalid intake" in result.text
    finally:
        agent.close()
