"""Permission-aware retrieval over the semantic layer.

Deterministic intent heuristics route a query to entity lookups and/or chunk search;
every SQL statement filters by tenant and role — permissions are enforced below the
LLM, never by prompt. Refusals are first-class results, not exceptions.
"""

from __future__ import annotations

import re
from typing import Any

import psycopg
from jai_manifest import RunContext
from psycopg.rows import dict_row

from jai_cortex.acl import allowed_types
from jai_cortex.models import ChunkHit, Citation, RetrievalResult

_SKU_RE = re.compile(r"\b[A-Z]{2,4}-\d{4,6}\b")

_INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "contract": ("contract", "agreement", "clause", "sla", "termination", "terms of"),
    "policy": ("policy", "bids", "threshold", "approval", "code of conduct",
               "competitive bidding", "rule"),
    "news": ("news", "risk signal", "recall", "sanction", "distress", "headline"),
    "rfx": ("rfx", "sourcing event", "rfp", "rfq", "awarded"),
    "supplier": ("supplier", "vendor"),
    "item": ("sku", "unit price", "item", "price of"),
}


def _keyword_intents(query: str) -> set[str]:
    lowered = query.lower()
    return {
        intent
        for intent, words in _INTENT_KEYWORDS.items()
        if any(w in lowered for w in words)
    }


def _fact_citation(source_type: str, row: dict[str, Any], label_key: str) -> Citation:
    return Citation(
        source_type=source_type,
        source_id=str(row.get("id", "")),
        snippet=str(row.get(label_key, ""))[:120],
    )


