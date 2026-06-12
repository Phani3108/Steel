"""Shared fixtures: in-memory fakes for the engine's three ports, plus the real echo
manifest. Unit tests run without any service; only the checkpointer test wants Postgres
and skips itself when none is reachable."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest
from engine_fakes import FakeBlackBox, FakeGateway, FakeMeter
from jai_manifest import Actor, AgentManifest, RunContext, load_manifest

ECHO_DIR = Path(__file__).resolve().parents[2] / "agents" / "echo"


@pytest.fixture
def echo_dir() -> Path:
    return ECHO_DIR


@pytest.fixture
def echo_manifest() -> AgentManifest:
    return load_manifest(ECHO_DIR / "manifest.yaml")


@pytest.fixture
def fake_gateway() -> FakeGateway:
    return FakeGateway()


@pytest.fixture
def fake_blackbox() -> FakeBlackBox:
    return FakeBlackBox()


@pytest.fixture
def fake_meter() -> FakeMeter:
    return FakeMeter()


@pytest.fixture
def ctx() -> RunContext:
    return RunContext(
        tenant_id="borealis-na",
        actor=Actor(id="tester", name="Engine tests", role="system"),
    )


@pytest.fixture
def no_checkpointer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the no-Postgres path so unit tests behave identically with or without docker."""
    monkeypatch.setattr("jai_engine.compile._postgres_checkpointer", lambda pg_url=None: None)


@pytest.fixture
def postgres_url() -> str:
    url = os.environ.get("POSTGRES_URL", "postgresql://jai:jai@localhost:5433/jai")
    try:
        psycopg.connect(url, connect_timeout=2).close()
    except Exception:
        pytest.skip("postgres unavailable")
    return url
