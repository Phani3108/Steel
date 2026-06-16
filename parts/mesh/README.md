# steel-mesh — the CAN bus

**System:** NETWORK · **Standalone use case:** an in-process A2A-shaped bus that lets agents
call each other by skill id while the run context (tenant, actor, budget, trace) rides along
on every hop — so one orchestration shares one trace across all the agents it touches. No
database, no network, no framework: pure transport. The only input is a `RunContext`-shaped
identity envelope (`steel_manifest`), and the agent cards are emitted as real A2A
`.well-known/agent.json` JSON, so a card the mesh dispatches in-process today can be served
cross-host tomorrow with no change to callers.

Drop it into any agent stack that needs agent-to-agent calls with propagated identity and a
recorded call graph — point handlers at your own functions and you have a fan-out coordinator
with a built-in network view.

| API | What it does |
|---|---|
| `Mesh(on_hop=None)` | a bus; `on_hop(Hop)` is called once per dispatch for observability |
| `.register(card, handlers)` | registers an `AgentCard` + its `{skill_id: handler}` map; raises if any advertised skill lacks a handler |
| `.cards()` | all registered cards, in registration order |
| `.card_for_skill(skill_id)` | the `AgentCard` serving a skill, or `None` |
| `.dispatch(ctx, skill_id, input)` | routes to the handler with a child `RunContext` (same tenant/actor/trace/budget, agent name swapped to the callee); returns a `TaskResult`; always emits a `Hop` (unknown skill → `ok=False`, no hop) |
| `.to_a2a_json(card)` | the A2A agent-card JSON (`.well-known/agent.json` shape) |
| `.topology()` | `{"nodes": [...], "skills": {skill_id: agent}}` — what the console network view renders |

Contracts (A2A-conformant subset): `Skill(id, name, description)`,
`AgentCard(name, description, url, version, skills, capabilities)`,
`TaskResult(skill_id, agent, ok, output, error, cost_usd)`,
`Hop(from_agent, to_agent, skill_id, ok, cost_usd)`.

**Context propagation rule:** the child `RunContext` keeps `tenant_id`, `trace_id`, `run_id`,
`actor`, and the `budget` pool from the parent and swaps only the agent name. That is what makes
one orchestration a single trace across every hop. A handler reads `_cost_usd` out of its own
return dict; the mesh surfaces it onto `TaskResult.cost_usd` and the emitted `Hop`.

`a2a-sdk` is the drop-in for real cross-host A2A serving/calling; `httpx` is already a dependency
for the future HTTP transport (the `HttpTransport` stub marks the seam).

## Usage

```python
from steel_manifest import Actor, RunContext
from steel_mesh import AgentCard, Hop, Mesh, Skill

hops: list[Hop] = []
mesh = Mesh(on_hop=hops.append)

analyst = AgentCard(
    name="spend-analyst",
    description="summarizes spend",
    skills=[Skill(id="spend.summary", name="Spend summary")],
)

def spend_summary(ctx: RunContext, input: dict) -> dict:
    # ctx is a child: same tenant/actor/trace/budget, agent swapped to "spend-analyst".
    return {"summary": f"{ctx.tenant_id}: $1.2M this quarter", "_cost_usd": 0.002}

mesh.register(analyst, {"spend.summary": spend_summary})

root = RunContext(
    tenant_id="acme",
    actor=Actor(id="u-demo", role="category_manager"),
    agent="agent-orchestrator",
    budget_usd_remaining=5.0,
)

result = mesh.dispatch(root, "spend.summary", {})   # TaskResult(ok=True, cost_usd=0.002, ...)
hops                                                 # [Hop(agent-orchestrator -> spend-analyst, ...)]
mesh.to_a2a_json(analyst)                            # .well-known/agent.json shape
mesh.topology()                                      # {"nodes": [...], "skills": {...}}
```

## Demo

```bash
export PATH="$HOME/.local/bin:$PATH"
cd /Users/susmitha/Downloads/STEEL
uv run python parts/mesh/demo/demo.py
```

Registers two toy agents (a `greeter` and a `spend.summary` analyst), dispatches both from one
root context plus one unknown skill, then prints the `TaskResult`s, the recorded `Hop`s, one
A2A agent-card JSON, and the topology.

## Tests

```bash
uv run pytest parts/mesh -q
```

No Postgres required — the mesh is pure transport. Covers the dispatch happy path (output +
cost + hop), child-context propagation, handler exceptions, unknown skills, register
validation, the A2A JSON shape, and topology.
