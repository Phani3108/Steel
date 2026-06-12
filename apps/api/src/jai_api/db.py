"""Postgres access for the control plane — one tiny read-only connection helper."""

from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

DEFAULT_PG_URL = "postgresql://jai:jai@localhost:5433/jai"


def pg_url() -> str:
    """Resolved at call time so tests and deployments can swap POSTGRES_URL freely."""
    return os.environ.get("POSTGRES_URL", DEFAULT_PG_URL)


def connect() -> psycopg.Connection[dict[str, Any]]:
    """A short-lived dict-row connection; connect_timeout keeps dead-DB requests fast."""
    return psycopg.connect(pg_url(), row_factory=dict_row, connect_timeout=2)


def ping() -> bool:
    """True when Postgres answers SELECT 1, False on any failure."""
    try:
        with connect() as conn:
            conn.execute("SELECT 1")
        return True
    except (psycopg.Error, OSError):
        return False
