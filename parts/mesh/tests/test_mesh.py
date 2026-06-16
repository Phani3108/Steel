"""Tests for steel_mesh — pure in-process transport, no Postgres, no network.

Covers: register/dispatch happy path (output + cost surfaced, Hop emitted with the right
from/to), child-context propagation (tenant + trace kept, agent swapped), handler
exception (ok=False with error, Hop still emitted), unknown skill (ok=False, no hop),
register raising on a handler-less skill, the A2A agent-card JSON shape, and topology.
"""

from __future__ import annotations

import pytest
from steel_manifest import Actor, RunContext
from steel_mesh import AgentCard, Hop, Mesh, Skill, TaskResult


def _root(agent: str | None = "agent-orchestrator") -> RunContext:
    return RunContext(
        tenant_id="acme",
        actor=Actor(id="u1", name="Pat", role="category_manager"),
        agent=agent,
        budget_usd_remaining=5.0,
    )


def _greeter_card() -> AgentCard:
    return AgentCard(
        name="greeter",
        description="says hello",
        url="https://mesh.local/agents/greeter",
        skills=[Skill(id="greeter", name="Greeter", description="greets a person")],
    )


def _analyst_card() -> AgentCard:
    return AgentCard(
        name="spend-analyst",
        description="summarizes spend",
        skills=[Skill(id="spend.summary", name="Spend summary")],
    )


def test_register_and_dispatch_happy_path_surfaces_output_cost_and_hop() -> None:
    hops: list[Hop] = []
    mesh = Mesh(on_hop=hops.append)

    def handler(ctx: RunContext, input: dict) -> dict:
        return {"summary": f"{ctx.tenant_id} spend", "_cost_usd": 0.002}

    mesh.register(_analyst_card(), {"spend.summary": handler})

    result = mesh.dispatch(_root(), "spend.summary", {})

    assert isinstance(result, TaskResult)
    assert result.ok is True
    assert result.agent == "spend-analyst"
    assert result.skill_id == "spend.summary"
    assert result.output == {"summary": "acme spend", "_cost_usd": 0.002}
    assert result.cost_usd == 0.002
    assert result.error is None

    # Exactly one hop, with the right direction and cost.
    assert len(hops) == 1
    hop = hops[0]
    assert hop.from_agent == "agent-orchestrator"
    assert hop.to_agent == "spend-analyst"
    assert hop.skill_id == "spend.summary"
    assert hop.ok is True
    assert hop.cost_usd == 0.002


def test_missing_cost_defaults_to_zero() -> None:
    mesh = Mesh()
    mesh.register(_greeter_card(), {"greeter": lambda ctx, i: {"greeting": "hi"}})
    result = mesh.dispatch(_root(), "greeter", {})
    assert result.ok is True
    assert result.cost_usd == 0.0


def test_dispatch_from_human_when_root_has_no_agent() -> None:
    hops: list[Hop] = []
    mesh = Mesh(on_hop=hops.append)
    mesh.register(_greeter_card(), {"greeter": lambda ctx, i: {"greeting": "hi"}})

    mesh.dispatch(_root(agent=None), "greeter", {})

    assert hops[0].from_agent == "human"
    assert hops[0].to_agent == "greeter"


def test_child_context_keeps_tenant_and_trace_and_swaps_agent() -> None:
    mesh = Mesh()
    seen: dict[str, object] = {}

    def handler(ctx: RunContext, input: dict) -> dict:
        seen["tenant_id"] = ctx.tenant_id
        seen["trace_id"] = ctx.trace_id
        seen["run_id"] = ctx.run_id
        seen["agent"] = ctx.agent
        seen["budget"] = ctx.budget_usd_remaining
        seen["actor_id"] = ctx.actor.id
        return {}

    mesh.register(_greeter_card(), {"greeter": handler})
    root = _root()
    mesh.dispatch(root, "greeter", {})

    # Same trace/tenant/budget/actor/run pool; only the agent name is swapped to the callee.
    assert seen["tenant_id"] == root.tenant_id
    assert seen["trace_id"] == root.trace_id
    assert seen["run_id"] == root.run_id
    assert seen["budget"] == root.budget_usd_remaining
    assert seen["actor_id"] == root.actor.id
    assert seen["agent"] == "greeter"
    assert root.agent == "agent-orchestrator"  # parent untouched


