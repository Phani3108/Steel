# ADR-002: Modular monolith with contract-enforced part boundaries

**Status:** Accepted · June 2026

## Context

The vision requires every part to be rippable — usable standalone, extractable as an MCP
server or service. The naive reading (one service per part) would mean ~20 deployables,
interface versioning, and distributed-systems tax that a small team cannot pay and a demo
platform does not need. A car is the right metaphor: modular at system interfaces,
tightly integrated within the assembly.

## Decision

One repository, one `docker compose up`, one uv workspace — but every part is:

1. its own Python package (`parts/<name>` → `steel_<name>`) with its own README, demo,
   version, and tests;
2. boundary-enforced in CI via import-linter: parts may import `steel_manifest` (the
   contract layer) and their own internals; cross-part calls go through published client
   interfaces, HTTP, MCP, or A2A — never another part's `_internal`;
3. independently runnable (`make demo-part-<name>`).

Extraction cost is therefore "deploy separately", never "rewrite".

## Consequences

- CI fails on any boundary violation — rippability is a build guarantee, not a hope.
- Some duplication (per-part pyproject/README) — accepted as the cost of the catalog.
