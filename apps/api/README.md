# steel-api — the STEEL control plane

**SYSTEM: COCKPIT** (backend) · one-line purpose: *the read-only FastAPI surface the
console reads — costs, runs, audit verification, health.*

## Standalone use case

Point `steel-api` at **any** Postgres that holds the two published table contracts —
`meter.task_ledger` (per-action cost ledger) and `blackbox.audit_events` (hash-chained
audit log) — and you get an instant read-only operations API: cost rollups by tenant /
agent / run / model group, a run browser, and independent tamper verification of the
audit chain. No other STEEL part needs to be installed or running; the chain check
recomputes SHA-256 hashes itself.

## The boundary decision (P0)

The control plane is assembler-tier: it reads other parts only through their published
interfaces. At P0, the parts' **tables are their public read contract** for the control
plane — `steel_api/queries.py` issues plain `SELECT`s against `blackbox.audit_events` and
`meter.task_ledger` and nothing else. Every query is read-only; this app owns **no**
schema and never writes a row. Revisit when the parts grow client libraries.

## Endpoints

| Route | Returns |
|---|---|
| `GET /health` | `{"status": "ok", "postgres": true\|false}` — always 200 |
| `GET /costs?by=tenant_id\|agent\|run_id\|model_group` | cost rollup rows `{key, calls, input_tokens, output_tokens, cost_usd}` |
| `GET /runs?limit=20` | distinct runs `{run_id, first_ts, last_ts, tenant_id, agent, events, outcome}` (outcome from `run.end` if present) |
| `GET /runs/{run_id}/events` | the run's audit events in chain order — hash internals omitted |
| `GET /audit/verify` | independent chain recomputation: `{ok, checked, broken_at_seq}` |

When Postgres is down, data routes answer `503` with
`{"error": "postgres_unavailable", "detail": "..."}` and `/health` answers `200` with
`postgres: false`. CORS is open for the console at `localhost:3000`.

## Usage

```bash
uv run steel-api                      # serve on PORT (default 8400), HOST (default 127.0.0.1)
curl http://localhost:8400/health
curl "http://localhost:8400/costs?by=model_group"
curl http://localhost:8400/audit/verify
```

Or embed the app factory:

```python
from steel_api import create_app

app = create_app()   # hand to any ASGI server
```

## Demo

```bash
docker compose up -d postgres        # optional — demo degrades gracefully without it
uv run python apps/api/demo/demo.py
```

## Tests

```bash
uv run pytest apps/api -q            # data-route tests skip when Postgres is unavailable
```

## Environment

| Variable | Default | Meaning |
|---|---|---|
| `POSTGRES_URL` | `postgresql://steel:steel@localhost:5433/steel` | read-only source database |
| `PORT` | `8400` | serve port for `steel-api` |
| `HOST` | `127.0.0.1` | bind address for `steel-api` |
