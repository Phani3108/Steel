"""Fixtures: an in-process API client and a postgres-or-skip seeded database."""

from __future__ import annotations

import os
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient
from steel_api.main import create_app
from steel_manifest import Actor, AuditEvent, RunContext, canonical_json, sha256_hex
from psycopg.types.json import Jsonb

POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://steel:steel@localhost:5433/steel")

GENESIS_HASH = "0" * 64

# Minimal mirrors of the published table contracts owned by steel-blackbox and
# steel-meter — created here only so the suite is self-sufficient on a fresh
# database. IF NOT EXISTS makes this a no-op when the owning parts already ran.
_CONTRACT_DDL = """
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
"""

_AUDIT_INSERT = """
INSERT INTO blackbox.audit_events (
    event_id, ts, tenant_id, actor_id, actor_role, agent, run_id, trace_id,
    action, outcome, policy_version, input_sha256, detail, canonical, prev_hash, hash
) VALUES (
    %(event_id)s, %(ts)s, %(tenant_id)s, %(actor_id)s, %(actor_role)s, %(agent)s,
    %(run_id)s, %(trace_id)s, %(action)s, %(outcome)s, %(policy_version)s,
    %(input_sha256)s, %(detail)s, %(canonical)s, %(prev_hash)s, %(hash)s
)
"""

_METER_INSERT = """
INSERT INTO meter.task_ledger
    (tenant_id, agent, run_id, trace_id, action, model, model_group,
     input_tokens, output_tokens, cost_usd, detail)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '{}')
"""


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def seeded_pg() -> dict[str, Any]:
    """Skip without Postgres; otherwise reset both tables and seed one run:
    three correctly chained audit events plus two metered model calls."""
    try:
        conn = psycopg.connect(POSTGRES_URL, connect_timeout=2)
    except Exception:
        pytest.skip("postgres unavailable")

    ctx = RunContext(
        tenant_id="acme",
        actor=Actor(id="u1", name="Pat", role="category_manager"),
        agent="agent-echo",
    )
    script = [
        ("run.start", "ok", {}),
        ("model.call", "ok", {"model_group": "reasoning"}),
        ("run.end", "ok", {"result": "done"}),
    ]
    with conn:
        conn.execute(_CONTRACT_DDL)
        conn.execute("TRUNCATE blackbox.audit_events RESTART IDENTITY")
        conn.execute("TRUNCATE meter.task_ledger RESTART IDENTITY")
        prev = GENESIS_HASH
        for action, outcome, detail in script:
            event = AuditEvent(
                tenant_id=ctx.tenant_id,
                actor_id=ctx.actor.id,
                actor_role=ctx.actor.role,
                agent=ctx.agent,
                run_id=ctx.run_id,
                trace_id=ctx.trace_id,
                action=action,
                outcome=outcome,
                detail=detail,
            )
            canonical = canonical_json(event)
            chain_hash = sha256_hex(prev + canonical)
            conn.execute(
                _AUDIT_INSERT,
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
                    "detail": Jsonb(event.detail),
                    "canonical": canonical,
                    "prev_hash": prev,
                    "hash": chain_hash,
                },
            )
            prev = chain_hash
        for model, group, in_tok, out_tok, cost in (
            ("gpt-5o", "reasoning", 1000, 200, "0.010000"),
            ("gpt-5o-mini", "fast", 100, 20, "0.001000"),
        ):
            conn.execute(
                _METER_INSERT,
                (
                    ctx.tenant_id, ctx.agent, ctx.run_id, ctx.trace_id,
                    "model.call", model, group, in_tok, out_tok, cost,
                ),
            )
    conn.close()
    return {"run_id": ctx.run_id, "tenant_id": ctx.tenant_id, "agent": ctx.agent}
