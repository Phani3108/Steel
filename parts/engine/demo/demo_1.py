"""Demo 1 — supplier intelligence: one agent, four personas, permission-aware answers.

Requires docker compose (postgres + the mock gateway); no API keys. The demo wires
jai-cortex into the engine as the injected retriever — an import that is allowed HERE
(the demo is assembler-tier glue) but forbidden inside jai_engine itself.
"""

import json
from pathlib import Path

from jai_blackbox import BlackBox
from jai_cortex import Cortex  # assembler-tier import: demos wire parts together
from jai_engine.compile import compile_manifest
from jai_gateway import GatewayClient
from jai_manifest import Actor, RunContext, load_manifest
from jai_meter import Meter

ROOT = Path(__file__).resolve().parents[3]
AGENT_DIR = ROOT / "parts" / "agents" / "supplier_intel"


def main() -> None:
    blackbox = BlackBox()
    blackbox.ensure_schema()
    meter = Meter()
    meter.ensure_schema()
    cortex = Cortex()
    cortex.ensure_schema()
    if not cortex.is_ingested():
        print("ingesting seed…", json.dumps(cortex.ingest_seed(ROOT / "data" / "seed")))

    agent = compile_manifest(
        load_manifest(AGENT_DIR / "manifest.yaml"),
        gateway=GatewayClient(),
        blackbox=blackbox,
        meter=meter,
        prompt_base=AGENT_DIR,
        retriever=cortex.retrieve,
    )

    seed = ROOT / "data" / "seed"
    supplier = json.loads((seed / "suppliers.jsonl").read_text().splitlines()[0])
    contract = json.loads((seed / "contracts.jsonl").read_text().splitlines()[0])

    queries = [
        ("requester", supplier["tenant_id"], f"Tell me about supplier {supplier['name']}"),
        ("requester", contract["tenant_id"],
         f"What are the terms of the contract '{contract['title']}'?"),
        ("category_manager", contract["tenant_id"],
         f"What are the terms of the contract '{contract['title']}'?"),
        ("cpo", supplier["tenant_id"], f"Any news or risk signals about {supplier['name']}?"),
    ]

    last_run = ""
    for role, tenant, query in queries:
        ctx = RunContext(tenant_id=tenant, actor=Actor(id="demo", role=role))
        result = agent.run(ctx, query)
        last_run = result.run_id
        print(f"\n── {role} asks: {query!r}")
        print("   " + result.text.replace("\n", "\n   ")[:600])
        if result.citations:
            cites = [f"{c['source_type']}:{c['source_id']}" for c in result.citations[:5]]
            print(f"   citations: {cites}")
        print(f"   refused={result.refused}  cost=${result.cost_usd:.4f}  run={result.run_id}")

    print("\n── audit tail (last run)")
    for row in blackbox.tail(n=6, run_id=last_run):
        print(f"   {row['action']:<12} {row['outcome']:<8} hash={row['hash'][:12]}…")
    verdict = blackbox.verify()
    print(f"\nblackbox verify: ok={verdict.ok} checked={verdict.checked}")
    agent.close()


if __name__ == "__main__":
    main()
