"""Orchestrator tests with a fake mesh and fake sourcing — no services needed."""

from pathlib import Path
from types import SimpleNamespace

from engine_fakes import FakeBlackBox
from steel_engine.orchestrate import compile_orchestrator
from steel_manifest import Actor, RunContext, load_manifest

AGENT_DIR = Path(__file__).resolve().parents[2] / "agents" / "orchestrator"


def _ctx(role="cpo"):
    return RunContext(tenant_id="TEN-1", actor=Actor(id="t", role=role))


class FakeMesh:
    """Returns canned TaskResults by skill; records the child agent it saw per dispatch."""

    def __init__(self, route="sourcing_required"):
        self.route = route
        self.calls: list[tuple[str, str]] = []  # (skill_id, from_agent)

    def dispatch(self, ctx, skill_id, input):
        self.calls.append((skill_id, ctx.agent))
        outputs = {
            "intake.triage": {"route": self.route, "reason": "fake route"},
            "risk.assess": {"summary": "fake risk: 1 adverse signal"},
            "spend.summary": {"summary": "fake spend: top cat $1M"},
        }
        return SimpleNamespace(skill_id=skill_id, agent=f"agent-{skill_id.split('.')[0]}",
                               ok=True, output=outputs.get(skill_id, {}), cost_usd=0.001,
                               error=None)


class FakeSourcing:
    def __init__(self, status="paused"):
        self.status = status
        self.ran = False

    def run(self, ctx, input_text, *, thread_id=None):
        self.ran = True
        return SimpleNamespace(status=self.status, text=f"{self.status.upper()}: fake",
                               event_id="EVT-9", thread_id="th-9", run_id=ctx.run_id)


def _orchestrator(mesh, sourcing):
    blackbox = FakeBlackBox()
    orch = compile_orchestrator(load_manifest(AGENT_DIR / "manifest.yaml"),
                                mesh=mesh, blackbox=blackbox, sourcing=sourcing)
    return orch, blackbox


def test_auto_approve_skips_specialists_and_sourcing():
    mesh = FakeMesh(route="auto_approved")
    sourcing = FakeSourcing()
    orch, blackbox = _orchestrator(mesh, sourcing)
    result = orch.run(_ctx(), {"title": "tiny", "category": "c", "est_value_usd": 1000})
    assert result.status == "auto_approved"
    assert [c[0] for c in mesh.calls] == ["intake.triage"]  # no fan-out
    assert not sourcing.ran
    assert "run.end" in blackbox.actions()


def test_sourcing_route_fans_out_under_one_agent_lineage():
    mesh = FakeMesh(route="sourcing_required")
    sourcing = FakeSourcing(status="paused")
    orch, blackbox = _orchestrator(mesh, sourcing)
    result = orch.run(_ctx(), {"title": "big", "category": "c", "est_value_usd": 120000})
    assert result.status == "paused"
    assert [c[0] for c in mesh.calls] == ["intake.triage", "risk.assess", "spend.summary"]
    # every dispatch saw the orchestrator as the caller (one lineage)
    assert {c[1] for c in mesh.calls} == {"agent-orchestrator"}
    assert sourcing.ran
    assert len(result.hops) == 4  # triage, risk, spend, sourcing
    assert set(result.memos) == {"risk", "spend"}
    assert result.event_id == "EVT-9" and result.thread_id == "th-9"
    assert blackbox.actions().count("mesh.dispatch") == 4


def test_total_cost_rolls_up_hops():
    mesh = FakeMesh()
    orch, _ = _orchestrator(mesh, FakeSourcing())
    result = orch.run(_ctx(), {"title": "big", "category": "c", "est_value_usd": 120000})
    # three mesh hops at 0.001 each; the sourcing hop is 0.0
    assert abs(result.total_cost_usd - 0.003) < 1e-9


def test_trace_id_is_shared_lineage():
    ctx = _ctx()
    orch, _ = _orchestrator(FakeMesh(), FakeSourcing())
    result = orch.run(ctx, {"title": "big", "category": "c", "est_value_usd": 120000})
    assert result.trace_id == ctx.trace_id  # the orchestration shares the caller's trace
