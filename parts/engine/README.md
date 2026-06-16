# steel-engine

**SYSTEM: POWERTRAIN** — the engine. Compiles Agent Manifests into a runnable agent
(LangGraph 1.x today; the compile seam is what makes runtimes swappable — ADR-001, ADR-004).

## What it does

`compile_manifest()` turns a declarative `AgentManifest` (YAML, framework-free) into a
`CompiledAgent` backed by a LangGraph `StateGraph`:

```
guard_in  ──▶  model  ──▶  guard_out
(injection     (prompt file +   (output
 deny-list)     gateway call)    validation)
```

Every run is wrapped in an audit envelope (`run.start` / `model.call` / `run.end` appended
to the blackbox hash chain), every model call is metered to the cost ledger, and — when a
Postgres is reachable — state is checkpointed via `langgraph-checkpoint-postgres` so a run
with a `thread_id` survives a crash (ADR-004: durability without Temporal).

The engine never hardcodes its collaborators: gateway, blackbox, and meter are injected
ports (`Protocol`s in `compile.py`). Swap the orchestrator by writing a second compile
function against the same manifest — nothing outside the engine notices.

## Standalone use case

You have a YAML spec of an agent (system prompt file, model group, token/budget caps,
guardrail toggles) and want a runnable, auditable agent loop **without** adopting the rest
of STEEL. Bring any OpenAI-compatible gateway client with a
`complete(ctx, *, group, messages, max_tokens)` method, any sink with `append(event)`, and
any ledger with `record(...)` — in-memory implementations are ~40 lines (see
`tests/engine_fakes.py`). No Postgres needed: without one, the agent simply runs
un-checkpointed.

## Usage

```python
from pathlib import Path

from steel_blackbox import BlackBox
from steel_engine import compile_manifest
from steel_gateway import GatewayClient
from steel_manifest import Actor, RunContext, load_manifest
from steel_meter import Meter

echo_dir = Path("parts/agents/echo")
manifest = load_manifest(echo_dir / "manifest.yaml")

agent = compile_manifest(
    manifest,
    gateway=GatewayClient(),       # STEEL_MOCK=1 (default) -> keyless mock completions
    blackbox=BlackBox(),           # hash-chained audit trail
    meter=Meter(),                 # cost ledger
    prompt_base=echo_dir,          # manifest.prompt.path is relative to this
)

ctx = RunContext(tenant_id="borealis-na", actor=Actor(id="me", role="system"))
result = agent.run(ctx, "Hello, STEEL.")          # thread_id=... for resumable runs
print(result.text, result.cost_usd, result.run_id)
```

`run()` raises `GuardrailViolation` on a screened input or empty output, and propagates
`BudgetExceededError` from the gateway's pre-dispatch budget gate. All three outcomes are
audited before the exception leaves the engine.

## Demo 0

The platform's smoke test — manifest → compile → run → audit + ledger, keyless:

```bash
docker compose up -d            # postgres + litellm; no provider API keys needed
python parts/engine/demo/demo_0.py   # or: make smoke
```

Prints the agent output, the run's ledger total, the blackbox `verify()` verdict, and the
audit tail for the run.

## Tests

```bash
uv run pytest parts/engine -q
```

No services required: gateway/blackbox/meter are in-memory fakes. The single Postgres
checkpointer test skips itself when no Postgres answers at `POSTGRES_URL`
(default `postgresql://steel:steel@localhost:5433/steel`).

## Env

| Variable | Default | Used for |
|---|---|---|
| `POSTGRES_URL` | `postgresql://steel:steel@localhost:5433/steel` | LangGraph checkpointer (optional) |
| `LITELLM_BASE_URL` | `http://localhost:4000` | via steel-gateway |
| `LITELLM_MASTER_KEY` | `sk-steel-master-dev` | via steel-gateway |
| `STEEL_MOCK` | `1` | keyless mock completions via steel-gateway |

Note on schemas: the LangGraph checkpointer writes its tables to Postgres's default
schema (accepted for P0; the engine's own `engine` schema namespace stays reserved).
