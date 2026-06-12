"""Connect-or-skip Postgres fixture (pattern: parts/meter/tests)."""

from __future__ import annotations

import os

import psycopg
import pytest

POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://jai:jai@localhost:5433/jai")


@pytest.fixture
def pg() -> str:
    """Skip cleanly when Postgres is unavailable; otherwise reset jai-mcp's own state."""
    try:
        conn = psycopg.connect(POSTGRES_URL, connect_timeout=2)
    except Exception:
        pytest.skip("postgres unavailable")
    conn.close()

    from jai_mcp.db import ensure_schemas

    ensure_schemas()
    with psycopg.connect(POSTGRES_URL) as conn:
        conn.execute("TRUNCATE sourcing.events, sourcing.bids")
        conn.execute("TRUNCATE intake.requests")
    return POSTGRES_URL
