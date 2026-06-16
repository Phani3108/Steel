# steel-registry — the fleet roster

**System:** NETWORK · **Standalone use case:** a drop-in catalog for any fleet of agents —
point it at a Postgres and you have one queryable table holding every agent's card (system,
description, autonomy level, pipeline, skills), its live status (`active | paused | killed |
planned`), its bounded mandate, and its latest scorecard headline — plus an append-only log
of every status change (who, why, when). No STEEL runtime required: it ingests framework-free
`AgentManifest`s and plain scorecard JSON, so any console or orchestrator can read the whole
fleet at a glance and any operator can pause or revive an agent with a paper trail.

Owned schema namespace `registry` (ADR-003), no other part's schema touched. Two tables:
`registry.agents` (the live roster, one row per agent, upserted by name) and
`registry.status_log` (the history). Agents are upserted from their manifests, never
hand-typed; status is owned by `set_status`, so re-registering a promoted agent never
silently revives a paused or killed one.

| API | What it does |
|---|---|
| `Registry(pg_url=None)` | connects via `pg_url` or `POSTGRES_URL` |
| `ensure_schema()` | idempotently creates `registry.agents` + `registry.status_log` |
| `register_manifest(manifest, *, system, status="active")` | upserts one agent by name from its manifest; returns `AgentRecord` |
| `list()` | the whole roster, ordered by system then name |
| `get(name)` | one `AgentRecord`, or `None` |
| `set_status(name, status, *, by, reason="")` | flips live status **and** appends a `status_log` row; raises if unknown |
| `attach_scorecard(name, scorecard)` | stores the scorecard headline (no-op if the agent is unknown) |
| `sync_agents(agents_dir, systems)` | registers every `*/manifest.yaml` under `agents_dir`, mapping name → system (default `NETWORK`); returns count |
| `load_scorecards(results_dir)` | ingests `*.json` (single card or a list), attaching each to its agent by the card's `agent` field; returns count |

`register_manifest` derives `autonomy_level = int(manifest.autonomy_level)`, `pipeline`,
`skills`, and `mandate_usd = manifest.mandate.max_spend_usd`. `load_scorecards` keeps only
the headline keys `{suite, pass_rate, n_cases, n_passed, ts}` — the full failure list stays
in `evals/results` and the dyno.

## Usage

```python
from pathlib import Path
from steel_registry import Registry

reg = Registry()          # uses POSTGRES_URL (default postgresql://steel:steel@localhost:5433/steel)
reg.ensure_schema()

# Load the whole on-disk fleet + its scorecards in two calls.
reg.sync_agents(Path("parts/agents"), {"agent-sourcing": "DRIVETRAIN"})
reg.load_scorecards(Path("evals/results"))

reg.list()                                  # ordered by system, then name
reg.get("agent-supplier-intel").scorecard   # {'suite': 'suite1-goldens', 'pass_rate': 1.0, ...}

# Pause an agent with a logged reason, then revive it.
reg.set_status("agent-sourcing", "paused", by="u-cpo", reason="quarterly freeze")
reg.set_status("agent-sourcing", "active", by="u-cpo", reason="freeze lifted")
```

## CLI

The `steel-registry` console script wraps the two everyday operations against the built-in
SYSTEMS map (echo→POWERTRAIN, supplier-intel→CHASSIS, sourcing→DRIVETRAIN, the rest→NETWORK):

```bash
steel-registry sync     # load parts/agents/*/manifest.yaml + evals/results/*.json, then print the roster
steel-registry list     # pretty table of the current roster
```

## Demo

Syncs the real fleet, prints the roster, pauses `agent-sourcing` (showing the status flip and
the `status_log` entry that records who/why), then revives it.

```bash
docker compose up -d postgres     # from the repo root, if not already running
python parts/registry/demo/demo.py
```

## Tests

```bash
uv run pytest parts/registry -q   # Postgres-or-skip; TRUNCATEs the registry tables at setup
```
