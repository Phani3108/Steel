"""jai-cortex standalone demo: the same questions, four personas, four outcomes."""

import json
from pathlib import Path

from jai_cortex import Cortex
from jai_manifest import Actor, RunContext

SEED = Path(__file__).resolve().parents[3] / "data" / "seed"


def show(label: str, result) -> None:
    print(f"\n── {label}")
    if result.refused:
        print(f"   REFUSED: {result.refusal_reason}")
        return
    for f in result.facts[:2]:
        print(f"   fact: { {k: f[k] for k in list(f)[:6]} }")
    for h in result.chunks[:2]:
        print(f"   chunk[{h.doc_type}:{h.source_id}]: {h.text[:90]}…")
    print(f"   citations: {[f'{c.source_type}:{c.source_id}' for c in result.citations[:5]]}")


def main() -> None:
    cortex = Cortex()
    cortex.ensure_schema()
    if not cortex.is_ingested():
        print("ingesting seed…", json.dumps(cortex.ingest_seed(SEED)))

    supplier = json.loads((SEED / "suppliers.jsonl").read_text().splitlines()[0])
    contract = json.loads((SEED / "contracts.jsonl").read_text().splitlines()[0])
    tenant_s, tenant_c = supplier["tenant_id"], contract["tenant_id"]

    def ctx(role: str, tenant: str) -> RunContext:
        return RunContext(tenant_id=tenant, actor=Actor(id="demo", role=role))

    q_supplier = f"Tell me about supplier {supplier['name']}"
    q_contract = f"What are the terms of the contract '{contract['title']}'?"

    show(f"requester asks: {q_supplier!r}", cortex.retrieve(ctx("requester", tenant_s), q_supplier))
    show(f"requester asks: {q_contract!r}", cortex.retrieve(ctx("requester", tenant_c), q_contract))
    show(
        f"category_manager asks: {q_contract!r}",
        cortex.retrieve(ctx("category_manager", tenant_c), q_contract),
    )
    q_news = f"Any news or risk signals about {supplier['name']}?"
    show(f"cpo asks: {q_news!r}", cortex.retrieve(ctx("cpo", tenant_s), q_news))


if __name__ == "__main__":
    main()
