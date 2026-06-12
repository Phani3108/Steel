"""Capability (T1–T5), tenant-isolation, and ACL-refusal tests against the real seed."""

import json
from pathlib import Path

from jai_manifest import Actor, RunContext

SEED_DIR = Path(__file__).resolve().parents[3] / "data" / "seed"


def _rows(name: str) -> list[dict]:
    return [json.loads(line) for line in (SEED_DIR / name).read_text().splitlines() if line]


def _ctx(role: str, tenant_id: str) -> RunContext:
    return RunContext(tenant_id=tenant_id, actor=Actor(id="test", role=role))


def test_t1_supplier_by_name(cortex):
    supplier = sorted(_rows("suppliers.jsonl"), key=lambda s: s["id"])[0]
    ctx = _ctx("requester", supplier["tenant_id"])
    result = cortex.retrieve(ctx, f"Tell me about supplier {supplier['name']}")
    assert not result.refused
    facts = [f for f in result.facts if f.get("id") == supplier["id"]]
    assert facts and facts[0]["country"] == supplier["country"]
    assert any(c.source_type == "supplier" for c in result.citations)


def test_t2_item_by_sku(cortex):
    item = sorted(_rows("items.jsonl"), key=lambda i: i["id"])[0]
    ctx = _ctx("requester", item["tenant_id"])
    result = cortex.retrieve(ctx, f"What is the unit price of {item['sku']}?")
    assert not result.refused
    facts = [f for f in result.facts if f.get("sku") == item["sku"]]
    assert facts and abs(facts[0]["unit_price"] - item["unit_price"]) < 1e-6


def test_t3_contract_by_title_role_gated(cortex):
    contract = sorted(_rows("contracts.jsonl"), key=lambda c: c["id"])[0]
    query = f"What are the terms of the contract '{contract['title']}'?"
    ok = cortex.retrieve(_ctx("category_manager", contract["tenant_id"]), query)
    assert not ok.refused
    assert any(f.get("id") == contract["id"] for f in ok.facts)
    assert any(h.doc_type == "contract" for h in ok.chunks) or ok.facts

    denied = cortex.retrieve(_ctx("requester", contract["tenant_id"]), query)
    assert denied.refused and "contract" in (denied.refusal_reason or "")


def test_t4_policy_search(cortex):
    result = cortex.retrieve(
        _ctx("category_manager", "TEN-0001"), "How many bids does the policy require?"
    )
    assert not result.refused
    assert any(h.doc_type == "policy" for h in result.chunks)

    refused = cortex.retrieve(_ctx("requester", "TEN-0001"), "What does the policy require?")
    assert refused.refused


def test_t5_news_cpo_only(cortex):
    news = sorted(_rows("news_snippets.jsonl"), key=lambda n: n["id"])[0]
    suppliers = {s["id"]: s for s in _rows("suppliers.jsonl")}
    supplier = suppliers[news["supplier_id"]]
    query = f"Any news or risk signals about {supplier['name']}?"

    ok = cortex.retrieve(_ctx("cpo", supplier["tenant_id"]), query)
    assert not ok.refused
    assert any(f.get("supplier_id") == supplier["id"] for f in ok.facts)

    denied = cortex.retrieve(_ctx("category_manager", supplier["tenant_id"]), query)
    assert denied.refused and "news" in (denied.refusal_reason or "")


def test_tenant_isolation(cortex):
    suppliers = sorted(_rows("suppliers.jsonl"), key=lambda s: s["id"])
    supplier = suppliers[0]
    home = supplier["tenant_id"]
    other_tenant = next(s["tenant_id"] for s in suppliers if s["tenant_id"] != home)
    result = cortex.retrieve(
        _ctx("cpo", other_tenant), f"Tell me about supplier {supplier['name']}"
    )
    assert all(f.get("id") != supplier["id"] for f in result.facts)
