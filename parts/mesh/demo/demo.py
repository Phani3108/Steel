"""Standalone steel-mesh demo: register two toy agents on the CAN bus, dispatch each from a
root run context, and print the results, the recorded hops, one A2A agent-card JSON, and
the network topology.

No database, no network — pure in-process transport.

Run: python parts/mesh/demo/demo.py
"""

from __future__ import annotations

import json
import sys

from steel_manifest import Actor, RunContext
from steel_mesh import AgentCard, Hop, Mesh, Skill


def greeter_handler(ctx: RunContext, input: dict) -> dict:
    # Handlers receive a child RunContext: same tenant/actor/trace, agent name swapped.
    name = input.get("name", "world")
    return {"greeting": f"Hello, {name}!", "by": ctx.agent}


def spend_summary_handler(ctx: RunContext, input: dict) -> dict:
    tenant = ctx.tenant_id
    return {
        "summary": f"{tenant}: $1.2M committed across 14 suppliers this quarter.",
        "_cost_usd": 0.002,  # surfaced to TaskResult.cost_usd by the mesh
    }


def main() -> int:
    hops: list[Hop] = []
    mesh = Mesh(on_hop=hops.append)

    greeter = AgentCard(
        name="greeter",
        description="says hello",
        url="https://mesh.local/agents/greeter",
        version="0.1.0",
        skills=[Skill(id="greeter", name="Greeter", description="greets a person by name")],
    )
    analyst = AgentCard(
        name="spend-analyst",
        description="summarizes spend",
        url="https://mesh.local/agents/spend-analyst",
        skills=[
            Skill(id="spend.summary", name="Spend summary", description="quarterly spend recap")
        ],
    )

    mesh.register(greeter, {"greeter": greeter_handler})
    mesh.register(analyst, {"spend.summary": spend_summary_handler})

    # One root context — its trace_id is shared across every hop below.
    root = RunContext(
        tenant_id="acme",
        actor=Actor(id="u-demo", name="Pat", role="category_manager"),
        agent="agent-orchestrator",
        budget_usd_remaining=5.0,
    )

    print(f"root trace_id: {root.trace_id}\n")

    print("=== dispatch results ===")
    for skill_id, payload in [
        ("greeter", {"name": "Jaggaer"}),
        ("spend.summary", {}),
        ("does.not.exist", {}),  # unknown skill -> ok=False, no hop
    ]:
        result = mesh.dispatch(root, skill_id, payload)
        status = "ok" if result.ok else f"ERR {result.error}"
        print(
            f"  {skill_id:<16} agent={result.agent:<16} "
            f"${result.cost_usd:.4f}  {status}  {result.output}"
        )

    print("\n=== recorded hops (the network view feed) ===")
    for hop in hops:
        print(
            f"  {hop.from_agent} -> {hop.to_agent}  "
            f"[{hop.skill_id}]  ok={hop.ok}  ${hop.cost_usd:.4f}"
        )

    print("\n=== A2A agent-card JSON (.well-known/agent.json) for spend-analyst ===")
    print(json.dumps(mesh.to_a2a_json(analyst), indent=2))

    print("\n=== topology ===")
    print(json.dumps(mesh.topology(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
