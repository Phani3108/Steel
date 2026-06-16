"""Tests for steel_meter.ledger — require Postgres, skip cleanly when it is unavailable."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import psycopg
import pytest
from steel_manifest import Actor, RunContext
from steel_meter import CostRow, Meter

POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://steel:steel@localhost:5433/steel")


@pytest.fixture
def meter() -> Meter:
    try:
        conn = psycopg.connect(POSTGRES_URL, connect_timeout=2)
    except Exception:
        pytest.skip("postgres unavailable")
    conn.close()
    m = Meter(POSTGRES_URL)
    m.ensure_schema()
    with psycopg.connect(POSTGRES_URL) as conn:
        conn.execute("TRUNCATE meter.task_ledger")
    return m


def _ctx(tenant_id: str = "acme", agent: str | None = "agent-echo") -> RunContext:
    return RunContext(
        tenant_id=tenant_id,
        actor=Actor(id="u1", name="Pat", role="category_manager"),
        agent=agent,
    )


def test_record_and_run_total_round_trip_decimal_precision(meter: Meter) -> None:
    ctx = _ctx()
    row_id = meter.record(
        ctx,
        action="model.call",
        model="gpt-5o",
        model_group="reasoning",
        input_tokens=1000,
        output_tokens=200,
        cost_usd=0.123456,
    )
    assert isinstance(row_id, int)
    meter.record(
        ctx,
        action="model.call",
        model="gpt-5o-mini",
        model_group="fast",
        input_tokens=10,
        output_tokens=5,
        cost_usd=0.000001,
    )
    total = meter.run_total(ctx.run_id)
    assert isinstance(total, Decimal)
    assert total == Decimal("0.123457")
    assert meter.run_total("run_does_not_exist") == Decimal("0")


def test_ctx_fields_land_in_the_row(meter: Meter) -> None:
    ctx = _ctx(tenant_id="globex", agent="agent-sourcing")
    row_id = meter.record(
        ctx,
        action="tool.call",
        model=None,
        model_group=None,
        input_tokens=0,
        output_tokens=0,
        cost_usd=0.0,
        detail={"tool": "supplier-master"},
    )
    with psycopg.connect(POSTGRES_URL) as conn:
        row = conn.execute(
            "SELECT tenant_id, agent, run_id, trace_id, action, model, model_group,"
            "       input_tokens, output_tokens, cost_usd, detail, ts"
            "  FROM meter.task_ledger WHERE id = %s",
            (row_id,),
        ).fetchone()
    assert row is not None
    assert row[0] == "globex"
    assert row[1] == "agent-sourcing"
    assert row[2] == ctx.run_id
    assert row[3] == ctx.trace_id
    assert row[4] == "tool.call"
    assert row[5] is None
    assert row[6] is None
    assert (row[7], row[8]) == (0, 0)
    assert row[9] == Decimal("0")
    assert row[10] == {"tool": "supplier-master"}
    assert row[11].tzinfo is not None


def test_costs_by_each_dimension(meter: Meter) -> None:
    ctx_a1 = _ctx(tenant_id="acme", agent="agent-echo")
    ctx_a2 = _ctx(tenant_id="acme", agent="agent-sourcing")
    ctx_b = _ctx(tenant_id="globex", agent="agent-echo")
    meter.record(
        ctx_a1,
        action="model.call",
        model="m1",
        model_group="reasoning",
        input_tokens=100,
        output_tokens=10,
        cost_usd=0.10,
    )
    meter.record(
        ctx_a2,
        action="model.call",
        model="m2",
        model_group="fast",
        input_tokens=50,
        output_tokens=5,
        cost_usd=0.02,
    )
    meter.record(
        ctx_b,
        action="model.call",
        model="m1",
        model_group="reasoning",
        input_tokens=200,
        output_tokens=20,
        cost_usd=0.30,
    )

    by_tenant = {r.key: r for r in meter.costs_by("tenant_id")}
    assert set(by_tenant) == {"acme", "globex"}
    assert by_tenant["acme"] == CostRow(
        key="acme", calls=2, input_tokens=150, output_tokens=15, cost_usd=Decimal("0.12")
    )
    assert by_tenant["globex"].cost_usd == Decimal("0.30")

    by_agent = {r.key: r for r in meter.costs_by("agent")}
    assert by_agent["agent-echo"].calls == 2
    assert by_agent["agent-echo"].cost_usd == Decimal("0.40")
    assert by_agent["agent-sourcing"].calls == 1

    by_run = {r.key: r for r in meter.costs_by("run_id")}
    assert set(by_run) == {ctx_a1.run_id, ctx_a2.run_id, ctx_b.run_id}
    assert by_run[ctx_a1.run_id].cost_usd == Decimal("0.10")

    by_group = {r.key: r for r in meter.costs_by("model_group")}
    assert by_group["reasoning"] == CostRow(
        key="reasoning", calls=2, input_tokens=300, output_tokens=30, cost_usd=Decimal("0.40")
    )
    assert by_group["fast"].cost_usd == Decimal("0.02")


def test_costs_by_since_filter_and_null_key(meter: Meter) -> None:
    meter.record(
        _ctx(agent=None),
        action="retrieval",
        model=None,
        model_group=None,
        input_tokens=1,
        output_tokens=1,
        cost_usd=0.01,
    )
    # NULL agent / model_group aggregate under the "-" key (matches RunContext tags).
    assert [r.key for r in meter.costs_by("agent")] == ["-"]
    assert meter.costs_by("tenant_id", since=datetime.now(UTC) - timedelta(hours=1)) != []
    assert meter.costs_by("tenant_id", since=datetime.now(UTC) + timedelta(hours=1)) == []


def test_costs_by_rejects_unknown_dimension(meter: Meter) -> None:
    with pytest.raises(ValueError):
        meter.costs_by("detail")  # type: ignore[arg-type]
