# ADR-004: Durable execution via Postgres checkpointing, not Temporal

**Status:** Accepted · June 2026

## Context

Procurement workflows span days/weeks with human approvals in the middle (a sourcing
event waits on gate reviews). Agents driving them need two properties: kill-9
resumability and human-in-the-loop pauses. Temporal is the industry answer at production
scale (OpenAI and Replit run agent loops on it) — and it is four extra moving parts for a
single-node platform.

## Decision

Use LangGraph's Postgres checkpointer (`engine` schema) for crash-resumable state and
`interrupt()` for HITL gates (`steel-brakes` owns the approval inbox + resume). The P2 demo
literally `kill -9`s the worker mid-RFx and resumes from the checkpoint.

**Temporal is recorded as the production answer.** The engine's compile step is the seam:
a Temporal-backed runtime would be a second adapter behind the same manifest, exactly
like `miniloop` (ADR-001).

## Consequences

- Zero extra infrastructure; durability rides the existing Postgres.
- No distributed workers, no cron/retry-policy engine — out of scope until production.
