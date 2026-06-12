# jai-mcp — the drivetrain

**System:** DRIVETRAIN · **Standalone use case:** five procurement tool servers any
MCP-speaking client (Claude Desktop, an agent runtime, JAGGAER One, a script) can plug
into — point one at a Postgres with supplier/contract/PO data and you have a working
supplier master, RFx engine, contract search, spend cube, and intake desk. Mock-backed
today, hexagonal by design: the tool contracts are the stable surface; the SQL behind
them is swappable for any real S2P system's REST APIs without touching a single client.

Every server has two faces:

1. **Plain typed functions** (`jai_mcp.<module>.TOOLS`) — the in-process API other parts
   get injected with (jai-engine consumes this seam via `in_process_tools()`).
2. **A FastMCP server object** (`jai_mcp.<module>.server`) — the same functions
   registered as MCP tools, servable over streamable HTTP.

Identity travels explicitly: every tool takes `tenant_id` and `role` parameters.
An HTTP deployment fills both from auth middleware (TODO at P3 — no real JWT at P2).

| Server | Tools | Role gate | Data |
|---|---|---|---|
| `supplier-master` | `search_suppliers` `get_supplier` | all roles | cortex.suppliers (read) |
| `sourcing-events` | `create_event` `invite_suppliers` `open_bidding` `submit_bid` `list_bids` `score_bids` `award` `get_event` | category_manager+ to manage | own schema `sourcing` |
| `contracts` | `search_contracts` | category_manager+ | cortex.contracts + chunk FTS (read) |
| `spend-analytics` | `spend_cube` `price_benchmark` | category_manager+ | foundry.purchase_orders/items/suppliers (read) |
| `intake` | `submit_request` `list_requests` `get_request` | all roles | own schema `intake` |

`sourcing-events` enforces a strict lifecycle — `draft → invited → bidding → scored →
awarded` — wrong-state calls and forbidden roles return `{"error": "..."}`, never raise.
`score_bids` ranks by normalized price + lead time (`price_weight`, default 0.7).
`intake` triages inline against the canonical requester threshold: ≤ $5,000 →
`auto_approved`, above → `sourcing_required`.

Own schema namespaces (ADR-003): `sourcing`, `intake`. Everything else is read-only over
cortex/foundry published table contracts.

## Usage

```python
from jai_mcp import SERVERS, in_process_tools

sourcing = in_process_tools("sourcing-events")
event = sourcing["create_event"](
    "TEN-0001", "category_manager", "FY26 bearings", "Bearings & Bushings",
    [{"sku": "BRG-00001", "qty": 500}], created_by="cm-1",
)
SERVERS["sourcing-events"]   # the same tools as a FastMCP object
```

Or over the wire:

```sh
uv run jai-mcp serve supplier-master --port 8101   # streamable HTTP at /mcp
uv run jai-mcp tools sourcing-events               # print a server's tool names
```

## Demo

```sh
docker compose up -d postgres        # from the repo root, with cortex/foundry seeded
make demo-part-mcp                   # or: uv run python parts/mcp/demo/demo.py
```

Runs a full sourcing lifecycle in-process — find 3 suppliers → create → invite → bid ×3
→ score → award — then prints the top-5 spend categories and an intake
auto-approve/escalation pair.

## Tests

```sh
uv run pytest parts/mcp -q           # skip cleanly if Postgres is not reachable
```

State machine + role gates, deterministic scoring math, the $5,000 triage edge,
spend-cube aggregation, and tool-registry parity between both faces of every server.
