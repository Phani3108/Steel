"""Fixtures for jai-foundry tests. Postgres-backed tests skip when no server is reachable."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest
from jai_foundry.generate import DEFAULT_SEED, generate


@pytest.fixture(scope="session")
def seed_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One generated dataset shared by all tests in the session."""
    out = tmp_path_factory.mktemp("borealis") / "seed"
    generate(seed=DEFAULT_SEED, out=out)
    return out


@pytest.fixture
def pg_url() -> str:
    url = os.environ.get("POSTGRES_URL", "postgresql://jai:jai@localhost:5433/jai")
    try:
        conn = psycopg.connect(url, connect_timeout=2)
    except Exception:
        pytest.skip("postgres unavailable")
    else:
        conn.close()
    return url
