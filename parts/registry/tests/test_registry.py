"""Tests for steel_registry — require Postgres, skip cleanly when it is unavailable."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest
from steel_manifest import AgentManifest, AutonomyLevel, Mandate, PromptRef
from steel_registry import AgentRecord, Registry

POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://steel:steel@localhost:5433/steel")

_REPO_ROOT = Path(__file__).resolve().parents[3]
_AGENTS_DIR = _REPO_ROOT / "parts" / "agents"
_RESULTS_DIR = _REPO_ROOT / "evals" / "results"


@pytest.fixture
def registry() -> Registry:
    try:
        conn = psycopg.connect(POSTGRES_URL, connect_timeout=2)
    except Exception:
        pytest.skip("postgres unavailable")
    conn.close()
    r = Registry(POSTGRES_URL)
    r.ensure_schema()
    with psycopg.connect(POSTGRES_URL) as conn:
        conn.execute("TRUNCATE registry.agents, registry.status_log")
    return r


def _manifest(
    name: str = "agent-test",
    *,
    autonomy: AutonomyLevel = AutonomyLevel.L2_ASSIST,
    pipeline: str = "direct",
    skills: list[str] | None = None,
    max_spend: float | None = None,
) -> AgentManifest:
    return AgentManifest(
        name=name,
        description=f"{name} description",
        autonomy_level=autonomy,
        pipeline=pipeline,  # type: ignore[arg-type]
        skills=skills or [],
        prompt=PromptRef(path="prompts/x.md"),
        mandate=Mandate(max_spend_usd=max_spend),
    )


def test_register_manifest_maps_fields(registry: Registry) -> None:
    rec = registry.register_manifest(
        _manifest(
            "agent-mapper",
            autonomy=AutonomyLevel.L3_GATED,
            pipeline="sourcing",
            skills=["rfx.draft", "award.recommend"],
            max_spend=250000.0,
        ),
        system="DRIVETRAIN",
    )
    assert isinstance(rec, AgentRecord)
    assert rec.name == "agent-mapper"
    assert rec.system == "DRIVETRAIN"
    assert rec.description == "agent-mapper description"
    assert rec.autonomy_level == 3
    assert rec.pipeline == "sourcing"
    assert rec.skills == ["rfx.draft", "award.recommend"]
    assert rec.status == "active"
    assert rec.mandate_usd == 250000.0
    assert rec.scorecard is None
    assert rec.updated_at is not None


def test_register_manifest_upsert_preserves_status(registry: Registry) -> None:
    # First registration lands active, then the agent is paused out of band.
    registry.register_manifest(_manifest("agent-upsert"), system="NETWORK")
    registry.set_status("agent-upsert", "paused", by="u-cpo", reason="manual hold")

    # Re-registering the manifest (e.g. after a promotion to L3) must not revive it.
    rec = registry.register_manifest(
        _manifest("agent-upsert", autonomy=AutonomyLevel.L3_GATED),
        system="NETWORK",
    )
    assert rec.status == "paused"  # status owned by set_status, not re-registration
    assert rec.autonomy_level == 3  # card fields still updated

    again = registry.get("agent-upsert")
    assert again is not None and again.status == "paused"


def test_set_status_logs_each_change(registry: Registry) -> None:
    registry.register_manifest(_manifest("agent-logged"), system="NETWORK")

    registry.set_status("agent-logged", "paused", by="u-cpo", reason="freeze")
    rec = registry.set_status("agent-logged", "active", by="u-cm", reason="lifted")
    assert rec.status == "active"

    with psycopg.connect(POSTGRES_URL) as conn:
        rows = conn.execute(
            """
            SELECT status, changed_by, reason FROM registry.status_log
             WHERE name = 'agent-logged' ORDER BY id
            """
        ).fetchall()
    assert rows == [("paused", "u-cpo", "freeze"), ("active", "u-cm", "lifted")]


def test_set_status_unknown_agent_raises(registry: Registry) -> None:
    with pytest.raises(ValueError, match="not in the registry"):
        registry.set_status("agent-ghost", "paused", by="u-cpo")


def test_get_unknown_returns_none(registry: Registry) -> None:
    assert registry.get("agent-nobody") is None


def test_list_orders_by_system_then_name(registry: Registry) -> None:
    registry.register_manifest(_manifest("agent-zeta"), system="NETWORK")
    registry.register_manifest(_manifest("agent-alpha"), system="NETWORK")
    registry.register_manifest(_manifest("agent-bravo"), system="CHASSIS")

    ordered = [(r.system, r.name) for r in registry.list()]
    assert ordered == [
        ("CHASSIS", "agent-bravo"),
        ("NETWORK", "agent-alpha"),
        ("NETWORK", "agent-zeta"),
    ]


def test_sync_agents_loads_on_disk_manifests(registry: Registry) -> None:
    systems = {"agent-supplier-intel": "CHASSIS", "agent-sourcing": "DRIVETRAIN"}
    count = registry.sync_agents(_AGENTS_DIR, systems)
    assert count >= 3  # echo, supplier_intel, sourcing all on disk

    intel = registry.get("agent-supplier-intel")
    assert intel is not None
    assert intel.pipeline == "rag"
    assert intel.system == "CHASSIS"

    # An agent not in the systems map defaults to NETWORK.
    echo = registry.get("agent-echo")
    assert echo is not None
    assert echo.system == "NETWORK"


def test_load_scorecards_attaches_by_agent(registry: Registry) -> None:
    # Need the agents present first; scorecards attach by the "agent" field.
    registry.sync_agents(_AGENTS_DIR, {})
    attached = registry.load_scorecards(_RESULTS_DIR)
    # suite1 = list of 3 supplier-intel cards, suite2 = 1 sourcing card.
    assert attached >= 4

    sourcing = registry.get("agent-sourcing")
    assert sourcing is not None
    assert sourcing.scorecard is not None
    assert sourcing.scorecard["suite"] == "suite2-sourcing"
    assert sourcing.scorecard["pass_rate"] == 1.0
    assert sourcing.scorecard["n_cases"] == 12
    assert sourcing.scorecard["n_passed"] == 12
    assert "ts" in sourcing.scorecard
    # Only the headline keys are stored, not the full failures list.
    assert "failures" not in sourcing.scorecard

    intel = registry.get("agent-supplier-intel")
    assert intel is not None
    assert intel.scorecard is not None
    assert intel.scorecard["suite"].startswith("suite1")
    assert intel.scorecard["pass_rate"] == 1.0


def test_attach_scorecard_unknown_agent_is_noop(registry: Registry) -> None:
    # Attaching to an absent agent neither raises nor creates a row.
    registry.attach_scorecard("agent-absent", {"suite": "s", "pass_rate": 1.0})
    assert registry.get("agent-absent") is None
