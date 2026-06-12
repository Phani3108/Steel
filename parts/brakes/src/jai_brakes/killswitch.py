"""Kill switch — the emergency brake, one durable flag per agent.

Any runtime checks is_killed(agent) before acting; a human (or the governor)
flips it with kill()/revive(). State lives in brakes.kill_switch so it holds
across process restarts and is shared by every runtime on the same Postgres.
"""

from __future__ import annotations

import os
from typing import Any

import psycopg

_DEFAULT_PG_URL = "postgresql://jai:jai@localhost:5433/jai"

# "by" is quoted: BY is a reserved word in PostgreSQL.
_SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS brakes;
CREATE TABLE IF NOT EXISTS brakes.kill_switch (
    agent  text PRIMARY KEY,
    killed boolean NOT NULL,
    "by"   text,
    reason text,
    ts     timestamptz NOT NULL DEFAULT now()
);
"""

_UPSERT_SQL = """
INSERT INTO brakes.kill_switch (agent, killed, "by", reason, ts)
VALUES (%s, %s, %s, %s, now())
ON CONFLICT (agent) DO UPDATE
   SET killed = EXCLUDED.killed,
       "by"   = EXCLUDED."by",
       reason = EXCLUDED.reason,
       ts     = now()
"""


class KillSwitch:
    """The emergency brake: kill/revive an agent, durable in Postgres."""

    def __init__(self, pg_url: str | None = None) -> None:
        self._pg_url = pg_url or os.environ.get("POSTGRES_URL", _DEFAULT_PG_URL)

    def _connect(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._pg_url)

    def ensure_schema(self) -> None:
        """Idempotently create the brakes schema and kill_switch table."""
        with self._connect() as conn:
            conn.execute(_SCHEMA_SQL)

    def kill(self, agent: str, *, by: str, reason: str = "") -> None:
        """Stop the agent: every runtime must refuse to run it until revived."""
        with self._connect() as conn:
            conn.execute(_UPSERT_SQL, (agent, True, by, reason))

    def revive(self, agent: str, *, by: str) -> None:
        """Clear the kill flag (records who revived; reason is cleared)."""
        with self._connect() as conn:
            conn.execute(_UPSERT_SQL, (agent, False, by, None))

    def is_killed(self, agent: str) -> bool:
        """True iff the agent is currently killed; missing row means not killed."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT killed FROM brakes.kill_switch WHERE agent = %s", (agent,)
            ).fetchone()
        return bool(row[0]) if row is not None else False
