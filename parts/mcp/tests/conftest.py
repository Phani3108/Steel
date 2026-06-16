"""Connect-or-skip Postgres fixture (pattern: parts/meter/tests)."""

from __future__ import annotations

import os

import psycopg
import pytest

POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://steel:steel@localhost:5433/steel")


@pytest.fixture
def pg() -> str:
    """Skip cleanly when Postgres is unavailable; otherwise reset steel-mcp's own state."""
    try:
        conn = psycopg.connect(POSTGRES_URL, connect_timeout=2)
    except Exception:
        pytest.skip("postgres unavailable")
    conn.close()

    from steel_mcp.db import ensure_schemas

    ensure_schemas()
    with psycopg.connect(POSTGRES_URL) as conn:
        conn.execute("TRUNCATE sourcing.events, sourcing.bids")
        conn.execute("TRUNCATE intake.requests")
    return POSTGRES_URL
