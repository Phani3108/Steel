"""Read-only queries over other parts' published table contracts.

The control plane is assembler-tier: at P0 the ``blackbox.audit_events`` and
``meter.task_ledger`` tables ARE those parts' public read contract for the
console (revisit when the parts grow client libraries). Every statement in
this module is a plain SELECT — the control plane never writes.
"""

from __future__ import annotations

from typing import Any

from jai_manifest import sha256_hex
from psycopg import sql

from jai_api.db import connect

GENESIS_HASH = "0" * 64

# The aggregation column is interpolated into SQL as an identifier, so it must
# be validated against this closed set, never trusted as a free string.
COST_DIMENSIONS: frozenset[str] = frozenset({"tenant_id", "agent", "run_id", "model_group"})

_COSTS_SQL = sql.SQL(
    """
    SELECT
        COALESCE({dim}, '-') AS key,
        COUNT(*)::int AS calls,
        COALESCE(SUM(input_tokens), 0)::bigint AS input_tokens,
        COALESCE(SUM(output_tokens), 0)::bigint AS output_tokens,
        COALESCE(SUM(cost_usd), 0)::float8 AS cost_usd
    FROM meter.task_ledger
    GROUP BY 1
    ORDER BY cost_usd DESC, key
    """
)

_RUNS_SQL = """
SELECT
    run_id,
    MIN(ts) AS first_ts,
    MAX(ts) AS last_ts,
    MAX(tenant_id) AS tenant_id,
    MAX(agent) AS agent,
    COUNT(*)::int AS events,
    MAX(outcome) FILTER (WHERE action = 'run.end') AS outcome
FROM blackbox.audit_events
GROUP BY run_id
ORDER BY MAX(ts) DESC
LIMIT %(limit)s
"""

# Hash-chain internals (canonical, prev_hash, hash) are deliberately omitted:
# they are blackbox's mechanism, not the console's data.
_RUN_EVENTS_SQL = """
SELECT
    seq, event_id, ts, tenant_id, actor_id, actor_role, agent, trace_id,
    action, outcome, policy_version, detail
FROM blackbox.audit_events
WHERE run_id = %(run_id)s
ORDER BY seq ASC
"""


def costs_by(dimension: str) -> list[dict[str, Any]]:
    """Cost rollup from meter.task_ledger grouped by one allowed dimension."""
    if dimension not in COST_DIMENSIONS:
        raise ValueError(f"dimension must be one of {sorted(COST_DIMENSIONS)}, got {dimension!r}")
    query = _COSTS_SQL.format(dim=sql.Identifier(dimension))
    with connect() as conn:
        return conn.execute(query).fetchall()


def list_runs(limit: int = 20) -> list[dict[str, Any]]:
    """Distinct runs from blackbox.audit_events, most recently active first."""
    with connect() as conn:
        return conn.execute(_RUNS_SQL, {"limit": limit}).fetchall()


def run_events(run_id: str) -> list[dict[str, Any]]:
    """One run's audit events in chain order, hash internals omitted."""
    with connect() as conn:
        return conn.execute(_RUN_EVENTS_SQL, {"run_id": run_id}).fetchall()


def verify_chain() -> dict[str, Any]:
    """Independently recompute the blackbox hash chain.

    Same chain rule as jai-blackbox: hash = sha256(prev_hash + canonical),
    genesis prev_hash is sixty-four zeros. Walks every row in seq order via a
    server-side cursor; `checked` is the number of rows that verified.
    """
    checked = 0
    expected_prev = GENESIS_HASH
    with connect() as conn, conn.cursor(name="jai_api_audit_verify") as cur:
        cur.execute(
            "SELECT seq, canonical, prev_hash, hash FROM blackbox.audit_events ORDER BY seq"
        )
        for row in cur:
            intact = (
                row["prev_hash"] == expected_prev
                and sha256_hex(row["prev_hash"] + row["canonical"]) == row["hash"]
            )
            if not intact:
                return {"ok": False, "checked": checked, "broken_at_seq": row["seq"]}
            expected_prev = row["hash"]
            checked += 1
    return {"ok": True, "checked": checked, "broken_at_seq": None}


def tenants() -> list[dict[str, Any]]:
    """Tenant list for the console's persona switcher (cortex's published read contract)."""
    with connect() as conn:
        rows = conn.execute("SELECT id, name FROM cortex.tenants ORDER BY id").fetchall()
    return list(rows)
