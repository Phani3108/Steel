"""Meter — the per-action cost ledger backed by the `meter` Postgres schema."""

from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

import psycopg
from steel_manifest import RunContext
from psycopg import sql
from psycopg.types.json import Jsonb
from pydantic import BaseModel

Dimension = Literal["tenant_id", "agent", "run_id", "model_group"]

# Mirror of Dimension — the aggregation column is interpolated into SQL, so it
# must be validated against this closed set, never trusted as a free string.
_DIMENSIONS: frozenset[str] = frozenset({"tenant_id", "agent", "run_id", "model_group"})

_DEFAULT_PG_URL = "postgresql://steel:steel@localhost:5433/steel"

_SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS meter;
CREATE TABLE IF NOT EXISTS meter.task_ledger (
    id            bigserial PRIMARY KEY,
    ts            timestamptz NOT NULL DEFAULT now(),
    tenant_id     text NOT NULL,
    agent         text,
    run_id        text NOT NULL,
    trace_id      text NOT NULL,
    action        text NOT NULL,
    model         text,
    model_group   text,
    input_tokens  int NOT NULL DEFAULT 0,
    output_tokens int NOT NULL DEFAULT 0,
    cost_usd      numeric(12,6) NOT NULL DEFAULT 0,
    detail        jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS task_ledger_run_id_idx ON meter.task_ledger (run_id);
CREATE INDEX IF NOT EXISTS task_ledger_tenant_ts_idx ON meter.task_ledger (tenant_id, ts);
CREATE INDEX IF NOT EXISTS task_ledger_agent_idx ON meter.task_ledger (agent);
"""

_INSERT_SQL = """
INSERT INTO meter.task_ledger
    (tenant_id, agent, run_id, trace_id, action, model, model_group,
     input_tokens, output_tokens, cost_usd, detail)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING id
"""


class CostRow(BaseModel):
    """One aggregated line of a cost report."""

    key: str
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal


class Meter:
    """The odometer: records what every action cost, answers who spent what."""

    def __init__(self, pg_url: str | None = None) -> None:
        self._pg_url = pg_url or os.environ.get("POSTGRES_URL", _DEFAULT_PG_URL)

    def _connect(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._pg_url)

    def ensure_schema(self) -> None:
        """Idempotently create the meter schema, ledger table, and indexes."""
        with self._connect() as conn:
            conn.execute(_SCHEMA_SQL)

    def record(
        self,
        ctx: RunContext,
        *,
        action: str,
        model: str | None,
        model_group: str | None,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        detail: dict[str, Any] | None = None,
    ) -> int:
        """Write one ledger row attributed via ctx; returns the row id."""
        with self._connect() as conn:
            row = conn.execute(
                _INSERT_SQL,
                (
                    ctx.tenant_id,
                    ctx.agent,
                    ctx.run_id,
                    ctx.trace_id,
                    action,
                    model,
                    model_group,
                    input_tokens,
                    output_tokens,
                    # str() preserves the float's shortest decimal repr exactly,
                    # avoiding binary-float drift in the numeric(12,6) column.
                    Decimal(str(cost_usd)),
                    Jsonb(detail or {}),
                ),
            ).fetchone()
            if row is None:  # pragma: no cover - RETURNING always yields a row
                raise RuntimeError("insert returned no row")
            return int(row[0])

    def run_total(self, run_id: str) -> Decimal:
        """Total cost in USD accrued by one run."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM meter.task_ledger WHERE run_id = %s",
                (run_id,),
            ).fetchone()
            if row is None:  # pragma: no cover - aggregate always yields a row
                raise RuntimeError("aggregate returned no row")
            return Decimal(row[0])

    def costs_by(self, dimension: Dimension, since: datetime | None = None) -> list[CostRow]:
        """Cost report grouped by one dimension, optionally limited to ts >= since."""
        if dimension not in _DIMENSIONS:
            raise ValueError(f"dimension must be one of {sorted(_DIMENSIONS)}, got {dimension!r}")
        query = sql.SQL(
            """
            SELECT
                COALESCE({dim}, '-') AS key,
                COUNT(*)::int AS calls,
                COALESCE(SUM(input_tokens), 0)::bigint AS input_tokens,
                COALESCE(SUM(output_tokens), 0)::bigint AS output_tokens,
                COALESCE(SUM(cost_usd), 0) AS cost_usd
            FROM meter.task_ledger
            WHERE (%(since)s::timestamptz IS NULL OR ts >= %(since)s)
            GROUP BY 1
            ORDER BY cost_usd DESC, key
            """
        ).format(dim=sql.Identifier(dimension))
        with self._connect() as conn:
            rows = conn.execute(query, {"since": since}).fetchall()
        return [
            CostRow(
                key=key,
                calls=calls,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=Decimal(cost_usd),
            )
            for key, calls, input_tokens, output_tokens, cost_usd in rows
        ]
