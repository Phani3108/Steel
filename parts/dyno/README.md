# steel-dyno — the test bench

**SYSTEM: SAFETY** · eval harness + scorecards + autonomy promotion gates.
An agent ships only with a passing scorecard.

## What it does

- **Suites** (`suite.py`) — declarative eval suites in YAML: cases with an input, an
  expected value, and a grader (`exact`, `contains`, or `llm_judge` with a rubric).
- **Graders** (`graders.py`) — `grade_exact`, `grade_contains`, and `grade_llm_judge`,
  which asks the gateway's `fast` model group for a one-line `PASS:`/`FAIL:` verdict
  (keyless in mock mode via LiteLLM's `mock_response`).
- **Harness** (`harness.py`) — `run_suite(suite, target, ...)` runs any callable
  `str -> str` through a suite and produces a `Scorecard`. A crashing target is a failed
  case, never a crashed run.
- **Promotion gate** (`scorecard.py`) — `promotion_gate(manifest, scorecard)` promotes an
  agent exactly one autonomy level, only if `pass_rate >= metrics.eval_pass_rate` and
  `policy_violations <= metrics.max_policy_violations` — and never above L4
  automatically: the jump to L5 is a human decision.

## Standalone use case

You don't need STEEL to use the bench. Any team with a chatbot, an RAG pipeline, or a
classifier behind a `str -> str` callable can write a YAML suite, run it in CI, and gate
deploys on the scorecard's `pass_rate` — no manifests, no gateway, no database. The
gateway is only needed if you want LLM-judged rubric cases; the promotion gate is only
needed if you adopt `steel_manifest` autonomy levels.

```python
from steel_dyno import load_suite, run_suite

suite = load_suite("evals/suite0_smoke/smoke.yaml")
scorecard = run_suite(suite, my_bot.answer, agent_name="my-bot")
assert scorecard.pass_rate >= 0.9, scorecard.failures
```

## Suite format

```yaml
name: suite0_smoke
description: what this suite proves
cases:
  - id: exact-roundtrip
    input: "hello procurement"
    expected: "hello procurement"
    grader: exact            # exact | contains | llm_judge
  - id: judged-tone
    input: "draft a polite escalation"
    grader: llm_judge
    judge_rubric: "Output is polite and under 100 words."
```

## Promotion gate

```python
from steel_manifest import load_manifest
from steel_dyno import promotion_gate

decision = promotion_gate(load_manifest("agents/scout.yaml"), scorecard)
if decision.promote:
    print(f"earned {decision.to_level.name}")   # one level up, capped at L4
```

## CLI

```bash
steel-dyno run evals/suite0_smoke/smoke.yaml --target echo
# prints the scorecard as JSON; exit 1 only if pass_rate < 0.5 (smoke threshold)
```

## Demo

```bash
python parts/dyno/demo/demo.py    # no services required
```

Runs the smoke suite against the echo target, then shows the promotion gate promoting an
L1 manifest and capping an L4 one.

## Tests

```bash
uv run pytest parts/dyno -q       # no docker, no network — the gateway is faked
```
