"""Tests for the control plane. /health works with no services at all; the data
routes run against the postgres-or-skip seeded fixture."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

# Nothing listens on the discard port — connections are refused immediately,
# which is exactly the "postgres down" condition the app must absorb.
_DEAD_PG_URL = "postgresql://jai:jai@127.0.0.1:9/jai"


def test_health_shape_without_any_service(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert isinstance(body["postgres"], bool)


def test_health_reports_postgres_false_when_down(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POSTGRES_URL", _DEAD_PG_URL)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "postgres": False}


@pytest.mark.parametrize("path", ["/costs", "/runs", "/runs/run_x/events", "/audit/verify"])
def test_data_routes_degrade_to_503_when_postgres_down(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    monkeypatch.setenv("POSTGRES_URL", _DEAD_PG_URL)
    resp = client.get(path)
    assert resp.status_code == 503
    assert resp.json()["error"] == "postgres_unavailable"


def test_costs_rejects_unknown_dimension(client: TestClient) -> None:
    assert client.get("/costs?by=color").status_code == 422


def test_costs_rollup_by_tenant_and_model_group(
    seeded_pg: dict[str, Any], client: TestClient
) -> None:
    resp = client.get("/costs", params={"by": "tenant_id"})
    assert resp.status_code == 200
    rows = resp.json()
    assert isinstance(rows, list)
    acme = next(r for r in rows if r["key"] == seeded_pg["tenant_id"])
    assert acme["calls"] == 2
    assert acme["input_tokens"] == 1100
    assert acme["output_tokens"] == 220
    assert acme["cost_usd"] == pytest.approx(0.011)

    by_group = client.get("/costs", params={"by": "model_group"}).json()
    assert {r["key"] for r in by_group} == {"reasoning", "fast"}


def test_runs_lists_seeded_run(seeded_pg: dict[str, Any], client: TestClient) -> None:
    resp = client.get("/runs", params={"limit": 20})
    assert resp.status_code == 200
    rows = resp.json()
    assert isinstance(rows, list)
    run = next(r for r in rows if r["run_id"] == seeded_pg["run_id"])
    assert run["tenant_id"] == seeded_pg["tenant_id"]
    assert run["agent"] == seeded_pg["agent"]
    assert run["events"] == 3
    assert run["outcome"] == "ok"  # from the run.end event
    assert run["first_ts"] <= run["last_ts"]


def test_run_events_ordered_without_hash_internals(
    seeded_pg: dict[str, Any], client: TestClient
) -> None:
    resp = client.get(f"/runs/{seeded_pg['run_id']}/events")
    assert resp.status_code == 200
    events = resp.json()
    assert [e["action"] for e in events] == ["run.start", "model.call", "run.end"]
    assert [e["seq"] for e in events] == sorted(e["seq"] for e in events)
    for event in events:
        assert {"ts", "action", "outcome", "detail"} <= event.keys()
        assert not {"canonical", "prev_hash", "hash", "input_sha256"} & event.keys()
    assert events[2]["detail"] == {"result": "done"}


def test_run_events_empty_for_unknown_run(seeded_pg: dict[str, Any], client: TestClient) -> None:
    resp = client.get("/runs/run_does_not_exist/events")
    assert resp.status_code == 200
    assert resp.json() == []


def test_audit_verify_recomputes_intact_chain(
    seeded_pg: dict[str, Any], client: TestClient
) -> None:
    resp = client.get("/audit/verify")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "checked": 3, "broken_at_seq": None}


def test_network_reference_topology_when_fleet_unavailable() -> None:
    """Without a live fleet, /network returns the canonical structure marked not-live."""
    from jai_api.fleet import network_topology

    topo = network_topology(None)
    assert topo["live"] is False
    assert {n["id"] for n in topo["nodes"]} >= {"agent-orchestrator", "agent-negotiator"}
    assert all("source" in e and "target" in e for e in topo["edges"])
