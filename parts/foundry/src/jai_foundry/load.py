"""Load a generated Borealis dataset into Postgres (schema namespace: ``foundry``).

``ensure_schema`` is idempotent (CREATE SCHEMA/TABLE IF NOT EXISTS); ``load`` truncates
and bulk-inserts, so reloading the same directory is also idempotent. The foundry owns
exactly the ``foundry.*`` schema and never touches any other part's tables (ADR-003).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

DEFAULT_PG_URL = "postgresql://jai:jai@localhost:5433/jai"


@dataclass(frozen=True)
class _TableSpec:
    table: str
    columns: tuple[str, ...]
    ddl_body: str
    json_cols: frozenset[str] = field(default_factory=frozenset)
    date_cols: frozenset[str] = field(default_factory=frozenset)
    ts_cols: frozenset[str] = field(default_factory=frozenset)

    @property
    def filename(self) -> str:
        return f"{self.table}.jsonl"


TABLE_SPECS: tuple[_TableSpec, ...] = (
    _TableSpec(
        "tenants",
        ("id", "name", "region"),
        "id text PRIMARY KEY, name text NOT NULL, region text NOT NULL",
    ),
    _TableSpec(
        "suppliers",
        ("id", "tenant_id", "name", "category", "tier", "country", "certifications",
         "annual_revenue_usd", "risk_score", "red_flag", "payment_terms_days"),
        "id text PRIMARY KEY, tenant_id text NOT NULL, name text NOT NULL, "
        "category text NOT NULL, tier int NOT NULL, country text NOT NULL, "
        "certifications jsonb NOT NULL, annual_revenue_usd numeric(16,2) NOT NULL, "
        "risk_score int NOT NULL, red_flag boolean NOT NULL, payment_terms_days int NOT NULL",
        json_cols=frozenset({"certifications"}),
    ),
    _TableSpec(
        "items",
        ("id", "tenant_id", "sku", "name", "category", "unit_price", "price_history"),
        "id text PRIMARY KEY, tenant_id text NOT NULL, sku text NOT NULL, "
        "name text NOT NULL, category text NOT NULL, unit_price numeric(14,2) NOT NULL, "
        "price_history jsonb NOT NULL",
        json_cols=frozenset({"price_history"}),
    ),
    _TableSpec(
        "contracts",
        ("id", "tenant_id", "supplier_id", "title", "category", "start_date", "end_date",
         "value_usd", "payment_terms_days", "clause_text"),
        "id text PRIMARY KEY, tenant_id text NOT NULL, supplier_id text NOT NULL, "
        "title text NOT NULL, category text NOT NULL, start_date date NOT NULL, "
        "end_date date NOT NULL, value_usd numeric(16,2) NOT NULL, "
        "payment_terms_days int NOT NULL, clause_text text NOT NULL",
        date_cols=frozenset({"start_date", "end_date"}),
    ),
    _TableSpec(
        "purchase_orders",
        ("id", "tenant_id", "supplier_id", "item_id", "qty", "unit_price", "total",
         "ordered_at", "anomaly"),
        "id text PRIMARY KEY, tenant_id text NOT NULL, supplier_id text NOT NULL, "
        "item_id text NOT NULL, qty int NOT NULL, unit_price numeric(14,2) NOT NULL, "
        "total numeric(16,2) NOT NULL, ordered_at timestamp NOT NULL, anomaly text NOT NULL",
        ts_cols=frozenset({"ordered_at"}),
    ),
    _TableSpec(
        "invoices",
        ("id", "tenant_id", "po_id", "amount", "invoiced_at", "anomaly"),
        "id text PRIMARY KEY, tenant_id text NOT NULL, po_id text NOT NULL, "
        "amount numeric(16,2) NOT NULL, invoiced_at timestamp NOT NULL, anomaly text NOT NULL",
        ts_cols=frozenset({"invoiced_at"}),
    ),
    _TableSpec(
        "rfx_events",
        ("id", "tenant_id", "title", "category", "line_items", "invited_supplier_ids",
         "bids", "awarded_supplier_id", "cycle_days"),
        "id text PRIMARY KEY, tenant_id text NOT NULL, title text NOT NULL, "
        "category text NOT NULL, line_items jsonb NOT NULL, "
        "invited_supplier_ids jsonb NOT NULL, bids jsonb NOT NULL, "
        "awarded_supplier_id text NOT NULL, cycle_days int NOT NULL",
        json_cols=frozenset({"line_items", "invited_supplier_ids", "bids"}),
    ),
    _TableSpec(
        "policy_docs",
        ("id", "name", "markdown"),
        "id text PRIMARY KEY, name text NOT NULL, markdown text NOT NULL",
    ),
    _TableSpec(
        "news_snippets",
        ("id", "supplier_id", "published_at", "headline", "body", "signal"),
        "id text PRIMARY KEY, supplier_id text NOT NULL, published_at timestamp NOT NULL, "
        "headline text NOT NULL, body text NOT NULL, signal text NOT NULL",
        ts_cols=frozenset({"published_at"}),
    ),
    _TableSpec(
        "seller_personas",
        ("id", "name", "style", "price_floor_pct", "concession_step_pct", "max_rounds"),
        "id text PRIMARY KEY, name text NOT NULL, style text NOT NULL, "
        "price_floor_pct numeric(6,2) NOT NULL, concession_step_pct numeric(6,2) NOT NULL, "
        "max_rounds int NOT NULL",
    ),
)


def _resolve_pg_url(pg_url: str | None) -> str:
    return pg_url or os.environ.get("POSTGRES_URL", DEFAULT_PG_URL)


def _ensure_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS foundry")
        for spec in TABLE_SPECS:
            cur.execute(
                f"CREATE TABLE IF NOT EXISTS foundry.{spec.table} ({spec.ddl_body})"
            )


def ensure_schema(pg_url: str | None = None, *, conn: psycopg.Connection | None = None) -> None:
    """Idempotently create the ``foundry`` schema and its tables."""
    if conn is not None:
        _ensure_schema(conn)
        return
    with psycopg.connect(_resolve_pg_url(pg_url)) as owned:
        _ensure_schema(owned)
        owned.commit()


def _row(spec: _TableSpec, record: dict[str, Any]) -> tuple[Any, ...]:
    values: list[Any] = []
    for col in spec.columns:
        value = record[col]
        if col in spec.json_cols:
            value = Jsonb(value)
        elif col in spec.date_cols:
            value = date.fromisoformat(value)
        elif col in spec.ts_cols:
            value = datetime.fromisoformat(value)
        values.append(value)
    return tuple(values)


def load(from_dir: Path | str, pg_url: str | None = None) -> dict[str, int]:
    """TRUNCATE-and-insert every entity JSONL from ``from_dir`` into ``foundry.*``.

    Returns rows inserted per table. Reloading the same directory is idempotent.
    """
    src = Path(from_dir)
    counts: dict[str, int] = {}
    with psycopg.connect(_resolve_pg_url(pg_url)) as conn:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            for spec in TABLE_SPECS:
                records = [
                    json.loads(line)
                    for line in (src / spec.filename).read_text().splitlines()
                    if line
                ]
                cur.execute(f"TRUNCATE foundry.{spec.table}")
                placeholders = ", ".join(["%s"] * len(spec.columns))
                cur.executemany(
                    f"INSERT INTO foundry.{spec.table} ({', '.join(spec.columns)}) "
                    f"VALUES ({placeholders})",
                    [_row(spec, r) for r in records],
                )
                counts[spec.table] = len(records)
        conn.commit()
    return counts
