# jai-foundry — the parts foundry

**System:** CHASSIS · **Standalone use case:** a deterministic synthetic-procurement-data
factory — drop it into any procurement, ERP, or agent-eval project that needs a realistic,
byte-reproducible dataset (suppliers, contracts, POs, invoices, RFx, policies, news) with
labeled anomalies. No LLM, no network, no license-encumbered data.

The foundry forges **Borealis Manufacturing**, a fictional $800M industrial manufacturer
operating as three tenants (North America / Europe / APAC). Every JAI demo and eval is
grounded in this dataset, so results are comparable run-to-run.

## What it forges (seed `31082` by default)

| Entity | Count | Notes |
|---|---|---|
| tenants | 3 | Borealis NA / EU / APAC |
| suppliers | 250 | 30 UNSPSC-flavored categories, 15 red-flagged |
| items | 1,200 | 24-month price history with per-item drift |
| contracts | 80 | clause text assembled from a legal template library |
| purchase_orders | 5,000 | 4% labeled anomalies: price_mismatch / duplicate / maverick |
| invoices | 12,000 | 4% labeled anomalies, 2–3 invoices per PO |
| rfx_events | 40 | 3–6 bids each, deterministically determinable winner |
| policy_docs | 10 | real usable markdown: approval matrix, 3-bid rule, risk thresholds… |
| news_snippets | 120 | mostly tied to red-flag suppliers (distress/recall/sanction) |
| seller_personas | 6 | negotiation counterparties with floors and concession curves |

**Determinism guarantee:** one `random.Random(seed)` threaded through everything; ids are
sequential (`SUP-0001`), dates derive from base date 2026-01-01, never `uuid4` or
`datetime.now`. Same seed ⇒ byte-identical files, verified by sha256 in `manifest.json`.

## Standalone usage

```sh
# Generate to JSONL (one file per entity + manifest.json with counts and sha256s)
jai-foundry generate --out data/seed --seed 31082

# Load into Postgres — owns exactly the `foundry.*` schema, TRUNCATE-then-insert (idempotent)
jai-foundry load --from data/seed --pg-url postgresql://jai:jai@localhost:5433/jai
```

```python
from jai_foundry import generate, load, ensure_schema

manifest = generate(seed=31082, out="data/seed")   # returns {seed, counts, sha256}
ensure_schema()                                     # idempotent CREATE SCHEMA/TABLEs
load("data/seed")                                   # uses $POSTGRES_URL by default
```

Anomaly labels make the dataset eval-ready: an invoice-audit agent can be scored against
the known `anomaly` column; an RFx-award agent against the known best bid.

## Demo

```sh
uv run python parts/foundry/demo/demo.py   # no services required
```

Prints manifest counts, two sample suppliers, and a policy-doc excerpt from a temp dir.

## Tests

```sh
uv run pytest parts/foundry -q
```

Tests cover byte-determinism (double generation, sha256 compare), anomaly rate bounds,
red-flag count, RFx winner determinability, and a Postgres load round-trip (skipped
automatically when Postgres is unavailable).
