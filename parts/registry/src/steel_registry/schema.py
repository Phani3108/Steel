"""The `registry` Postgres schema: the agents catalog and its status change log.

`registry.agents` is the live roster — one row per agent, upserted from its manifest,
carrying its card, autonomy level, status, and latest scorecard. `registry.status_log`
is the append-only history of every status change (who, why, when), so a paused or
killed agent always has a paper trail.
"""

from __future__ import annotations

SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS registry;

CREATE TABLE IF NOT EXISTS registry.agents (
    name           text PRIMARY KEY,
    system         text NOT NULL,
    description    text NOT NULL DEFAULT '',
    autonomy_level int  NOT NULL DEFAULT 1,
    pipeline       text NOT NULL DEFAULT 'direct',
    skills         jsonb NOT NULL DEFAULT '[]',
    status         text NOT NULL DEFAULT 'active',
    mandate_usd    numeric(14,2),
    scorecard      jsonb,
    updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS registry.status_log (
    id         bigserial PRIMARY KEY,
    name       text NOT NULL,
    status     text NOT NULL,
    changed_by text NOT NULL,
    reason     text NOT NULL DEFAULT '',
    ts         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS agents_system_name_idx ON registry.agents (system, name);
CREATE INDEX IF NOT EXISTS status_log_name_idx ON registry.status_log (name, ts);
"""
