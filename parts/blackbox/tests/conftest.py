"""Postgres-or-skip fixture. Tests own the local/CI database: the chain is global and
append-only, so isolation is a TRUNCATE at setup, not per-row cleanup."""

from __future__ import annotations

import os
from collections.abc import Iterator

import psycopg
import pytest
from jai_blackbox import BlackBox

PG_URL = os.environ.get("POSTGRES_URL", "postgresql://jai:jai@localhost:5433/jai")


@pytest.fixture
def box() -> Iterator[BlackBox]:
    try:
        conn = psycopg.connect(PG_URL, connect_timeout=2)
    except psycopg.OperationalError:
        pytest.skip("postgres unavailable")
    blackbox = BlackBox(PG_URL)
    blackbox.ensure_schema()
    with conn:
        conn.execute("TRUNCATE blackbox.audit_events RESTART IDENTITY")
    conn.close()
    yield blackbox
