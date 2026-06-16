# steel-manifest — the part drawing

**System:** POWERTRAIN · **Standalone use case:** a framework-free standard for defining
AI agents — adopt the schema in any stack, validate in CI, compile to any runtime.

Defines the three contracts every other STEEL part builds on:

| Contract | What it is |
|---|---|
| `AgentManifest` | Complete declarative agent definition: identity, autonomy level (L1–L5), model policy (gateway group + budget), versioned prompt ref, MCP tool refs, guardrails, HITL gates, bounded mandate, scorecard targets |
| `RunContext` | The identity/budget envelope that travels with every action: tenant, actor (+role), run/trace ids. Agents inherit the human's permissions through it |
| `AuditEvent` | The audit-trail envelope (identity, authz context, policy version, action, outcome) that steel-blackbox chains and tamper-proofs |

This package imports **no other part** — it is the bottom of the dependency tree
(enforced by import-linter in CI).

## Standalone usage

```sh
# Validate any manifest in CI
steel-manifest validate parts/agents/echo/manifest.yaml

# Export the JSON Schemas (the public contract; TS types are generated from these)
steel-manifest export-schemas --out schemas/
```

```python
from steel_manifest import AgentManifest, RunContext, load_manifest

manifest = load_manifest("manifest.yaml")
ctx = RunContext(tenant_id="t1", actor={"id": "u1", "role": "category_manager"})
```

## Demo

```sh
make demo-part-manifest   # validates the example manifest and prints its schema
```
