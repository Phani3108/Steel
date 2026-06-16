"""steel-foundry tests: determinism, volumes, anomaly rates, RFx winners, Postgres round-trip."""

from __future__ import annotations

import json
from pathlib import Path

import psycopg
import pytest
from steel_foundry.generate import DEFAULT_SEED, generate
from steel_foundry.load import TABLE_SPECS, load

EXPECTED_COUNTS = {
    "tenants": 3,
    "suppliers": 250,
    "items": 1200,
    "contracts": 80,
    "purchase_orders": 5000,
    "invoices": 12000,
    "rfx_events": 40,
    "policy_docs": 10,
    "news_snippets": 120,
    "seller_personas": 6,
}


def _manifest(d: Path) -> dict:
    return json.loads((d / "manifest.json").read_text())


def _records(d: Path, entity: str) -> list[dict]:
    return [json.loads(line) for line in (d / f"{entity}.jsonl").read_text().splitlines()]


def test_determinism_same_seed_byte_identical(
    seed_dir: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    other = tmp_path_factory.mktemp("borealis_again") / "seed"
    generate(seed=DEFAULT_SEED, out=other)
    first, second = _manifest(seed_dir), _manifest(other)
    assert first["sha256"] == second["sha256"]
    # Belt and braces: raw byte equality on the largest file.
    assert (seed_dir / "invoices.jsonl").read_bytes() == (other / "invoices.jsonl").read_bytes()


def test_different_seed_differs(tmp_path: Path, seed_dir: Path) -> None:
    other = tmp_path / "seed"
    generate(seed=DEFAULT_SEED + 1, out=other)
    assert _manifest(other)["sha256"] != _manifest(seed_dir)["sha256"]


def test_counts_match_spec(seed_dir: Path) -> None:
    assert _manifest(seed_dir)["counts"] == EXPECTED_COUNTS


def test_anomaly_rate_within_3_to_5_percent(seed_dir: Path) -> None:
    for entity in ("purchase_orders", "invoices"):
        records = _records(seed_dir, entity)
        anomalous = [r for r in records if r["anomaly"] != "none"]
        rate = len(anomalous) / len(records)
        assert 0.03 <= rate <= 0.05, f"{entity} anomaly rate {rate:.4f}"
        kinds = {r["anomaly"] for r in anomalous}
        assert kinds == {"price_mismatch", "duplicate", "maverick"}


def test_red_flag_count_about_15(seed_dir: Path) -> None:
    suppliers = _records(seed_dir, "suppliers")
    red = [s for s in suppliers if s["red_flag"]]
    assert 12 <= len(red) <= 18
    assert all(s["risk_score"] >= 70 for s in red)


def test_rfx_winner_is_determinable_best_bid(seed_dir: Path) -> None:
    for event in _records(seed_dir, "rfx_events"):
        assert 3 <= len(event["bids"]) <= 6
        best = min(
            event["bids"], key=lambda b: (b["total"], b["lead_time_days"], b["supplier_id"])
        )
        assert event["awarded_supplier_id"] == best["supplier_id"]
        invited = set(event["invited_supplier_ids"])
        assert {b["supplier_id"] for b in event["bids"]} <= invited


def test_ids_and_dates_are_seed_derived(seed_dir: Path) -> None:
    suppliers = _records(seed_dir, "suppliers")
    assert suppliers[0]["id"] == "SUP-0001"
    assert suppliers[-1]["id"] == "SUP-0250"
    for po in _records(seed_dir, "purchase_orders")[:50]:
        assert po["ordered_at"] < "2026-01-01"  # everything derives from the 2026-01-01 anchor


def test_load_roundtrip_postgres(seed_dir: Path, pg_url: str) -> None:
    counts = load(seed_dir, pg_url=pg_url)
    assert counts == {spec.table: EXPECTED_COUNTS[spec.table] for spec in TABLE_SPECS}

    first_supplier = _records(seed_dir, "suppliers")[0]
    with psycopg.connect(pg_url) as conn:
        row = conn.execute(
            "SELECT name, category, certifications, red_flag, payment_terms_days "
            "FROM foundry.suppliers WHERE id = %s",
            (first_supplier["id"],),
        ).fetchone()
        assert row is not None
        name, category, certifications, red_flag, terms = row
        assert name == first_supplier["name"]
        assert category == first_supplier["category"]
        assert certifications == first_supplier["certifications"]
        assert red_flag == first_supplier["red_flag"]
        assert terms == first_supplier["payment_terms_days"]

    # Reload is idempotent: same counts, no duplicate rows. Done outside the connection
    # above — its open transaction holds ACCESS SHARE locks that would deadlock TRUNCATE.
    load(seed_dir, pg_url=pg_url)
    with psycopg.connect(pg_url) as conn:
        (n,) = conn.execute("SELECT count(*) FROM foundry.invoices").fetchone()
        assert n == EXPECTED_COUNTS["invoices"]
