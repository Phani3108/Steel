"""cortex schema — entities + documents + chunks, all carrying tenant and ACL columns."""

from __future__ import annotations

import psycopg

DDL = """
CREATE SCHEMA IF NOT EXISTS cortex;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS cortex.tenants (
    id text PRIMARY KEY,
    name text NOT NULL,
    region text NOT NULL
);

CREATE TABLE IF NOT EXISTS cortex.suppliers (
    id text PRIMARY KEY,
    tenant_id text NOT NULL,
    name text NOT NULL,
    category text NOT NULL,
    tier int NOT NULL,
    country text NOT NULL,
    certifications jsonb NOT NULL DEFAULT '[]',
    annual_revenue_usd numeric NOT NULL,
    risk_score int NOT NULL,
    red_flag boolean NOT NULL DEFAULT false,
    payment_terms_days int NOT NULL
);
CREATE INDEX IF NOT EXISTS suppliers_tenant_idx ON cortex.suppliers (tenant_id);
CREATE INDEX IF NOT EXISTS suppliers_name_idx ON cortex.suppliers (lower(name));

CREATE TABLE IF NOT EXISTS cortex.items (
    id text PRIMARY KEY,
    tenant_id text NOT NULL,
    sku text NOT NULL,
    name text NOT NULL,
    category text NOT NULL,
    unit_price numeric NOT NULL
);
CREATE INDEX IF NOT EXISTS items_tenant_idx ON cortex.items (tenant_id);
CREATE INDEX IF NOT EXISTS items_sku_idx ON cortex.items (sku);

CREATE TABLE IF NOT EXISTS cortex.contracts (
    id text PRIMARY KEY,
    tenant_id text NOT NULL,
    supplier_id text NOT NULL,
    title text NOT NULL,
    category text NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    value_usd numeric NOT NULL,
    payment_terms_days int NOT NULL
);
CREATE INDEX IF NOT EXISTS contracts_tenant_idx ON cortex.contracts (tenant_id);

CREATE TABLE IF NOT EXISTS cortex.news (
    id text PRIMARY KEY,
    tenant_id text NOT NULL,
    supplier_id text NOT NULL,
    published_at timestamptz NOT NULL,
    headline text NOT NULL,
    signal text NOT NULL
);
CREATE INDEX IF NOT EXISTS news_tenant_idx ON cortex.news (tenant_id);
CREATE INDEX IF NOT EXISTS news_supplier_idx ON cortex.news (supplier_id);

CREATE TABLE IF NOT EXISTS cortex.documents (
    doc_id text PRIMARY KEY,
    doc_type text NOT NULL,
    tenant_id text,              -- NULL = visible to every tenant (e.g. policies)
    source_id text NOT NULL,
    title text NOT NULL,
    acl_roles text[] NOT NULL,
    body text NOT NULL
);

CREATE TABLE IF NOT EXISTS cortex.chunks (
    chunk_id text PRIMARY KEY,
    doc_id text NOT NULL REFERENCES cortex.documents (doc_id) ON DELETE CASCADE,
    doc_type text NOT NULL,
    tenant_id text,
    source_id text NOT NULL,
    acl_roles text[] NOT NULL,
    text text NOT NULL,
    ts tsvector,
    embedding vector(1536)
);
CREATE INDEX IF NOT EXISTS chunks_ts_idx ON cortex.chunks USING gin (ts);
CREATE INDEX IF NOT EXISTS chunks_tenant_idx ON cortex.chunks (tenant_id);
CREATE INDEX IF NOT EXISTS chunks_doc_type_idx ON cortex.chunks (doc_type);
"""


def ensure_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(DDL)
    conn.commit()
