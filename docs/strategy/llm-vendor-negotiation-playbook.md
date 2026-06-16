# LLM Vendor Negotiation Playbook

> How an enterprise software company should buy model capacity in 2026. Public document —
> generic industry guidance, public sources only. (Sources researched June 2026; numbers
> are market-reported ranges, not quotes.)

## The one-sentence playbook

**Architecture is the negotiation.** A gateway-routed, multi-model platform (every call
addressed to a *model group*, never a provider) makes switching cost ~zero — and the
credible ability to move traffic is worth more than any volume argument.

## Leverage, ranked

1. **Live competitive proposals.** Run a real bake-off with published eval results
   (steel-dyno-style scorecards on your own workloads). Vendors discount hardest against a
   competitor who has already passed your evals.
2. **Routing + caching beat discounts.** Model-mix routing (fast tier for bulk work,
   reasoning tier only where it pays) plus prompt caching typically cuts spend **40–70%**
   — more than any negotiated discount. Do the engineering first; negotiate on the
   residual.
3. **Committed spend.** Market-reported ranges (mid-2026): OpenAI ~25–40% below list at
   $500K–$5M prepay; Anthropic ~10–15% at $250K–$1M, up to ~25–40% at $5M+. Commit only
   after 1–2 quarters of measured baseline usage.
4. **Hyperscaler routes.** Azure OpenAI draws down a MACC (~10–20% effective savings);
   Bedrock ties into an AWS EDP. If the company already has cloud commit, the indirect
   route often beats direct pricing — but watch for feature lag vs. first-party APIs.
5. **Walk-away tier.** Keep one open-weights deployment path (vLLM + a strong open model)
   benchmarked and documented, even if unused. It is the BATNA that keeps everyone honest.

## Contract must-haves (non-negotiables before signature)

| Clause | What to demand | Why |
|---|---|---|
| Training on your data | **Opt-in only**, contractually; covers prompts, outputs, embeddings, logs | Your customers' procurement data is the asset |
| Zero data retention | ZDR **verified across safety/abuse layers**, not just the main path | "We don't retain" often excludes trust-and-safety storage |
| Deprecation | **90–180 days notice** + continued access to the legacy model for migration | Model retirements break tuned prompts and evals |
| No-regression | Right to re-run your eval baseline on replacement models; exit or credit if it regresses | Capability is what you bought |
| Rate limits | Contractual RPM/TPM floors with burst terms, not "fair use" | Agents fail loudly at rate-limit cliffs |
| Price protection | Cap on per-token increases during the term; pass-through of list-price cuts | List prices have only fallen — capture that |
| Audit rights | Usage/billing data export at line-item granularity | Reconcile against your own meter (steel-meter pattern) |
| Output IP | Full assignment of output rights to you/your customers | Table stakes, but verify for fine-tuned variants |
| Liability/indemnity | IP indemnity for outputs; clarity on AI-Act-relevant obligations | EU AI Act transparency duties apply from Aug 2026 |

## Pricing-model selection (what to *sell*, informed by what you buy)

The market hasn't settled: one vendor bundles agents free (platform-defense pricing), one
meters per agent step at 3–8× copilot rates, one prices on outcomes. The only safe
position is **instrument first**: meter every agent action (tenant / agent / run / task)
from day one so any of free-bundle, metered, seat, or outcome pricing is a SQL query away
— never a re-architecture.

## Cadence

- **Quarterly:** re-run the eval bake-off on your top 5 workloads; rebalance routing.
- **Renewal minus 6 months:** open parallel conversations with ≥2 alternates; refresh the
  BATNA benchmark.
- **Always:** keep per-workload cost/quality scorecards — the negotiation deck writes itself.
