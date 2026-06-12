"""Shared Postgres access for the drivetrain servers.

jai-mcp owns two schema namespaces (ADR-003): ``sourcing`` (RFx events + bids) and
``intake`` (purchase requests). Everything else it touches — ``cortex.*`` and
``foundry.*`` — is read-only over those parts' published table contracts
(precedent: apps/api/src/jai_api/queries.py).
"""

from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

_DEFAULT_PG_URL = "postgresql://jai:jai@localhost:5433/jai"

_SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS sourcing;
CREATE TABLE IF NOT EXISTS sourcing.events (
    id                  text PRIMARY KEY,
    tenant_id           text NOT NULL,
    title               text NOT NULL,
    category            text NOT NULL,
    status              text NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'invited', 'bidding', 'scored', 'awarded')),
    line_items          jsonb NOT NULL DEFAULT '[]',
    invited             jsonb NOT NULL DEFAULT '[]',
    created_by          text NOT NULL,
    created_at          timestamptz NOT NULL DEFAULT now(),
    awarded_supplier_id text,
    award_total_usd     numeric(16,2)
);
CREATE SEQUENCE IF NOT EXISTS sourcing.event_seq;
CREATE TABLE IF NOT EXISTS sourcing.bids (
    id             bigserial PRIMARY KEY,
    event_id       text NOT NULL REFERENCES sourcing.events(id) ON DELETE CASCADE,
    supplier_id    text NOT NULL,
    total_usd      numeric(16,2) NOT NULL,
    lead_time_days int NOT NULL,
    submitted_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS events_tenant_idx ON sourcing.events (tenant_id);
CREATE INDEX IF NOT EXISTS bids_event_idx ON sourcing.bids (event_id);

CREATE SCHEMA IF NOT EXISTS intake;
CREATE TABLE IF NOT EXISTS intake.requests (
    id            text PRIMARY KEY,
    tenant_id     text NOT NULL,
    requested_by  text NOT NULL,
    title         text NOT NULL,
    description   text NOT NULL DEFAULT '',
    category      text NOT NULL DEFAULT '',
    est_value_usd numeric(16,2) NOT NULL,
    status        text NOT NULL
        CHECK (status IN ('submitted', 'auto_approved', 'sourcing_required')),
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE SEQUENCE IF NOT EXISTS intake.request_seq;
CREATE INDEX IF NOT EXISTS requests_tenant_idx ON intake.requests (tenant_id);
"""


def pg_url() -> str:
    return os.environ.get("POSTGRES_URL", _DEFAULT_PG_URL)


def connect() -> psycopg.Connection[dict[str, Any]]:
    """A short-lived autocommit-on-close connection returning dict rows."""
    return psycopg.connect(pg_url(), row_factory=dict_row)


def ensure_schemas() -> None:
    """Idempotently create jai-mcp's own namespaces: sourcing + intake."""
    with connect() as conn:
        conn.execute(_SCHEMA_SQL)


def jsonable(row: dict[str, Any]) -> dict[str, Any]:
    """Make a DB row JSON-friendly (Decimal → float, datetime → isoformat)."""
    out: dict[str, Any] = {}
    for k, v in row.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif type(v).__name__ == "Decimal":
            out[k] = float(v)
        else:
            out[k] = v
    return out
