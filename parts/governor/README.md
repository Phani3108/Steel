# steel-governor — the speed governor

**System:** SAFETY · **Standalone use case:** a drop-in pre-action policy engine for any
agent stack — point it at a versioned YAML policy file and call `check()` before every
consequential action. Pure Python + pydantic + YAML: no database, no model calls, no
network. The agent can reason however it likes; the governor evaluates fixed rules and
returns an auditable `Decision`. No STEEL required: the only input shape is a
`RunContext`-like identity envelope (tenant + actor role) plus the action params.

The policy is a *file* (`policies/procurement.yaml`), versioned in git. Every `Decision`
carries the `policy_version` it was evaluated under, and one human-readable reason per
rule consulted — pass and fail — so an audit log can replay exactly why an action was
allowed, gated, or denied. Unknown actions and unknown roles are **denied by default**.

| API | What it does |
|---|---|
| `Governor(policy_path=None)` | loads + validates the policy (default `<repo>/policies/procurement.yaml`) |
| `.check(ctx, action, params)` | evaluates every rule for `action`; returns `Decision` |
| `.version` | the loaded policy's version string |
| `Decision` | `allowed: bool` · `reasons: list[str]` · `policy_version: str` · `requires_gate: str \| None` |

`requires_gate` names the HITL gate (steel-brakes) that must approve before proceeding —
`"award_approval"` for over-threshold awards, `"intake_escalation"` for over-threshold
intake approvals. Allowed-with-gate is not a denial: the action is lawful, but a human signs.

## Rules (policy version 2026.06-1)

| Action | Rules consulted |
|---|---|
| `rfx.create` | role must be in `sourcing.create_roles` |
| `rfx.award` | **mandate** (spend over the agent's cap → hard deny) · **three-bid** (`n_bids < 3` at ≥ $10k → deny) · **threshold** (over the role's ceiling → gate `award_approval`) |
| `intake.approve` | **threshold** (over the role's ceiling → gate `intake_escalation`) |
| anything else | denied — `"no policy for action"` |

Role ceilings: requester $5,000 · category_manager $50,000 · cpo $250,000.

## Usage

```python
from steel_manifest import Actor, RunContext
from steel_governor import Governor

gov = Governor()
ctx = RunContext(tenant_id="acme", actor=Actor(id="u1", role="category_manager"))

d = gov.check(ctx, "rfx.award", {"total_usd": 120_000, "n_bids": 4})
d.allowed          # True
d.requires_gate    # "award_approval" — pause for a human before executing
d.reasons          # one line per rule: mandate, three-bid, threshold
d.policy_version   # "2026.06-1"
```

## Demo

```sh
python parts/governor/demo/demo.py
```

Prints seven checks: a requester denied `rfx.create`, a category manager allowed; an
$8k/2-bid award (exempt), a $40k/2-bid award (three-bid deny), $45k/3 bids (clean pass),
$120k/4 bids (allowed behind the `award_approval` gate), and a $30k award under a $25k
mandate cap (hard deny).

## Tests

```sh
uv run pytest parts/governor -q      # no Postgres needed — the governor is pure
```
