# steel-meter — the odometer

**System:** SAFETY · **Standalone use case:** a drop-in cost ledger for any LLM/agent stack —
point it at a Postgres, call `record()` after every action, and you have per-tenant /
per-agent / per-run / per-model-group cost accounting that any future pricing model
(chargeback, subscription tiers, per-task billing) can be built on. No STEEL required:
the only inputs are a `RunContext`-shaped identity envelope and token/cost numbers.

One ledger table, owned schema namespace `meter` (ADR-003), no other part's schema touched.

| API | What it does |
|---|---|
| `Meter(pg_url=None)` | connects via `pg_url` or `POSTGRES_URL` |
| `ensure_schema()` | idempotently creates `meter.task_ledger` + indexes |
| `record(ctx, *, action, model, model_group, input_tokens, output_tokens, cost_usd, detail=None)` | writes one row attributed from the `RunContext`; returns row id |
| `run_total(run_id)` | `Decimal` total cost of one run |
| `costs_by(dimension, since=None)` | report grouped by `tenant_id` / `agent` / `run_id` / `model_group` as `list[CostRow]` |

## Usage

```python
from steel_manifest import Actor, RunContext
from steel_meter import Meter

meter = Meter()                      # uses POSTGRES_URL (default postgresql://steel:steel@localhost:5433/steel)
meter.ensure_schema()

ctx = RunContext(
    tenant_id="acme",
    actor=Actor(id="u1", role="category_manager"),
    agent="agent-sourcing",
)
meter.record(
    ctx,
    action="model.call",
    model="gpt-5o",
    model_group="reasoning",
    input_tokens=1200,
    output_tokens=350,
    cost_usd=0.042,
)

meter.run_total(ctx.run_id)          # Decimal('0.042000')
meter.costs_by("tenant_id")          # [CostRow(key='acme', calls=1, ..., cost_usd=Decimal('0.042000'))]
```

## Demo

```sh
docker compose up -d postgres        # from the repo root
python parts/meter/demo/demo.py
```

Records six actions across two tenants and two agents, then prints run totals and a
cost report per dimension.

## Tests

```sh
uv run pytest parts/meter -q         # skip cleanly if Postgres is not reachable
```
