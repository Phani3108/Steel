# steel-gateway — the fuel system

**System:** POWERTRAIN · **Standalone use case:** a typed Python client for any
LiteLLM proxy — model-group routing, pre-dispatch budget gates, per-call metering tags,
and a keyless mock mode for CI. Point it at your own LiteLLM deployment and you get the
same cost-control surface with zero STEEL coupling beyond the `RunContext` envelope.

Every model call in the platform flows through this client, and every call gets:

| Guarantee | How |
|---|---|
| **Routing by group** | Callers ask for `"reasoning"`, `"reasoning-max"`, `"fast"`, or `"embed"` — never a provider model id. Swapping providers is a proxy-config edit, not a code change |
| **Budgets** | If `ctx.budget_usd_remaining` is exhausted, `BudgetExceededError` is raised BEFORE dispatch — no spend, no call |
| **Metering tags** | `ctx.metadata_tags()` (tenant, actor, agent, run, trace) travel to LiteLLM on every call for cost attribution |
| **Keyless mock mode** | `STEEL_MOCK=1` (the default) sends LiteLLM's `mock_response` so the whole platform runs with no provider keys; cost is 0.0 by definition |
| **Real cost per call** | Live calls read the `x-litellm-response-cost` header into `GatewayResponse.cost_usd` |

## Standalone usage

```python
from steel_gateway import BudgetExceededError, GatewayClient
from steel_manifest import RunContext

ctx = RunContext(
    tenant_id="acme",
    actor={"id": "u1", "role": "category_manager"},
    budget_usd_remaining=0.50,
)
client = GatewayClient()  # env: LITELLM_BASE_URL, LITELLM_MASTER_KEY, STEEL_MOCK

resp = client.complete(
    ctx,
    group="reasoning",
    messages=[{"role": "user", "content": "Summarize this supplier's risk profile."}],
)
print(resp.text, resp.model, resp.cost_usd)

vectors = client.embed(ctx, texts=["supplier risk"])  # mock mode: deterministic dim-8
```

Provision a per-(tenant, agent) virtual key with its own hard budget — enforced by the
proxy itself (requires LiteLLM running with a database; demo-only, never used by tests):

```python
from steel_gateway import provision_virtual_key

key = provision_virtual_key("acme", "agent-sourcing", max_budget_usd=5.00)
```

## Environment

| Var | Default | Meaning |
|---|---|---|
| `LITELLM_BASE_URL` | `http://localhost:4000` | The proxy endpoint |
| `LITELLM_MASTER_KEY` | `sk-steel-master-dev` | Auth against the proxy |
| `STEEL_MOCK` | `1` | Keyless mock mode; set `0` for live provider calls |

## Demo

```sh
docker compose up -d --wait          # postgres + LiteLLM proxy, no provider keys needed
python parts/gateway/demo/demo.py    # mock completion + tags + cost + budget refusal
```

## Tests

```sh
uv run pytest parts/gateway -q       # zero network — the openai client object is faked
```
