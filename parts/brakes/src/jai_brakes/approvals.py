"""Approvals — durable HITL gates backed by the `brakes` Postgres schema.

An agent run that reaches a HITL gate writes one row here and pauses. A human
decides (approve/reject); the run resumes by reading the decision keyed on
(thread_id, gate). The row IS the contract — no queue, no callback, just
Postgres state that survives restarts. Decisions are write-once: a second
decide() on the same row refuses with ValueError.
"""

from __future__ import annotations

import os
from typing import Any

import psycopg
from jai_manifest import RunContext
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

_DEFAULT_PG_URL = "postgresql://jai:jai@localhost:5433/jai"

_SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS brakes;
CREATE TABLE IF NOT EXISTS brakes.approvals (
    id           bigserial PRIMARY KEY,
    ts           timestamptz NOT NULL DEFAULT now(),
    tenant_id    text NOT NULL,
    gate         text NOT NULL,
    agent        text,
    run_id       text NOT NULL,
    thread_id    text NOT NULL,
    requested_by text NOT NULL,
    payload      jsonb NOT NULL DEFAULT '{}',
    status       text NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending', 'approved', 'rejected')),
    decided_by   text,
    decided_at   timestamptz,
    note         text
);
CREATE INDEX IF NOT EXISTS approvals_status_idx ON brakes.approvals (status);
CREATE INDEX IF NOT EXISTS approvals_tenant_ts_idx ON brakes.approvals (tenant_id, ts);
CREATE INDEX IF NOT EXISTS approvals_thread_gate_idx ON brakes.approvals (thread_id, gate);
"""


class Approvals:
    """The brake caliper: request → pending → human decision → resume."""

    def __init__(self, pg_url: str | None = None) -> None:
        self._pg_url = pg_url or os.environ.get("POSTGRES_URL", _DEFAULT_PG_URL)

    def _connect(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._pg_url, row_factory=dict_row)

    def ensure_schema(self) -> None:
        """Idempotently create the brakes schema, approvals table, and indexes."""
        with self._connect() as conn:
            conn.execute(_SCHEMA_SQL)

    def request(self, ctx: RunContext, *, gate: str, thread_id: str, payload: dict) -> int:
        """File one pending approval attributed from ctx; returns the approval id."""
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO brakes.approvals
                    (tenant_id, gate, agent, run_id, thread_id, requested_by, payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    ctx.tenant_id,
                    gate,
                    ctx.agent,
                    ctx.run_id,
                    thread_id,
                    ctx.actor.id,
                    Jsonb(payload),
                ),
            ).fetchone()
            if row is None:  # pragma: no cover - RETURNING always yields a row
                raise RuntimeError("insert returned no row")
            return int(row["id"])

    def pending(self, tenant_id: str | None = None) -> list[dict]:
        """All pending approvals, newest first, optionally for one tenant."""
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT * FROM brakes.approvals
                 WHERE status = 'pending'
                   AND (%(tenant_id)s::text IS NULL OR tenant_id = %(tenant_id)s)
                 ORDER BY ts DESC, id DESC
                """,
                {"tenant_id": tenant_id},
            ).fetchall()

    def get(self, approval_id: int) -> dict | None:
        """One approval row by id, or None."""
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM brakes.approvals WHERE id = %s", (approval_id,)
            ).fetchone()

    def decide(self, approval_id: int, *, approver: str, approve: bool, note: str = "") -> dict:
        """Record the human decision; returns the decided row.

        Write-once: raises ValueError if the approval does not exist or was
        already decided (the status='pending' predicate makes this race-safe).
        """
        status = "approved" if approve else "rejected"
        with self._connect() as conn:
            row = conn.execute(
                """
                UPDATE brakes.approvals
                   SET status = %s, decided_by = %s, decided_at = now(), note = %s
                 WHERE id = %s AND status = 'pending'
                RETURNING *
                """,
                (status, approver, note, approval_id),
            ).fetchone()
            if row is not None:
                return row
            existing = conn.execute(
                "SELECT status FROM brakes.approvals WHERE id = %s", (approval_id,)
            ).fetchone()
        if existing is None:
            raise ValueError(f"approval {approval_id} does not exist")
        raise ValueError(f"approval {approval_id} already decided: {existing['status']}")

    def decision_for(self, thread_id: str, gate: str) -> dict | None:
        """Latest decided row for (thread_id, gate), or None while pending/unknown."""
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT * FROM brakes.approvals
                 WHERE thread_id = %s AND gate = %s AND status <> 'pending'
                 ORDER BY decided_at DESC, id DESC
                 LIMIT 1
                """,
                (thread_id, gate),
            ).fetchone()
