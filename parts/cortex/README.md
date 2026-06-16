# steel-cortex — the frame everything mounts to

**System:** CHASSIS · **Standalone use case:** a permission-aware retrieval layer for any
multi-tenant dataset — point the ingest at your entities/documents, get tenant- and
role-filtered hybrid retrieval with citations and first-class refusals.

The procurement semantic layer: entities (suppliers, items, contracts, news) in typed
tables; unstructured text (contract clauses, policies, news, supplier profiles, RFx
summaries) chunked with `tenant_id` + `acl_roles` columns. **Permissions are enforced in
SQL, below the LLM** — an agent inherits the human's role via `RunContext` and cannot
exceed it. If a query only touches forbidden types, the result is a refusal, not an answer.

Retrieval = deterministic intent heuristics → entity lookups + FTS chunk search
(`plainto_tsquery` + `ts_rank`); a pgvector cosine arm fuses in via RRF when embeddings
are populated (real-key ingest only — the keyless path is deterministic FTS).

## Usage

```sh
steel-cortex ingest --from data/seed
steel-cortex ask "Tell me about supplier Rampart Engineering Inc." --role requester
steel-cortex ask "What are the terms of the contract 'X'?" --role requester   # → refusal
```

```python
from steel_cortex import Cortex
from steel_manifest import Actor, RunContext

cortex = Cortex()
ctx = RunContext(tenant_id="TEN-0001", actor=Actor(id="u1", role="category_manager"))
result = cortex.retrieve(ctx, "How many bids does the policy require?")
result.facts, result.chunks, result.citations, result.refused
```

## Demo

```sh
make demo-part-cortex   # 4 persona queries: lookups, a refusal, clause chunks, news
```
