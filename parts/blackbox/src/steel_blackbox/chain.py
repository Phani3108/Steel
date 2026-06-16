"""The hash chain: append AuditEvents, read the tail, verify end-to-end integrity.

Chain rule: hash = sha256_hex(prev_hash + canonical_json(event)); the genesis prev_hash
is sixty-four zeros. Appends are serialized with a transaction-scoped advisory lock so
the chain is linear even under concurrent writers. Verification recomputes every hash
AND cross-checks every stored column against the canonical payload, so editing any
column of any row — including `detail` — breaks the chain.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg
from steel_manifest import AuditEvent, canonical_json, sha256_hex
from psycopg.rows import dict_row
from psycopg.types.json import Json

GENESIS_HASH = "0" * 64

_DEFAULT_PG_URL = "postgresql://steel:steel@localhost:5433/steel"

_SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS blackbox;
CREATE TABLE IF NOT EXISTS blackbox.audit_events (
    seq            bigserial PRIMARY KEY,
    event_id       text UNIQUE NOT NULL,
    ts             timestamptz NOT NULL,
    tenant_id      text NOT NULL,
    actor_id       text NOT NULL,
    actor_role     text NOT NULL,
    agent          text,
    run_id         text NOT NULL,
    trace_id       text NOT NULL,
    action         text NOT NULL,
    outcome        text NOT NULL,
    policy_version text,
    input_sha256   text,
    detail         jsonb NOT NULL DEFAULT '{}',
    canonical      text NOT NULL,
    prev_hash      text NOT NULL,
    hash           text NOT NULL
);
CREATE INDEX IF NOT EXISTS audit_events_run_id_idx
    ON blackbox.audit_events (run_id);
CREATE INDEX IF NOT EXISTS audit_events_tenant_ts_idx
    ON blackbox.audit_events (tenant_id, ts);
"""

_INSERT_SQL = """
INSERT INTO blackbox.audit_events (
    event_id, ts, tenant_id, actor_id, actor_role, agent, run_id, trace_id,
    action, outcome, policy_version, input_sha256, detail, canonical, prev_hash, hash
) VALUES (
    %(event_id)s, %(ts)s, %(tenant_id)s, %(actor_id)s, %(actor_role)s, %(agent)s,
    %(run_id)s, %(trace_id)s, %(action)s, %(outcome)s, %(policy_version)s,
    %(input_sha256)s, %(detail)s, %(canonical)s, %(prev_hash)s, %(hash)s
)
"""

# Columns whose canonical-payload value must equal the stored column, verbatim.
_PLAIN_COLUMNS = (
    "event_id",
    "tenant_id",
    "actor_id",
    "actor_role",
    "agent",
    "run_id",
    "trace_id",
    "action",
    "outcome",
    "policy_version",
    "input_sha256",
)


@dataclass(frozen=True)
class VerifyResult:
    """Outcome of a chain walk. `checked` counts the rows matching the report filter;
    `broken_at_seq` is the first row (anywhere in the global chain) that fails."""

    ok: bool
    checked: int
    broken_at_seq: int | None


class BlackBox:
    """Append-only, hash-chained audit log over a single Postgres schema (`blackbox`)."""

    def __init__(self, pg_url: str | None = None) -> None:
        self.pg_url = pg_url or os.environ.get("POSTGRES_URL", _DEFAULT_PG_URL)

    def _connect(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self.pg_url, row_factory=dict_row)

    def ensure_schema(self) -> None:
        """Idempotently create the blackbox schema, table, and indexes."""
        with self._connect() as conn:
            conn.execute(_SCHEMA_SQL)

    def append(self, event: AuditEvent) -> str:
        """Append one event and return its chain hash.

        The advisory xact lock serializes writers; the previous row's hash is read
        inside the same transaction, so the chain can never fork.
        """
        canonical = canonical_json(event)
        with self._connect() as conn, conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(hashtext('steel_blackbox_chain'))")
            row = conn.execute(
                "SELECT hash FROM blackbox.audit_events ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            prev_hash = row["hash"] if row else GENESIS_HASH
            new_hash = sha256_hex(prev_hash + canonical)
            conn.execute(
                _INSERT_SQL,
                {
                    "event_id": event.event_id,
                    "ts": event.ts,
                    "tenant_id": event.tenant_id,
                    "actor_id": event.actor_id,
                    "actor_role": event.actor_role,
                    "agent": event.agent,
                    "run_id": event.run_id,
                    "trace_id": event.trace_id,
                    "action": event.action,
                    "outcome": event.outcome,
                    "policy_version": event.policy_version,
                    "input_sha256": event.input_sha256,
                    "detail": Json(event.detail),
                    "canonical": canonical,
                    "prev_hash": prev_hash,
                    "hash": new_hash,
                },
            )
        return new_hash

    def tail(self, n: int = 10, run_id: str | None = None) -> list[dict[str, Any]]:
        """The last `n` events in chain order, optionally filtered to one run."""
        where = "WHERE run_id = %(run_id)s" if run_id else ""
        sql = (
            "SELECT * FROM ("
            f"  SELECT * FROM blackbox.audit_events {where} ORDER BY seq DESC LIMIT %(n)s"
            ") last_n ORDER BY seq ASC"
        )
        with self._connect() as conn:
            return conn.execute(sql, {"n": n, "run_id": run_id}).fetchall()

    def verify(self, run_id: str | None = None) -> VerifyResult:
        """Walk the FULL chain in seq order, recomputing every hash and cross-checking
        every stored column against its canonical payload.

        The chain is global: a break anywhere yields ok=False. `run_id` only filters
        which rows are counted in `checked`, never which rows are verified.
        """
        checked = 0
        expected_prev = GENESIS_HASH
        with self._connect() as conn, conn.cursor(name="blackbox_verify") as cur:
            cur.row_factory = dict_row
            cur.execute("SELECT * FROM blackbox.audit_events ORDER BY seq ASC")
            for row in cur:
                if run_id is None or row["run_id"] == run_id:
                    checked += 1
                if not self._row_intact(row, expected_prev):
                    return VerifyResult(ok=False, checked=checked, broken_at_seq=row["seq"])
                expected_prev = row["hash"]
        return VerifyResult(ok=True, checked=checked, broken_at_seq=None)

    @staticmethod
    def _row_intact(row: dict[str, Any], expected_prev: str) -> bool:
        if row["prev_hash"] != expected_prev:
            return False
        if sha256_hex(row["prev_hash"] + row["canonical"]) != row["hash"]:
            return False
        # The hash proves `canonical` is untampered; now prove the queryable columns
        # still say what the canonical payload says.
        try:
            payload: dict[str, Any] = json.loads(row["canonical"])
        except ValueError:
            return False
        if any(payload.get(col) != row[col] for col in _PLAIN_COLUMNS):
            return False
        if payload.get("detail") != row["detail"]:
            return False
        try:
            canonical_ts = datetime.fromisoformat(payload["ts"])
        except (KeyError, TypeError, ValueError):
            return False
        return canonical_ts == row["ts"]
