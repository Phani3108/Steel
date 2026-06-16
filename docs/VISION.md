# STEEL — The Vision

> Founding document. Written June 2026, before the first line of code. If a design decision
> ever conflicts with this document, the conflict must be resolved consciously — in an ADR —
> not by accident.

## The car

STEEL is built the way an automotive engineer builds a car.

Each part of a car has its own function. It can be used in other vehicles. It can be pulled
out and connected to other types. Yet assembled together, the parts form a car that runs
super efficiently — like a well-oiled machine.

STEEL is something super big. But **every feature must have:**

1. **Its own name** — distinct nomenclature per part.
2. **A standalone use case** — each part is useful on its own, outside the assembled whole.
3. **Modularity** — each part can be ripped out as an MCP server / plug-and-play module and
   quickly adopted into other systems (such as JAGGAER One).
4. **A complete structure of its own** — own README, own demo, own version, own tests.

The functionality is a **tree**: systems contain parts, parts expose contracts. Strong
engineering architecture patterns hold the assembly together so the whole runs well-oiled.

Build only after critical scrutiny — solid, useful, highly appreciated. Never haphazard.

## The engineering refinement

What makes a car part swappable is not the part — it is the **standardized interface**:
the bolt pattern, the CAN bus, the OBD port. STEEL's standardized interfaces are:

| Car | STEEL |
|---|---|
| Bolt patterns / connectors | **MCP** — every domain capability is an MCP server |
| CAN bus | **A2A** — agents talk over the open agent-to-agent protocol |
| Part drawings / specs | **JSON Schema** — agent manifests, events, scorecards |
| Fuel line | **OpenAI-compatible HTTP** — all model access through one gateway |

**The rippability rule:** parts communicate ONLY through published contracts. No part
imports another part's internals — enforced in CI, not by convention. Extraction cost is
"deploy separately," never "rewrite."

## The systems

```
STEEL — the vehicle
├── POWERTRAIN  — intelligence supply   (steel-gateway · steel-manifest · steel-engine)
├── CHASSIS     — knowledge             (steel-cortex · steel-foundry)
├── DRIVETRAIN  — domain capability     (5 procurement MCP servers)
├── SAFETY      — trust                 (steel-blackbox · steel-governor · steel-dyno · steel-brakes · steel-meter)
├── NETWORK     — the fleet             (steel-registry · steel-mesh · the agents)
└── COCKPIT     — human interface       (steel-console)
```

## The standard every part must meet

A part ships when — and only when — it has:

- [ ] A name and a one-line purpose
- [ ] A README with a standalone use case
- [ ] A runnable standalone demo (`make demo-part-<name>`)
- [ ] Published contracts (schema / MCP tools / HTTP API) — no leaked internals
- [ ] Tests, and for agents: a scorecard (no scorecard → no ship)
- [ ] A version and a CHANGELOG entry

## Non-affiliation

STEEL is a personal research platform. It is not affiliated with, endorsed by, or derived
from Jaggaer, Inc. or its STEEL product. All data in this repository is synthetic; all domain
models are generic procurement concepts.
