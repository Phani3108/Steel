"""Negotiator tests — fake mesh seller + fake governor, no services."""

from pathlib import Path
from types import SimpleNamespace

from engine_fakes import FakeBlackBox
from steel_engine.negotiate import compile_negotiator
from steel_manifest import Actor, RunContext, load_manifest

AGENT_DIR = Path(__file__).resolve().parents[2] / "agents" / "negotiator"


def _ctx():
    return RunContext(tenant_id="TEN-1", actor=Actor(id="t", role="cpo"))


class FakeSellerMesh:
    """A seller that concedes from list toward a floor and accepts at/above it."""

    def __init__(self, floor_pct, step_pct=0.02):
        self.floor_pct, self.step_pct = floor_pct, step_pct

    def dispatch(self, ctx, skill_id, input):
        list_price = float(input["list_price"])
        offer = float(input["offer"])
        rnd = int(input["round"])
        floor = list_price * self.floor_pct
        counter = max(floor, list_price * (1.0 - self.step_pct * rnd))
        return SimpleNamespace(skill_id=skill_id, agent="seller", ok=True, error=None,
                               cost_usd=0.0, output={"counter_price": round(counter, 2),
                               "accept": offer >= floor, "persona": "FakeSeller"})


class FakeGovernor:
    def __init__(self, allow=True):
        self.allow = allow

    def check(self, ctx, action, params):
        return SimpleNamespace(allowed=self.allow, reasons=["fake"], policy_version="t",
                               requires_gate=None)


def _negotiator(mesh, governor=None):
    return compile_negotiator(load_manifest(AGENT_DIR / "manifest.yaml"), mesh=mesh,
                              blackbox=FakeBlackBox(), governor=governor or FakeGovernor())


def _deal(list_price):
    return {"list_price": list_price, "seller_skill": "negotiate.fake"}


def test_closes_within_zopa_with_savings():
    # floor 90% of list; cap is $150k (manifest), list $100k → ceiling = walkaway 95k
    n = _negotiator(FakeSellerMesh(floor_pct=0.90))
    r = n.run(_ctx(), _deal(100_000))
    assert r.status == "deal"
    assert r.final_price is not None and r.final_price <= 95_000.0  # within walkaway
    assert r.savings_pct > 0
    assert not r.breached


def test_walks_when_only_deals_exceed_hard_cap():
    # list $200k, manifest cap $150k. Seller floor 95% = $190k > ceiling $150k → walk.
    n = _negotiator(FakeSellerMesh(floor_pct=0.95))
    r = n.run(_ctx(), _deal(200_000))
    assert r.status in ("walked", "no_deal")
    assert r.final_price is None
    assert not r.breached  # never closed above the cap


def test_never_offers_above_the_ceiling():
    n = _negotiator(FakeSellerMesh(floor_pct=0.99))
    r = n.run(_ctx(), _deal(200_000))
    cap = r.mandate_cap
    assert all(t["offer"] <= cap for t in r.transcript)  # mandate clamp holds every round


def test_governor_backstop_blocks_a_close():
    # The seller would accept, but the governor denies the award → the close is stopped.
    n = _negotiator(FakeSellerMesh(floor_pct=0.80), governor=FakeGovernor(allow=False))
    r = n.run(_ctx(), _deal(100_000))
    assert r.status == "walked"
    assert r.final_price is None and not r.breached