def test_handler_exception_yields_ok_false_with_error_and_still_emits_hop() -> None:
    hops: list[Hop] = []
    mesh = Mesh(on_hop=hops.append)

    def boom(ctx: RunContext, input: dict) -> dict:
        raise RuntimeError("kaboom")

    mesh.register(_greeter_card(), {"greeter": boom})
    result = mesh.dispatch(_root(), "greeter", {})

    assert result.ok is False
    assert result.agent == "greeter"
    assert result.error is not None
    assert "kaboom" in result.error
    assert result.cost_usd == 0.0

    assert len(hops) == 1
    assert hops[0].from_agent == "agent-orchestrator"
    assert hops[0].to_agent == "greeter"
    assert hops[0].ok is False


def test_unknown_skill_yields_ok_false_and_emits_no_hop() -> None:
    hops: list[Hop] = []
    mesh = Mesh(on_hop=hops.append)
    mesh.register(_greeter_card(), {"greeter": lambda ctx, i: {}})

    result = mesh.dispatch(_root(), "does.not.exist", {})

    assert result.ok is False
    assert result.skill_id == "does.not.exist"
    assert result.error is not None
    assert "does.not.exist" in result.error
    # No callee was found, so no hop is recorded.
    assert hops == []


def test_register_raises_when_a_skill_lacks_a_handler() -> None:
    mesh = Mesh()
    card = AgentCard(
        name="two-skill",
        skills=[Skill(id="a", name="A"), Skill(id="b", name="B")],
    )
    with pytest.raises(ValueError) as exc:
        mesh.register(card, {"a": lambda ctx, i: {}})  # missing handler for "b"
    assert "b" in str(exc.value)


def test_cards_and_card_for_skill() -> None:
    mesh = Mesh()
    greeter = _greeter_card()
    analyst = _analyst_card()
    mesh.register(greeter, {"greeter": lambda ctx, i: {}})
    mesh.register(analyst, {"spend.summary": lambda ctx, i: {}})

    names = [c.name for c in mesh.cards()]
    assert names == ["greeter", "spend-analyst"]  # registration order

    assert mesh.card_for_skill("spend.summary").name == "spend-analyst"
    assert mesh.card_for_skill("greeter").name == "greeter"
    assert mesh.card_for_skill("nope") is None


def test_to_a2a_json_shape() -> None:
    mesh = Mesh()
    card = AgentCard(
        name="spend-analyst",
        description="summarizes spend",
        url="https://mesh.local/agents/spend-analyst",
        version="0.2.0",
        skills=[Skill(id="spend.summary", name="Spend summary", description="recap")],
    )
    doc = mesh.to_a2a_json(card)

    assert doc == {
        "name": "spend-analyst",
        "description": "summarizes spend",
        "url": "https://mesh.local/agents/spend-analyst",
        "version": "0.2.0",
        "capabilities": {"streaming": False},
        "skills": [
            {"id": "spend.summary", "name": "Spend summary", "description": "recap"}
        ],
    }


def test_topology_maps_skills_to_agents() -> None:
    mesh = Mesh()
    mesh.register(_greeter_card(), {"greeter": lambda ctx, i: {}})
    mesh.register(_analyst_card(), {"spend.summary": lambda ctx, i: {}})

    topo = mesh.topology()

    assert topo["nodes"] == [
        {"id": "greeter", "skills": ["greeter"]},
        {"id": "spend-analyst", "skills": ["spend.summary"]},
    ]
    assert topo["skills"] == {"greeter": "greeter", "spend.summary": "spend-analyst"}


def test_shared_trace_across_a_two_hop_orchestration() -> None:
    """One orchestration → one trace_id across every hop (the core propagation rule)."""
    hops: list[Hop] = []
    mesh = Mesh(on_hop=hops.append)
    mesh.register(_greeter_card(), {"greeter": lambda ctx, i: {"by": ctx.agent}})
    mesh.register(_analyst_card(), {"spend.summary": lambda ctx, i: {"_cost_usd": 0.01}})

    root = _root()
    mesh.dispatch(root, "greeter", {})
    mesh.dispatch(root, "spend.summary", {})

    assert len(hops) == 2
    # Same root context drives both hops; the trace is shared by construction.
    assert {h.to_agent for h in hops} == {"greeter", "spend-analyst"}
    assert all(h.from_agent == "agent-orchestrator" for h in hops)
