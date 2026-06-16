# ADR-001: Bet on protocols, hedge on frameworks

**Status:** Accepted · June 2026

## Context

The agent-framework layer is still churning (LangGraph, Microsoft Agent Framework, OpenAI
Agents SDK, Claude Agent SDK all shipped major versions within 12 months), while the
protocol layer has settled: MCP for tool integration, A2A (Linux Foundation) for
agent-to-agent interop, OpenAI-compatible HTTP as the de-facto model interface.
Princeton's HAL showed scaffold choice alone moves benchmark scores by up to 30 points —
the framework matters, and will keep being replaced.

## Decision

Agent definitions live in a framework-agnostic **Agent Manifest** (`steel-manifest`,
pydantic → JSON Schema). Only `steel-engine` imports an orchestration framework
(LangGraph 1.x today). Tools are referenced as MCP server/tool names, never Python
imports. Prompts are versioned files, never inline strings. Evals (`steel-dyno`) run
against manifests, not framework objects.

Portability is **proven, not asserted**: P4 ships a ~150-line plain-loop second runtime
(`miniloop`) that executes the same manifest and passes the same eval suites.

## Consequences

- Swapping the orchestrator is an engine change, invisible to every other part.
- The manifest schema is a public contract — versioned, exported to `schemas/`.
- Slight indirection cost in the engine (compile step) — accepted.
