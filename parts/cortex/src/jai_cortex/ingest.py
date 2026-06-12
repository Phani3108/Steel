"""Ingest the foundry seed into the semantic layer.

Entities land in typed tables; unstructured text (contract clauses, policies, news
bodies, supplier profiles, RFx summaries) is chunked into cortex.chunks with tenant and
ACL columns. Embeddings are computed only when a gateway is supplied AND mock mode is
off — the keyless path is FTS-only and fully deterministic.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import psycopg

if TYPE_CHECKING:  # circular-safe: only for type hints
    from jai_gateway import GatewayClient

# Who may read which doc_type. Mirrors jai_cortex.acl.ROLE_TYPES from the document side.
_DOC_ACL: dict[str, list[str]] = {
    "supplier": ["requester", "category_manager", "cpo", "system"],
    "contract": ["category_manager", "cpo", "system"],
    "policy": ["category_manager", "cpo", "system"],
    "rfx": ["category_manager", "cpo", "system"],
    "news": ["cpo", "system"],
}

_CHUNK_CHARS = 600


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _chunk(body: str) -> list[str]:
    """Split on blank lines, packing paragraphs into ~600-char chunks."""
    chunks: list[str] = []
    current = ""
    for para in body.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if current and len(current) + len(para) + 2 > _CHUNK_CHARS:
            chunks.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        chunks.append(current)
    return chunks


def ingest_seed(
    conn: psycopg.Connection,
    seed_dir: Path,
    *,
    gateway: GatewayClient | None = None,
) -> dict[str, int]:
    seed_dir = Path(seed_dir)
    tenants = _read_jsonl(seed_dir / "tenants.jsonl")
    suppliers = _read_jsonl(seed_dir / "suppliers.jsonl")
    items = _read_jsonl(seed_dir / "items.jsonl")
    contracts = _read_jsonl(seed_dir / "contracts.jsonl")
    policies = _read_jsonl(seed_dir / "policy_docs.jsonl")
    news = _read_jsonl(seed_dir / "news_snippets.jsonl")
    rfx = _read_jsonl(seed_dir / "rfx_events.jsonl")

    supplier_tenant = {s["id"]: s["tenant_id"] for s in suppliers}
    supplier_name = {s["id"]: s["name"] for s in suppliers}

    with conn.cursor() as cur:
        for table in ("chunks", "documents", "news", "contracts", "items", "suppliers", "tenants"):
            cur.execute(f"TRUNCATE cortex.{table} CASCADE")

        cur.executemany(
            "INSERT INTO cortex.tenants (id, name, region) VALUES (%s, %s, %s)",
            [(t["id"], t["name"], t["region"]) for t in tenants],
        )
        cur.executemany(
            """INSERT INTO cortex.suppliers
               (id, tenant_id, name, category, tier, country, certifications,
                annual_revenue_usd, risk_score, red_flag, payment_terms_days)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            [
                (
                    s["id"], s["tenant_id"], s["name"], s["category"], s["tier"], s["country"],
                    json.dumps(s["certifications"]), s["annual_revenue_usd"], s["risk_score"],
                    s["red_flag"], s["payment_terms_days"],
                )
                for s in suppliers
            ],
        )
        cur.executemany(
            """INSERT INTO cortex.items (id, tenant_id, sku, name, category, unit_price)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [
                (i["id"], i["tenant_id"], i["sku"], i["name"], i["category"], i["unit_price"])
                for i in items
            ],
        )
        cur.executemany(
            """INSERT INTO cortex.contracts
               (id, tenant_id, supplier_id, title, category, start_date, end_date,
                value_usd, payment_terms_days)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            [
                (
                    c["id"], c["tenant_id"], c["supplier_id"], c["title"], c["category"],
                    c["start_date"], c["end_date"], c["value_usd"], c["payment_terms_days"],
                )
                for c in contracts
            ],
        )
        cur.executemany(
            """INSERT INTO cortex.news (id, tenant_id, supplier_id, published_at, headline,
                                        signal)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [
                (
                    n["id"], supplier_tenant.get(n["supplier_id"], ""), n["supplier_id"],
                    n["published_at"], n["headline"], n["signal"],
                )
                for n in news
            ],
        )

        docs: list[tuple] = []  # (doc_id, doc_type, tenant_id, source_id, title, body)
        for c in contracts:
            docs.append((f"DOC-{c['id']}", "contract", c["tenant_id"], c["id"], c["title"],
                         c["clause_text"]))
        for p in policies:
            docs.append((f"DOC-{p['id']}", "policy", None, p["id"], p["name"], p["markdown"]))
        for n in news:
            tenant = supplier_tenant.get(n["supplier_id"])
            body = f"{n['headline']}\n\n{n['body']}"
            docs.append((f"DOC-{n['id']}", "news", tenant, n["supplier_id"], n["headline"], body))
        for s in suppliers:
            profile = (
                f"Supplier profile: {s['name']} ({s['id']}). Category: {s['category']}. "
                f"Tier {s['tier']}, based in {s['country']}. "
                f"Certifications: {', '.join(s['certifications']) or 'none'}. "
                f"Risk score {s['risk_score']}/100. Payment terms {s['payment_terms_days']} days."
            )
            docs.append((f"DOC-{s['id']}", "supplier", s["tenant_id"], s["id"], s["name"],
                         profile))
        for r in rfx:
            bid_lines = ", ".join(
                f"{supplier_name.get(b['supplier_id'], b['supplier_id'])} bid "
                f"${b['total']:,.0f} ({b['lead_time_days']}d lead time)"
                for b in r["bids"]
            )
            summary = (
                f"Sourcing event: {r['title']} ({r['id']}), category {r['category']}. "
                f"{len(r['invited_supplier_ids'])} suppliers invited, {len(r['bids'])} bids. "
                f"Bids: {bid_lines}. Awarded to "
                f"{supplier_name.get(r['awarded_supplier_id'], r['awarded_supplier_id'])}. "
                f"Cycle time {r['cycle_days']} days."
            )
            docs.append((f"DOC-{r['id']}", "rfx", r["tenant_id"], r["id"], r["title"], summary))

        cur.executemany(
            """INSERT INTO cortex.documents (doc_id, doc_type, tenant_id, source_id, title,
                                             acl_roles, body)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            [(d[0], d[1], d[2], d[3], d[4], _DOC_ACL[d[1]], d[5]) for d in docs],
        )

        chunk_rows: list[tuple] = []
        chunk_texts: list[str] = []
        for doc_id, doc_type, tenant_id, source_id, _title, body in docs:
            for n, text in enumerate(_chunk(body)):
                chunk_rows.append(
                    (f"{doc_id}#{n}", doc_id, doc_type, tenant_id, source_id,
                     _DOC_ACL[doc_type], text)
                )
                chunk_texts.append(text)

        embeddings: list[list[float] | None] = [None] * len(chunk_rows)
        if gateway is not None and os.environ.get("JAI_MOCK", "1") != "1":
            from jai_manifest import Actor, RunContext

            ctx = RunContext(tenant_id="-", actor=Actor(id="ingest", role="system"))
            for start in range(0, len(chunk_texts), 64):
                batch = chunk_texts[start : start + 64]
                for offset, vec in enumerate(gateway.embed(ctx, texts=batch)):
                    embeddings[start + offset] = vec

        cur.executemany(
            """INSERT INTO cortex.chunks
               (chunk_id, doc_id, doc_type, tenant_id, source_id, acl_roles, text, ts, embedding)
               VALUES (%s, %s, %s, %s, %s, %s, %s, to_tsvector('english', %s), %s)""",
            [row + (row[6], embeddings[idx]) for idx, row in enumerate(chunk_rows)],
        )

    conn.commit()
    return {
        "tenants": len(tenants),
        "suppliers": len(suppliers),
        "items": len(items),
        "contracts": len(contracts),
        "news": len(news),
        "documents": len(docs),
        "chunks": len(chunk_rows),
    }
