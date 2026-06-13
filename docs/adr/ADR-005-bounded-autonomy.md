# ADR-005: Bounded autonomy — the mandate, with the governor as backstop

**Status:** Accepted · June 2026

## Context

The most valuable autonomous procurement action is also the most dangerous: letting an
agent *commit money* (negotiate and close a deal). Pactum's results (3% average gain,
+35-day terms at Walmart) show the upside; the risk is an agent that, through a reasoning
error or prompt injection, agrees to a price it had no authority to agree to. "Trust the
model not to" is not a control.

## Decision

Autonomy is bounded in the **manifest**, and the bound is enforced **below the model** —
twice, defence in depth:

1. **The mandate is data, not a prompt.** `agent-negotiator`'s manifest carries a hard
   `max_spend_usd`, a target and a walkaway (as fractions of list), and a max round count.
   The negotiation loop clamps every offer to the mandate ceiling — it cannot *table* a
   number it could not honour, let alone accept one.
2. **The governor is the backstop.** Before any close is final, `jai-governor` is asked to
   bless it (reusing the award policy's mandate hard-deny). If the round logic were ever
   buggy or adversarially steered past the clamp, the governor denies the close, the event
   is audited, and the agent **walks** rather than breach. A constraint violation is
   impossible by construction, and the proof is an eval metric: suite 4 reports
   `constraint_violations`, and it is zero.

The same shape generalises: a bounded mandate in the manifest + an independent policy
check at the irreversible step is how any money-moving agent earns higher autonomy.

## Consequences

- The negotiator can be promoted toward higher autonomy because its worst case is bounded
  and *measured*, not asserted (see the eval-gated maturity ladder, `jai-dyno`).
- The walkaway is a feature, not a failure: refusing a deal that would breach the mandate
  is the correct, auditable outcome.
- Enforcement reuses existing policy (no negotiation-specific governor code) — the cap is
  one concept, checked everywhere money is committed.
