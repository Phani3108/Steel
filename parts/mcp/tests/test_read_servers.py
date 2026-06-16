"""supplier-master, contracts, spend-analytics: reads over seeded cortex/foundry data."""

from __future__ import annotations

import psycopg
import pytest
from steel_mcp import contracts_server, spend_analytics, supplier_master

TENANT = "TEN-0001"
CM = "category_manager"


@pytest.fixture
def seeded(pg: str) -> str:
    with psycopg.connect(pg) as conn:
        n = conn.execute(
            "SELECT count(*) FROM cortex.suppliers WHERE tenant_id = %s", (TENANT,)
        ).fetchone()[0]
    if n == 0:
        pytest.skip("cortex/foundry seed data not ingested")
    return pg


def test_search_suppliers_filters_and_cap(seeded: str) -> None:
    rows = supplier_master.search_suppliers(TENANT, "requester")
    assert 0 < len(rows) <= 25
    assert all(r["tenant_id"] == TENANT for r in rows)

    tier1 = supplier_master.search_suppliers(TENANT, "requester", min_tier=1)
    assert all(r["tier"] == 1 for r in tier1)

    cat = supplier_master.search_suppliers(TENANT, "requester", category="Bearings")
    assert cat and all("Bearings" in r["category"] for r in cat)

    certified = supplier_master.search_suppliers(TENANT, "requester", only_certified=["ISO9001"])
    assert all("ISO9001" in r["certifications"] for r in certified)


def test_get_supplier_round_trip_and_tenant_scope(seeded: str) -> None:
    some = supplier_master.search_suppliers(TENANT, "requester")[0]
    full = supplier_master.get_supplier(TENANT, "requester", some["id"])
    assert full is not None and full["name"] == some["name"]
    assert supplier_master.get_supplier("TEN-OTHER", "requester", some["id"]) is None


def test_search_contracts_role_gate_and_results(seeded: str) -> None:
    forbidden = contracts_server.search_contracts(TENANT, "requester", "payment")
    assert "error" in forbidden and "forbidden role" in forbidden["error"]

    result = contracts_server.search_contracts(TENANT, CM, "payment terms")
    assert "error" not in result
    assert result["clauses"], "FTS over contract chunks should match 'payment terms'"
    assert all(c["tenant_id"] == TENANT for c in result["contracts"])
    clause_ids = {c["contract_id"] for c in result["clauses"]}
    assert clause_ids <= {c["id"] for c in result["contracts"]}


def test_spend_cube_returns_rows(seeded: str) -> None:
    assert "error" in spend_analytics.spend_cube(TENANT, "requester")

    by_cat = spend_analytics.spend_cube(TENANT, CM, by="category", limit=5)
    assert 0 < len(by_cat) <= 5
    assert by_cat[0]["total_usd"] >= by_cat[-1]["total_usd"]
    assert all(r["po_count"] > 0 for r in by_cat)

    by_sup = spend_analytics.spend_cube(TENANT, CM, by="supplier", limit=3)
    assert 0 < len(by_sup) <= 3
    assert "error" in spend_analytics.spend_cube(TENANT, CM, by="invoice")


def test_price_benchmark_for_a_real_sku(seeded: str) -> None:
    with psycopg.connect(seeded) as conn:
        sku = conn.execute(
            "SELECT i.sku FROM foundry.purchase_orders p"
            " JOIN foundry.items i ON i.id = p.item_id AND i.tenant_id = p.tenant_id"
            " WHERE p.tenant_id = %s LIMIT 1",
            (TENANT,),
        ).fetchone()[0]
    bench = spend_analytics.price_benchmark(TENANT, "cpo", sku)
    assert bench["sku"] == sku and bench["n"] > 0
    assert bench["min"] <= bench["avg"] <= bench["max"]
    assert spend_analytics.price_benchmark(TENANT, CM, "SKU-NOPE")["n"] == 0
