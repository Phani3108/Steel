"""Cortex — the public face of the semantic layer."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import psycopg
from steel_manifest import RunContext

from steel_cortex.ingest import ingest_seed
from steel_cortex.models import RetrievalResult
from steel_cortex.retrieve import Retriever
from steel_cortex.schema import ensure_schema

if TYPE_CHECKING:
    from steel_gateway import GatewayClient

_DEFAULT_PG_URL = "postgresql://steel:steel@localhost:5433/steel"


class Cortex:
    def __init__(self, pg_url: str | None = None, gateway: GatewayClient | None = None):
        self._pg_url = pg_url or os.environ.get("POSTGRES_URL", _DEFAULT_PG_URL)
        self._gateway = gateway
        self._conn: psycopg.Connection | None = None

    @property
    def conn(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self._pg_url, connect_timeout=5)
        return self._conn

    def ensure_schema(self) -> None:
        ensure_schema(self.conn)

    def ingest_seed(self, seed_dir: Path) -> dict[str, int]:
        return ingest_seed(self.conn, Path(seed_dir), gateway=self._gateway)

    def retrieve(self, ctx: RunContext, query: str, *, k: int = 8) -> RetrievalResult:
        return Retriever(self.conn).retrieve(ctx, query, k=k)

    def is_ingested(self) -> bool:
        with self.conn.cursor() as cur:
            cur.execute("SELECT to_regclass('cortex.tenants')")
            if cur.fetchone()[0] is None:
                return False
            cur.execute("SELECT count(*) FROM cortex.tenants")
            return cur.fetchone()[0] > 0

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