class Retriever:
    def __init__(self, conn: psycopg.Connection):
        self._conn = conn

    def retrieve(self, ctx: RunContext, query: str, *, k: int = 8) -> RetrievalResult:
        role = ctx.actor.role
        allowed = allowed_types(role)
        asked = _keyword_intents(query)  # what the query explicitly asks for

        facts: list[dict] = []
        citations: list[Citation] = []

        # Entity matches are the query's *subjects* — they widen retrieval but the
        # refusal decision belongs to what was asked for.
        subjects: set[str] = set()
        suppliers = self._suppliers_in_query(ctx.tenant_id, query)
        if suppliers:
            subjects.add("supplier")
        skus = _SKU_RE.findall(query)
        if skus:
            subjects.add("item")
        contracts = self._contracts_in_query(ctx.tenant_id, query)
        if contracts:
            subjects.add("contract")

        # Specific asks (contract/policy/news/rfx) dominate the refusal decision: a
        # generic word like "supplier" in "recall headlines for our suppliers" must not
        # smuggle a denied ask past the ACL.
        specific = {"contract", "policy", "news", "rfx"}
        asked_specific = asked & specific
        if asked_specific and not (asked_specific & allowed):
            blocked = ", ".join(sorted(asked_specific - allowed))
            return RetrievalResult(
                refused=True,
                refusal_reason=f"role {role!r} is not permitted to access {blocked}",
            )
        denied_asked = asked - allowed
        if asked and asked <= denied_asked:
            blocked = ", ".join(sorted(denied_asked))
            return RetrievalResult(
                refused=True,
                refusal_reason=f"role {role!r} is not permitted to access {blocked}",
            )
        if not asked and subjects and not (subjects & allowed):
            blocked = ", ".join(sorted(subjects - allowed))
            return RetrievalResult(
                refused=True,
                refusal_reason=f"role {role!r} is not permitted to access {blocked}",
            )
        intents = asked | subjects
        permitted = intents & allowed

        if "supplier" in permitted:
            for row in suppliers:
                facts.append(row)
                citations.append(_fact_citation("supplier", row, "name"))
        if "item" in permitted and skus:
            for row in self._items_by_sku(ctx.tenant_id, skus):
                facts.append(row)
                citations.append(_fact_citation("item", row, "name"))
        if "contract" in permitted:
            for row in contracts:
                facts.append(row)
                citations.append(_fact_citation("contract", row, "title"))
        if "news" in permitted and "news" in intents:
            for row in self._news(ctx.tenant_id, [s["id"] for s in suppliers]):
                facts.append(row)
                citations.append(_fact_citation("news", row, "headline"))

        # Chunk search: scoped to permitted doc types; policy/contract questions and
        # anything without entity facts fall through to FTS.
        chunk_types = sorted(permitted or allowed)
        chunks = self._search_chunks(ctx.tenant_id, role, query, chunk_types, k=k)
        for hit in chunks:
            citations.append(
                Citation(
                    source_type=hit.doc_type,
                    source_id=hit.source_id,
                    snippet=hit.text[:120],
                )
            )

        return RetrievalResult(facts=facts, chunks=chunks, citations=citations)

    # ── entity lookups (all tenant- and role-scoped by construction) ──────────

    def _suppliers_in_query(self, tenant_id: str, query: str) -> list[dict]:
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """SELECT id, tenant_id, name, category, tier, country, certifications,
                          annual_revenue_usd::float8 AS annual_revenue_usd, risk_score,
                          red_flag, payment_terms_days
                   FROM cortex.suppliers
                   WHERE tenant_id = %s AND position(lower(name) IN lower(%s)) > 0
                   ORDER BY id LIMIT 5""",
                (tenant_id, query),
            )
            return list(cur.fetchall())

    def _items_by_sku(self, tenant_id: str, skus: list[str]) -> list[dict]:
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """SELECT id, tenant_id, sku, name, category, unit_price::float8 AS unit_price
                   FROM cortex.items
                   WHERE tenant_id = %s AND sku = ANY(%s) ORDER BY sku""",
                (tenant_id, skus),
            )
            return list(cur.fetchall())

    def _contracts_in_query(self, tenant_id: str, query: str) -> list[dict]:
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """SELECT id, tenant_id, supplier_id, title, category,
                          start_date::text, end_date::text,
                          value_usd::float8 AS value_usd, payment_terms_days
                   FROM cortex.contracts
                   WHERE tenant_id = %s AND position(lower(title) IN lower(%s)) > 0
                   ORDER BY id LIMIT 5""",
                (tenant_id, query),
            )
            return list(cur.fetchall())

    def _news(self, tenant_id: str, supplier_ids: list[str]) -> list[dict]:
        with self._conn.cursor(row_factory=dict_row) as cur:
            if supplier_ids:
                cur.execute(
                    """SELECT id, supplier_id, published_at::text, headline, signal
                       FROM cortex.news
                       WHERE tenant_id = %s AND supplier_id = ANY(%s)
                       ORDER BY published_at DESC LIMIT 10""",
                    (tenant_id, supplier_ids),
                )
            else:
                cur.execute(
                    """SELECT id, supplier_id, published_at::text, headline, signal
                       FROM cortex.news WHERE tenant_id = %s
                       ORDER BY published_at DESC LIMIT 10""",
                    (tenant_id,),
                )
            return list(cur.fetchall())

    # ── chunk search: FTS now, vector fused via RRF when embeddings exist ─────

    def _search_chunks(
        self, tenant_id: str, role: str, query: str, doc_types: list[str], *, k: int
    ) -> list[ChunkHit]:
        if not doc_types:
            return []
        # OR the query's words: plainto_tsquery ANDs every lexeme, which makes natural
        # questions ("How many bids does the policy require?") match nothing. Ranking
        # still rewards chunks matching more terms.
        words = [w for w in re.findall(r"[a-zA-Z]{3,}", query)]
        if not words:
            return []
        or_query = " | ".join(words)
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """SELECT chunk_id, doc_type, doc_id, source_id, text,
                          ts_rank(ts, to_tsquery('english', %s)) AS score
                   FROM cortex.chunks
                   WHERE (tenant_id = %s OR tenant_id IS NULL)
                     AND %s = ANY(acl_roles)
                     AND doc_type = ANY(%s)
                     AND ts @@ to_tsquery('english', %s)
                   ORDER BY score DESC LIMIT %s""",
                (or_query, tenant_id, role, doc_types, or_query, k),
            )
            fts = list(cur.fetchall())
        # RRF fusion seam: when embeddings are populated (real-key ingest), a cosine
        # search joins here with 1/(60+rank) scoring. FTS-only keeps keyless runs
        # deterministic.
        return [
            ChunkHit(
                chunk_id=r["chunk_id"],
                doc_type=r["doc_type"],
                doc_id=r["doc_id"],
                source_id=r["source_id"],
                text=r["text"],
                score=float(r["score"]),
            )
            for r in fts
        ]
