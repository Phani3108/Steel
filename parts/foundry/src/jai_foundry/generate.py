"""Deterministic generation of the Borealis Manufacturing dataset.

A single ``random.Random(seed)`` instance is threaded through every generator in a fixed
order; ids are sequential ("SUP-0001") and all dates derive from BASE_DATE — never
``uuid4`` or ``datetime.now`` — so two runs with the same seed are byte-identical.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from jai_foundry import vocab
from jai_foundry.entities import (
    Bid,
    Contract,
    Invoice,
    Item,
    NewsSnippet,
    PolicyDoc,
    PricePoint,
    PurchaseOrder,
    RFxEvent,
    RFxLineItem,
    SellerPersona,
    Supplier,
    Tenant,
)

DEFAULT_SEED = 31082
BASE_DATE = date(2026, 1, 1)  # everything is derived backwards from this anchor

# 24 months of history ending the month before BASE_DATE: 2024-01 .. 2025-12
HISTORY_MONTHS: tuple[tuple[int, int], ...] = tuple(
    (2024 + (m // 12), (m % 12) + 1) for m in range(24)
)

_TENANTS: tuple[tuple[str, str, str], ...] = (
    ("TEN-0001", "Borealis North America", "NA"),
    ("TEN-0002", "Borealis Europe", "EU"),
    ("TEN-0003", "Borealis APAC", "APAC"),
)

N_SUPPLIERS = 250
N_RED_FLAGS = 15
N_ITEMS = 1200
N_CONTRACTS = 80
N_POS = 5000
N_INVOICES = 12000
N_RFX = 40
N_NEWS = 120
ANOMALY_RATE = 0.04
PAYMENT_TERM_CHOICES = (30, 45, 60, 90)


def _money(value: float) -> float:
    return round(value, 2)


def _tenants() -> list[Tenant]:
    return [Tenant(id=i, name=n, region=r) for i, n, r in _TENANTS]


def _supplier_name(rng: random.Random, country: str, used: set[str]) -> str:
    name = (
        f"{rng.choice(vocab.NAME_FIRST)} {rng.choice(vocab.NAME_SECOND)} "
        f"{vocab.COUNTRY_SUFFIX[country]}"
    )
    while name in used:
        name = name.replace(f" {vocab.COUNTRY_SUFFIX[country]}", "", 1)
        name = f"{name} {rng.choice(vocab.NAME_SECOND)} {vocab.COUNTRY_SUFFIX[country]}"
    used.add(name)
    return name


def _suppliers(rng: random.Random, tenants: list[Tenant]) -> list[Supplier]:
    red_indices = set(rng.sample(range(N_SUPPLIERS), N_RED_FLAGS))
    used_names: set[str] = set()
    suppliers: list[Supplier] = []
    for i in range(N_SUPPLIERS):
        # The first 90 suppliers cover every (tenant, category) combination exactly once
        # so downstream generators always find a matching supplier.
        if i < len(tenants) * len(vocab.CATEGORIES):
            tenant = tenants[i % len(tenants)]
            category = vocab.CATEGORY_NAMES[(i // len(tenants)) % len(vocab.CATEGORIES)]
        else:
            tenant = rng.choice(tenants)
            category = rng.choice(vocab.CATEGORY_NAMES)
        country = rng.choice(vocab.REGION_COUNTRIES[tenant.region])
        red = i in red_indices
        suppliers.append(
            Supplier(
                id=f"SUP-{i + 1:04d}",
                tenant_id=tenant.id,
                name=_supplier_name(rng, country, used_names),
                category=category,
                tier=rng.choices((1, 2, 3), weights=(20, 50, 30))[0],
                country=country,
                certifications=sorted(
                    rng.sample(vocab.CERTIFICATIONS, k=rng.randint(1, 4))
                ),
                annual_revenue_usd=round(10 ** rng.uniform(6.0, 8.7), -3),
                risk_score=rng.randint(72, 96) if red else rng.randint(4, 68),
                red_flag=red,
                payment_terms_days=rng.choice(PAYMENT_TERM_CHOICES),
            )
        )
    return suppliers


def _items(rng: random.Random, tenants: list[Tenant]) -> list[Item]:
    items: list[Item] = []
    n_combos = len(tenants) * len(vocab.CATEGORIES)
    for i in range(N_ITEMS):
        # First 4 passes over all combos guarantee every (tenant, category) has items.
        if i < 4 * n_combos:
            tenant = tenants[i % len(tenants)]
            cat_idx = (i // len(tenants)) % len(vocab.CATEGORIES)
            cat_name, cat_code, nouns = vocab.CATEGORIES[cat_idx]
        else:
            tenant = rng.choice(tenants)
            cat_name, cat_code, nouns = rng.choice(vocab.CATEGORIES)
        price = round(10 ** rng.uniform(0.5, 3.7), 2)
        drift = rng.uniform(-0.012, 0.018)  # per-month trend, distinct per item
        history: list[PricePoint] = []
        for year, month in HISTORY_MONTHS:
            history.append(PricePoint(month=f"{year:04d}-{month:02d}", price=_money(price)))
            price = max(0.5, price * (1 + drift + rng.uniform(-0.01, 0.01)))
        items.append(
            Item(
                id=f"ITM-{i + 1:04d}",
                tenant_id=tenant.id,
                sku=f"{cat_code}-{i + 1:05d}",
                name=f"{rng.choice(vocab.ITEM_GRADES)} {rng.choice(nouns)} "
                f"{rng.choice(vocab.ITEM_SPECS)}",
                category=cat_name,
                unit_price=history[-1].price,
                price_history=history,
            )
        )
    return items


def _clause_text(rng: random.Random, payment_terms_days: int) -> str:
    kinds = rng.sample(vocab.CLAUSE_KINDS, k=rng.randint(2, 4))
    kinds.sort(key=vocab.CLAUSE_KINDS.index)  # canonical reading order
    params = {
        "days": payment_terms_days,
        "discount": rng.choice((1.0, 1.5, 2.0)),
        "otd": rng.choice((95, 97, 98)),
        "ppm": rng.choice((250, 500, 1000)),
        "credit": rng.choice((2, 3, 5)),
        "notice": rng.choice((30, 60, 90)),
        "cap_pct": rng.choice((100, 150, 200)),
    }
    return "\n\n".join(rng.choice(vocab.CLAUSE_LIBRARY[kind]).format(**params) for kind in kinds)


def _contracts(rng: random.Random, suppliers: list[Supplier]) -> list[Contract]:
    contracts: list[Contract] = []
    for i, supplier in enumerate(rng.sample(suppliers, N_CONTRACTS)):
        start = BASE_DATE - timedelta(days=rng.randint(30, 720))
        duration_days = {12: 365, 24: 730, 36: 1095}[rng.choice((12, 24, 36))]
        terms = (
            supplier.payment_terms_days
            if rng.random() < 0.8
            else rng.choice(PAYMENT_TERM_CHOICES)
        )
        contracts.append(
            Contract(
                id=f"CON-{i + 1:04d}",
                tenant_id=supplier.tenant_id,
                supplier_id=supplier.id,
                title=f"{rng.choice(vocab.CONTRACT_TITLES)} — {supplier.name}",
                category=supplier.category,
                start_date=start,
                end_date=start + timedelta(days=duration_days),
                value_usd=round(10 ** rng.uniform(4.7, 7.3), -2),
                payment_terms_days=terms,
                clause_text=_clause_text(rng, terms),
            )
        )
    return contracts


def _anomaly_kinds(n: int) -> tuple[str, ...]:
    kinds = ("price_mismatch", "duplicate", "maverick")
    return tuple(kinds[i % len(kinds)] for i in range(n))


def _purchase_orders(
    rng: random.Random, suppliers: list[Supplier], items: list[Item]
) -> list[PurchaseOrder]:
    by_tenant_cat: dict[tuple[str, str], list[Supplier]] = {}
    by_tenant: dict[str, list[Supplier]] = {}
    for s in suppliers:
        by_tenant_cat.setdefault((s.tenant_id, s.category), []).append(s)
        by_tenant.setdefault(s.tenant_id, []).append(s)

    pos: list[PurchaseOrder] = []
    for i in range(N_POS):
        item = rng.choice(items)
        candidates = by_tenant_cat.get((item.tenant_id, item.category)) or by_tenant[item.tenant_id]
        supplier = rng.choice(candidates)
        m = rng.randrange(len(HISTORY_MONTHS))
        year, month = HISTORY_MONTHS[m]
        ordered_at = datetime(
            year, month, rng.randint(1, 28), rng.randint(8, 17), rng.randint(0, 59)
        )
        unit_price = _money(item.price_history[m].price * rng.uniform(0.98, 1.02))
        qty = rng.randint(1, 500)
        pos.append(
            PurchaseOrder(
                id=f"PO-{i + 1:05d}",
                tenant_id=item.tenant_id,
                supplier_id=supplier.id,
                item_id=item.id,
                qty=qty,
                unit_price=unit_price,
                total=_money(qty * unit_price),
                ordered_at=ordered_at,
                anomaly="none",
            )
        )

    n_anomalies = round(N_POS * ANOMALY_RATE)
    indices = sorted(rng.sample(range(N_POS), n_anomalies))
    for kind, idx in zip(_anomaly_kinds(n_anomalies), indices, strict=True):
        po = pos[idx]
        po.anomaly = kind  # type: ignore[assignment]
        if kind == "price_mismatch":
            po.unit_price = _money(po.unit_price * rng.uniform(1.08, 1.30))
            po.total = _money(po.qty * po.unit_price)
        elif kind == "duplicate":
            src = pos[idx - 1] if idx > 0 else pos[idx + 1]
            po.tenant_id = src.tenant_id
            po.supplier_id = src.supplier_id
            po.item_id = src.item_id
            po.qty = src.qty
            po.unit_price = src.unit_price
            po.total = src.total
            po.ordered_at = src.ordered_at
        else:  # maverick: routed to an off-category supplier with no contract basis
            po.supplier_id = rng.choice(by_tenant[po.tenant_id]).id
    return pos


def _invoices(rng: random.Random, pos: list[PurchaseOrder]) -> list[Invoice]:
    # 2 invoices per PO, with a third for 2000 of them: 5000*2 + 2000 = 12000.
    extra_third = set(rng.sample(range(N_POS), N_INVOICES - 2 * N_POS))
    invoices: list[Invoice] = []
    first_invoice_of_po: dict[str, int] = {}
    for i, po in enumerate(pos):
        k = 3 if i in extra_third else 2
        weights = [rng.uniform(0.8, 1.2) for _ in range(k)]
        scale = po.total / sum(weights)
        amounts = [_money(w * scale) for w in weights[:-1]]
        amounts.append(_money(po.total - sum(amounts)))
        days_to_first = rng.randint(5, 45)
        for j, amount in enumerate(amounts):
            idx = len(invoices)
            first_invoice_of_po.setdefault(po.id, idx)
            invoices.append(
                Invoice(
                    id=f"INV-{idx + 1:05d}",
                    tenant_id=po.tenant_id,
                    po_id=po.id,
                    amount=amount,
                    invoiced_at=po.ordered_at + timedelta(days=days_to_first + j * 14),
                    anomaly="none",
                )
            )

    n_anomalies = round(N_INVOICES * ANOMALY_RATE)
    indices = sorted(rng.sample(range(N_INVOICES), n_anomalies))
    for kind, idx in zip(_anomaly_kinds(n_anomalies), indices, strict=True):
        inv = invoices[idx]
        inv.anomaly = kind  # type: ignore[assignment]
        if kind == "price_mismatch":
            inv.amount = _money(inv.amount * rng.uniform(1.05, 1.25))
        elif kind == "duplicate":
            inv.amount = invoices[first_invoice_of_po[inv.po_id]].amount
    return invoices


def _rfx_events(
    rng: random.Random, suppliers: list[Supplier], items: list[Item]
) -> list[RFxEvent]:
    items_by_combo: dict[tuple[str, str], list[Item]] = {}
    for item in items:
        items_by_combo.setdefault((item.tenant_id, item.category), []).append(item)
    combos = sorted(k for k, v in items_by_combo.items() if len(v) >= 2)
    suppliers_by_cat: dict[str, list[Supplier]] = {}
    for s in suppliers:
        suppliers_by_cat.setdefault(s.category, []).append(s)

    events: list[RFxEvent] = []
    for i in range(N_RFX):
        tenant_id, category = rng.choice(combos)
        pool_items = items_by_combo[(tenant_id, category)]
        chosen = rng.sample(pool_items, k=min(len(pool_items), rng.randint(2, 5)))
        line_items = [
            RFxLineItem(item_id=it.id, name=it.name, qty=rng.randint(10, 500)) for it in chosen
        ]
        base_value = sum(li.qty * it.unit_price for li, it in zip(line_items, chosen, strict=True))

        pool = list(suppliers_by_cat[category])
        if len(pool) < 8:  # cross-region sourcing tops up thin categories
            extras = [s for s in suppliers if s.category != category]
            pool.extend(rng.sample(extras, 8 - len(pool)))
        invited = rng.sample(pool, rng.randint(5, min(8, len(pool))))
        bidders = rng.sample(invited, rng.randint(3, min(6, len(invited))))
        bids = [
            Bid(
                supplier_id=s.id,
                total=_money(base_value * rng.uniform(0.85, 1.18)),
                lead_time_days=rng.randint(7, 90),
            )
            for s in bidders
        ]
        # Best bid is determinable: lowest total, ties broken by lead time then id.
        winner = min(bids, key=lambda b: (b.total, b.lead_time_days, b.supplier_id))
        events.append(
            RFxEvent(
                id=f"RFX-{i + 1:04d}",
                tenant_id=tenant_id,
                title=f"RFQ-2025-{i + 1:03d} — {category}",
                category=category,
                line_items=line_items,
                invited_supplier_ids=[s.id for s in invited],
                bids=bids,
                awarded_supplier_id=winner.supplier_id,
                cycle_days=rng.randint(14, 60),
            )
        )
    return events


def _policy_docs() -> list[PolicyDoc]:
    return [
        PolicyDoc(id=f"POL-{i + 1:03d}", name=name, markdown=markdown)
        for i, (name, markdown) in enumerate(vocab.policy_docs())
    ]


def _news(rng: random.Random, suppliers: list[Supplier]) -> list[NewsSnippet]:
    red = [s for s in suppliers if s.red_flag]
    clean = [s for s in suppliers if not s.red_flag]
    snippets: list[NewsSnippet] = []
    for i in range(N_NEWS):
        if i < 88:  # mostly tied to red-flag suppliers, with negative signals
            supplier = rng.choice(red)
            signal = rng.choices(
                ("financial_distress", "recall", "sanction"), weights=(50, 30, 20)
            )[0]
        else:
            supplier = rng.choice(clean)
            signal = rng.choices(
                ("positive", "financial_distress", "recall"), weights=(80, 10, 10)
            )[0]
        headline_tpl, body_tpl = rng.choice(vocab.NEWS_TEMPLATES[signal])
        fills = {
            "name": supplier.name,
            "country": supplier.country,
            "category": supplier.category,
        }
        published_at = datetime(
            BASE_DATE.year - 1, 1, 1, rng.randint(6, 21), rng.randint(0, 59)
        ) + timedelta(days=rng.randint(0, 364))
        snippets.append(
            NewsSnippet(
                id=f"NWS-{i + 1:04d}",
                supplier_id=supplier.id,
                published_at=published_at,
                headline=headline_tpl.format(**fills),
                body=body_tpl.format(**fills),
                signal=signal,  # type: ignore[arg-type]
            )
        )
    return snippets


def _personas() -> list[SellerPersona]:
    return [
        SellerPersona(id=f"PER-{i + 1:04d}", **p)  # type: ignore[arg-type]
        for i, p in enumerate(vocab.SELLER_PERSONAS)
    ]


def _write_jsonl(path: Path, records: Iterable[BaseModel]) -> str:
    """Write canonical JSONL (sorted keys, compact separators); return file sha256."""
    digest = hashlib.sha256()
    with path.open("wb") as f:
        for record in records:
            payload = json.dumps(
                record.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
            )
            line = payload.encode() + b"\n"
            f.write(line)
            digest.update(line)
    return digest.hexdigest()


def generate(seed: int = DEFAULT_SEED, *, out: Path | str) -> dict[str, Any]:
    """Generate the full Borealis dataset into ``out`` and return the manifest.

    Writes one JSONL file per entity type plus ``manifest.json`` containing the seed,
    per-entity counts, and the sha256 of every file. Byte-reproducible per seed.
    """
    rng = random.Random(seed)
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)

    tenants = _tenants()
    suppliers = _suppliers(rng, tenants)
    items = _items(rng, tenants)
    contracts = _contracts(rng, suppliers)
    pos = _purchase_orders(rng, suppliers, items)
    invoices = _invoices(rng, pos)
    rfx_events = _rfx_events(rng, suppliers, items)
    policies = _policy_docs()
    news = _news(rng, suppliers)
    personas = _personas()

    datasets: dict[str, list[BaseModel]] = {
        "tenants": list(tenants),
        "suppliers": list(suppliers),
        "items": list(items),
        "contracts": list(contracts),
        "purchase_orders": list(pos),
        "invoices": list(invoices),
        "rfx_events": list(rfx_events),
        "policy_docs": list(policies),
        "news_snippets": list(news),
        "seller_personas": list(personas),
    }

    counts: dict[str, int] = {}
    shas: dict[str, str] = {}
    for name, records in datasets.items():
        filename = f"{name}.jsonl"
        shas[filename] = _write_jsonl(out_dir / filename, records)
        counts[name] = len(records)

    manifest: dict[str, Any] = {"seed": seed, "counts": counts, "sha256": shas}
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest
