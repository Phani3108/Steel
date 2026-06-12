import os
from pathlib import Path

import psycopg
import pytest
from jai_cortex import Cortex

POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://jai:jai@localhost:5433/jai")
SEED_DIR = Path(__file__).resolve().parents[3] / "data" / "seed"


def _postgres_available() -> bool:
    try:
        psycopg.connect(POSTGRES_URL, connect_timeout=2).close()
    except Exception:
        return False
    return True


@pytest.fixture(scope="session")
def cortex() -> Cortex:
    if not _postgres_available():
        pytest.skip("postgres unavailable")
    c = Cortex(POSTGRES_URL)
    c.ensure_schema()
    if not c.is_ingested():
        c.ingest_seed(SEED_DIR)
    yield c
    c.close()
