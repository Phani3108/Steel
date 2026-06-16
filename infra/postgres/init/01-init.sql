-- STEEL bootstrap: one Postgres instance, logically partitioned.
-- Each part owns exactly one schema namespace and never queries another part's
-- schema directly (ADR-003). LiteLLM gets its own database for virtual keys.

CREATE DATABASE litellm;

\connect steel

CREATE EXTENSION IF NOT EXISTS vector;

-- Schema namespaces, one per part
CREATE SCHEMA IF NOT EXISTS blackbox;   -- steel-blackbox: hash-chained audit events
CREATE SCHEMA IF NOT EXISTS meter;      -- steel-meter: cost ledger
CREATE SCHEMA IF NOT EXISTS cortex;     -- steel-cortex: semantic layer + vectors (P1)
CREATE SCHEMA IF NOT EXISTS engine;     -- steel-engine: runtime checkpoints
CREATE SCHEMA IF NOT EXISTS foundry;    -- steel-foundry: seeded Borealis entities
CREATE SCHEMA IF NOT EXISTS registry;   -- steel-registry: agent cards + status (P3)
