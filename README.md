# JAI — A Modular Agentic Platform for Procurement

> Built like a car: every part has its own name, a standalone use case, and a complete
> structure of its own — and each can be ripped out and plugged into another system over
> open protocols (MCP, A2A). Assembled together, they form an autonomous procurement
> network that runs like a well-oiled machine.
>
> **Read the founding [VISION](docs/VISION.md).**

*Not affiliated with Jaggaer, Inc. or its JAI product. All data is synthetic
([Borealis Manufacturing](docs/adr/ADR-003-single-postgres.md) is a fictional company);
all domain models are generic.*

## The Parts Catalog

```
JAI — the vehicle
│
├── 1. POWERTRAIN — intelligence supply
│   ├── jai-gateway      · multi-model LLM router: model groups, fallbacks, per-(tenant, agent)
│   │                      virtual keys & budgets                       parts/gateway
│   ├── jai-manifest     · declarative agent spec + validator — the "part drawing" every
│   │                      agent follows (autonomy L1–L5, tools, HITL gates)  parts/manifest
│   └── jai-engine       · manifest→runtime compiler (LangGraph today, swappable tomorrow —
│                          proven by a second runtime)                  parts/engine
│
├── 2. CHASSIS — knowledge
│   ├── jai-cortex       · permission-aware procurement semantic layer + hybrid retrieval
│   └── jai-foundry      · deterministic synthetic-data factory          parts/foundry
│
├── 3. DRIVETRAIN — domain capability (the plug-and-play layer)
│   └── 5 MCP servers: supplier-master · sourcing-events · contracts · spend-analytics · intake
│       (mock-backed now; hexagonal adapters swap to any real S2P system's REST APIs)
│
├── 4. SAFETY — trust (the moat-grade system)
│   ├── jai-blackbox     · hash-chained tamper-evident audit chain       parts/blackbox
│   ├── jai-governor     · policy engine: permission inheritance, spend mandates
│   ├── jai-dyno         · eval harness, scorecards, autonomy promotion gates  parts/dyno
│   ├── jai-brakes       · HITL approval gates + kill switches
│   └── jai-meter        · per-action cost ledger                        parts/meter
│
├── 5. NETWORK — the fleet
│   ├── jai-registry     · agent cards, status, autonomy levels, scorecards
│   ├── jai-mesh         · A2A interop + context propagation
│   └── agents/          · supplier-intel · sourcing · risk-sentinel · spend-analyst · negotiator
│
└── 6. COCKPIT — human interface
    └── jai-console      · chat, run timeline, approvals inbox, cost dashboard, registry
```

Every part ships with its own README, standalone demo, version, and tests. Parts
communicate only through published contracts — enforced by import-linter in CI.

## The fleet, assembled

Five agents, each defined by a framework-free manifest and compiled to a runtime:

| Agent | Pipeline | What it does |
|---|---|---|
| `agent-supplier-intel` | rag | Cited Q&A over suppliers/contracts/policies/news, permission-scoped to the asker's role |
| `agent-sourcing` | sourcing | Runs an RFx end to end — durable, gated, governed — and survives `kill -9` |
| `agent-orchestrator` | orchestrate | One intake → triage → risk ∥ spend specialists → sourcing, all under one trace |
| `agent-negotiator` | negotiate | Multi-round supplier negotiation inside a hard mandate — walks rather than breach it |
| three specialists | — | intake-triage, risk-sentinel, spend-analyst, dispatched over the A2A mesh |

## Quickstart

```sh
cp .env.example .env        # leave JAI_MOCK=1 for fully keyless mode (no API spend)
make up                     # postgres + pgvector + LiteLLM gateway (docker compose)
make seed                   # generate + load the Borealis Manufacturing dataset

make smoke                  # Demo 0: an agent runs from a manifest through the gateway
make demo-p1                # supplier intelligence — one agent, four personas, refusals
make demo-p2                # autonomous sourcing — gates, kill -9 resume, kill switch
make demo-p3                # the orchestrated fleet — one intake, one trace, one chain
make demo-p4                # autonomous negotiation under a bounded mandate

make evals                  # all four eval suites (keyless, deterministic)
make portability            # prove the manifest is the contract: suite 1 on a 2nd runtime
make maturity               # the eval-gated autonomy promotion ladder
make api & make console     # the control plane (:8400) + the cockpit console (:3000)
```

Runs fully keyless: with `JAI_MOCK=1` every model call is served by the gateway's mock
path, so the whole platform — audit chain, ledger, manifests, evals, the nine-screen
console — is testable with zero API spend.

## Proof, not promises

Anti-agent-washing is the thesis: no agent ships without a scorecard.

| What | Result |
|---|---|
| Unit tests across every part | **184 passing** |
| Eval suite 1 — supplier intel (goldens + permission + injection) | **80 / 80** |
| Eval suite 2 — autonomous sourcing scenarios | **12 / 12** |
| Eval suite 3 — orchestration (routing, handoff, permission) | **12 / 12** |
| Eval suite 4 — negotiation, with **constraint violations** | **12 / 12 · 0 violations** |
| Portability — supplier-intel on a second runtime (no LangGraph) | **80 / 80** |
| Part-boundary contracts (import-linter) | **3 / 3 kept** |

The portability run is the architectural bet made good: the same agent manifest runs on
the LangGraph runtime and a ~120-line plain-Python runtime and passes the identical evals
— **the framework is a swappable detail; the manifest is the contract** ([ADR-001](docs/adr/ADR-001-protocols-over-frameworks.md)).

## The cockpit

`make console` opens a nine-screen mission-control UI: an exploded-vehicle parts catalog,
a live A2A fleet graph, a mission launcher (watch an orchestration fan out), a negotiation
theatre (watch the negotiator hold its mandate line), telemetry diagnostics, a
flight-recorder audit trail, an agent studio (form → schema-valid manifest), and a
governance view (the eval-gated maturity ladder + an EU AI Act Art. 50 disclosure).

## Why this exists

Procurement is drowning in agent demos and starving for **governed autonomy**. The scarce
assets are measurable outcomes per agent and trust infrastructure — permission inheritance,
tamper-evident audit, eval-gated autonomy promotion, bounded mandates, cost-per-task
accounting. JAI builds those as first-class parts, then assembles agents on top of them.

Strategy docs: [docs/strategy/](docs/strategy/) · Architecture decisions: [docs/adr/](docs/adr/)

## License

Apache-2.0 — see [LICENSE](LICENSE).
