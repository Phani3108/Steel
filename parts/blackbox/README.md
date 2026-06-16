# steel-blackbox — the flight recorder

**System:** SAFETY · **Standalone use case:** a tamper-evident audit log for ANY agent
system — point it at a Postgres, append `AuditEvent`s, and `verify` proves in one walk
that nobody edited history. EU AI Act Article 12-grade logging by construction, not by
policy document.

Every event is hash-chained: `hash = sha256(prev_hash + canonical_json(event))`, genesis
`prev_hash = "0" * 64`. Appends are serialized with a Postgres advisory lock so the chain
is linear under concurrent writers. `verify()` recomputes every hash **and** cross-checks
every stored column against its canonical payload — so editing any column of any row
(even `detail` jsonb) is detected, with the exact `seq` of the break.

Owns exactly one schema namespace: `blackbox` (ADR-003). Imports only `steel_manifest`.

## Standalone usage

```python
from steel_manifest import AuditEvent
from steel_blackbox import BlackBox

box = BlackBox()                       # or BlackBox("postgresql://user:pw@host/db")
box.ensure_schema()                    # idempotent — schema, table, indexes

box.append(AuditEvent(
    tenant_id="acme", actor_id="u42", actor_role="category_manager",
    run_id="run_1", trace_id="tr_1", action="tool.call", outcome="ok",
    detail={"tool": "supplier-master.search"},
))

result = box.verify()                  # walks the FULL chain
assert result.ok, f"history was edited at seq={result.broken_at_seq}"

for row in box.tail(n=10, run_id="run_1"):
    print(row["seq"], row["action"], row["outcome"])
```

```sh
steel-blackbox tail -n 10                # last 10 events, chain order
steel-blackbox verify                    # exit 1 if the chain is broken
steel-blackbox verify --run-id run_1     # same walk; reports that run's row count
```

`POSTGRES_URL` is the connection fallback (default `postgresql://steel:steel@localhost:5433/steel`).

## Demo

```sh
docker compose up -d postgres
python parts/blackbox/demo/demo.py
```

Appends 3 events, verifies OK, then tampers with one row via raw SQL `UPDATE` — and shows
`verify()` reporting `ok=False` with the broken `seq` — then restores the row.

## Tests

```sh
uv run pytest parts/blackbox -q        # skip cleanly when Postgres is down
```
