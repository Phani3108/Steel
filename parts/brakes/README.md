# jai-brakes — the brakes

**System:** SAFETY · **Standalone use case:** drop-in human-in-the-loop approval gates and an
agent kill switch for any agent stack — point it at a Postgres and you have durable
request → pending → human decision → resume state plus a per-agent emergency stop, with no
queue, no callback infrastructure, and nothing lost on restart. No JAI required: the only
input is a `RunContext`-shaped identity envelope.

Two tables, owned schema namespace `brakes` (ADR-003), no other part's schema touched.
A paused run holds only `(thread_id, gate)`; polling `decision_for()` is the resume signal.
Runtimes check `is_killed(agent)` before acting — the flag is shared by every runtime on
the same Postgres.

| API | What it does |
|---|---|
| `Brakes(pg_url=None)` | connects via `pg_url` or `POSTGRES_URL` |
| `ensure_schema()` | idempotently creates `brakes.approvals` + `brakes.kill_switch` |
| `request(ctx, *, gate, thread_id, payload)` | files one pending approval attributed from the `RunContext`; returns approval id |
| `pending(tenant_id=None)` | pending approvals as `list[dict]`, newest first |
| `get(approval_id)` | one approval row, or `None` |
| `decide(approval_id, *, approver, approve, note="")` | records the decision; write-once — raises `ValueError` if already decided |
| `decision_for(thread_id, gate)` | latest decided row for the gate, or `None` while pending/unknown |
| `kill(agent, *, by, reason="")` / `revive(agent, *, by)` | upsert the per-agent kill flag |
| `is_killed(agent)` | `True` iff killed; missing row means `False` |

`Approvals` and `KillSwitch` are also importable separately if you only need one half.

## Usage

```python
from jai_brakes import Brakes
from jai_manifest import Actor, RunContext

brakes = Brakes()          # uses POSTGRES_URL (default postgresql://jai:jai@localhost:5433/jai)
brakes.ensure_schema()

ctx = RunContext(
    tenant_id="acme",
    actor=Actor(id="u-req", role="requester"),
    agent="agent-sourcing",
)

# Agent side: pause at the gate (a requester may only self-approve up to $5,000).
approval_id = brakes.request(
    ctx, gate="po-approval", thread_id="thread-1",
    payload={"po_total_usd": 12_400, "supplier": "Veridian Metals"},
)

# Human side: review the inbox and decide.
brakes.pending("acme")                                   # newest first
brakes.decide(approval_id, approver="u-cm", approve=True, note="within budget")

# Agent side: resume on the decision.
decision = brakes.decision_for("thread-1", "po-approval")  # {'status': 'approved', ...}

# Emergency stop.
brakes.kill("agent-sourcing", by="u-cpo", reason="anomalous spend")
brakes.is_killed("agent-sourcing")                       # True
brakes.revive("agent-sourcing", by="u-cpo")
```

## Demo

```sh
docker compose up -d postgres        # from the repo root
python parts/brakes/demo/demo.py
```

Walks the full loop: request a $12,400 PO approval, list the pending inbox, approve it,
show the write-once refusal on a second decide, resume via `decision_for`, then kill and
revive `agent-sourcing`.

## Tests

```sh
uv run pytest parts/brakes -q        # skip cleanly if Postgres is not reachable
```
