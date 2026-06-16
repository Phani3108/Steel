/**
 * THE REFERENCE FLEET — the built-in, offline-safe picture of the STEEL vehicle.
 *
 * Two jobs:
 *  1. Graceful fallback. When GET /registry or /network 404 / 503 (those endpoints
 *     are being built in parallel), the catalog & fleet pages render THIS instead of
 *     a blank screen, with a quiet "live telemetry offline" note.
 *  2. Canonical catalog. Even when the API is up, this is the human-authored map of
 *     six systems → ~21 parts that the cockpit is organized around.
 *
 * Mirrors docs/VISION.md. Shapes intentionally match the API contract so a page can
 * swap `REFERENCE_FLEET` ↔ `fetchRegistry()` results with no other change.
 */

import type { System, Status } from "./theme";

export type Pipeline = "direct" | "rag" | "sourcing" | "orchestrate";

/** A part of the vehicle. Agents additionally carry autonomy/pipeline/skills. */
export interface FleetPart {
  /** Stable id used as the network node id and registry key. */
  name: string;
  system: System;
  /** One-line purpose. */
  purpose: string;
  status: Status;
  /** True for the NETWORK agents (vs. infrastructure parts/MCP servers). */
  isAgent?: boolean;
  autonomy_level?: 1 | 2 | 3 | 4 | 5;
  pipeline?: Pipeline;
  skills?: string[];
  /** Spend mandate ceiling, where one applies. */
  mandate_usd?: number | null;
}

export interface FleetSystem {
  system: System;
  tagline: string;
  parts: FleetPart[];
}

// --------------------------------------------------------------- the parts ----

export const REFERENCE_FLEET: FleetSystem[] = [
  {
    system: "POWERTRAIN",
    tagline: "intelligence supply",
    parts: [
      {
        name: "steel-gateway",
        system: "POWERTRAIN",
        purpose:
          "One fuel line — LiteLLM model access with budgets, tags, and mock mode.",
        status: "active",
      },
      {
        name: "steel-manifest",
        system: "POWERTRAIN",
        purpose:
          "The part drawings — agent specs, RunContext, and the audit-event contract.",
        status: "active",
      },
      {
        name: "steel-engine",
        system: "POWERTRAIN",
        purpose: "Compiles manifests into runnable agents and pipelines.",
        status: "active",
      },
    ],
  },
  {
    system: "CHASSIS",
    tagline: "knowledge",
    parts: [
      {
        name: "steel-cortex",
        system: "CHASSIS",
        purpose: "Retrieval memory and the semantic layer over the procurement world.",
        status: "active",
      },
      {
        name: "steel-foundry",
        system: "CHASSIS",
        purpose: "Seeded synthetic world — suppliers, POs, invoices, RFx, news.",
        status: "active",
      },
    ],
  },
  {
    system: "DRIVETRAIN",
    tagline: "domain capability",
    parts: [
      {
        name: "mcp-supplier-master",
        system: "DRIVETRAIN",
        purpose: "Supplier master MCP server — profiles, risk, certifications.",
        status: "active",
      },
      {
        name: "mcp-sourcing-events",
        system: "DRIVETRAIN",
        purpose: "Sourcing / RFx MCP server — create events, collect & rank bids.",
        status: "active",
      },
      {
        name: "mcp-contracts",
        system: "DRIVETRAIN",
        purpose: "Contracts MCP server — terms, expiries, obligations.",
        status: "active",
      },
      {
        name: "mcp-spend-analytics",
        system: "DRIVETRAIN",
        purpose: "Spend analytics MCP server — category rollups, tail spend, leakage.",
        status: "active",
      },
      {
        name: "mcp-intake",
        system: "DRIVETRAIN",
        purpose: "Intake MCP server — requests, triage routing, intake forms.",
        status: "active",
      },
    ],
  },
  {
    system: "SAFETY",
    tagline: "trust",
    parts: [
      {
        name: "steel-blackbox",
        system: "SAFETY",
        purpose: "Tamper-evident, hash-chained audit trail for every action.",
        status: "active",
      },
      {
        name: "steel-governor",
        system: "SAFETY",
        purpose: "Policy enforcement before actions — RBAC, mandates, scopes.",
        status: "active",
      },
      {
        name: "steel-dyno",
        system: "SAFETY",
        purpose: "Eval harness and scorecards — no scorecard, no ship.",
        status: "active",
      },
      {
        name: "steel-brakes",
        system: "SAFETY",
        purpose: "Human-in-the-loop approval gates that pause runs durably.",
        status: "active",
      },
      {
        name: "steel-meter",
        system: "SAFETY",
        purpose: "Cost ledger — who spent what, on which run and model.",
        status: "active",
      },
    ],
  },
  {
    system: "NETWORK",
    tagline: "the fleet",
    parts: [
      {
        name: "steel-registry",
        system: "NETWORK",
        purpose: "Catalog of agents, their autonomy levels, mandates, and scorecards.",
        status: "active",
      },
      {
        name: "steel-mesh",
        system: "NETWORK",
        purpose: "A2A — agents talking over the open agent-to-agent protocol.",
        status: "active",
      },
      {
        name: "agent-supplier-intel",
        system: "NETWORK",
        purpose:
          "Answers supplier questions with cited retrieval over the knowledge base.",
        status: "active",
        isAgent: true,
        autonomy_level: 2,
        pipeline: "rag",
        skills: ["supplier.lookup", "supplier.risk", "qa.cited"],
        mandate_usd: null,
      },
      {
        name: "agent-sourcing",
        system: "NETWORK",
        purpose:
          "Runs a sourcing event end-to-end — draft RFx, collect bids, rank, recommend.",
        status: "active",
        isAgent: true,
        autonomy_level: 3,
        pipeline: "sourcing",
        skills: ["rfx.draft", "bid.collect", "bid.rank", "award.recommend"],
        mandate_usd: 250_000,
      },
      {
        name: "agent-orchestrator",
        system: "NETWORK",
        purpose:
          "Routes an intake to the right specialists and composes their results.",
        status: "active",
        isAgent: true,
        autonomy_level: 3,
        pipeline: "orchestrate",
        skills: ["intent.route", "plan.compose", "handoff.a2a"],
        mandate_usd: 500_000,
      },
      {
        name: "agent-intake-triage",
        system: "NETWORK",
        purpose: "Classifies an incoming request and enriches it for routing.",
        status: "active",
        isAgent: true,
        autonomy_level: 2,
        pipeline: "direct",
        skills: ["intake.classify", "intake.enrich"],
        mandate_usd: null,
      },
      {
        name: "agent-risk-sentinel",
        system: "NETWORK",
        purpose: "Screens suppliers and deals for risk flags before they proceed.",
        status: "active",
        isAgent: true,
        autonomy_level: 2,
        pipeline: "rag",
        skills: ["risk.screen", "sanctions.check", "concentration.flag"],
        mandate_usd: null,
      },
      {
        name: "agent-spend-analyst",
        system: "NETWORK",
        purpose: "Analyzes spend by category and surfaces savings opportunities.",
        status: "active",
        isAgent: true,
        autonomy_level: 2,
        pipeline: "rag",
        skills: ["spend.rollup", "savings.identify", "tail.analyze"],
        mandate_usd: null,
      },
    ],
  },
  {
    system: "COCKPIT",
    tagline: "human interface",
    parts: [
      {
        name: "steel-console",
        system: "COCKPIT",
        purpose: "This app — mission control for the whole fleet.",
        status: "active",
      },
    ],
  },
];

/** Flat list of every part across all systems. */
export const REFERENCE_PARTS: FleetPart[] = REFERENCE_FLEET.flatMap((s) => s.parts);

/** Just the agents (NETWORK parts flagged isAgent) — the fleet proper. */
export const REFERENCE_AGENTS: FleetPart[] = REFERENCE_PARTS.filter((p) => p.isAgent);

/** Total parts across the vehicle (for the telemetry strip system/part counts). */
export const REFERENCE_PART_COUNT = REFERENCE_PARTS.length;

// ------------------------------------------------------------ the topology ----

export interface NetworkNode {
  id: string;
  label: string;
  system: System;
  /** human | agent | service — drives node shape in the fleet graph. */
  role: "human" | "agent" | "service";
}

export interface NetworkEdge {
  source: string;
  target: string;
  label?: string;
}

export interface NetworkTopology {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

/**
 * Reference topology (matches the /network shape):
 *   human → agent-orchestrator → { intake-triage, risk-sentinel, spend-analyst, agent-sourcing }
 *   agent-sourcing → mcp-sourcing-events
 *   agent-supplier-intel → steel-cortex
 */
export const REFERENCE_NETWORK: NetworkTopology = {
  nodes: [
    { id: "human", label: "Operator", system: "COCKPIT", role: "human" },
    {
      id: "agent-orchestrator",
      label: "Orchestrator",
      system: "NETWORK",
      role: "agent",
    },
    {
      id: "agent-intake-triage",
      label: "Intake Triage",
      system: "NETWORK",
      role: "agent",
    },
    {
      id: "agent-risk-sentinel",
      label: "Risk Sentinel",
      system: "NETWORK",
      role: "agent",
    },
    {
      id: "agent-spend-analyst",
      label: "Spend Analyst",
      system: "NETWORK",
      role: "agent",
    },
    { id: "agent-sourcing", label: "Sourcing", system: "NETWORK", role: "agent" },
    {
      id: "agent-supplier-intel",
      label: "Supplier Intel",
      system: "NETWORK",
      role: "agent",
    },
    {
      id: "mcp-sourcing-events",
      label: "Sourcing Events",
      system: "DRIVETRAIN",
      role: "service",
    },
    { id: "steel-cortex", label: "Cortex", system: "CHASSIS", role: "service" },
  ],
  edges: [
    { source: "human", target: "agent-orchestrator", label: "intake" },
    { source: "agent-orchestrator", target: "agent-intake-triage", label: "triage" },
    { source: "agent-orchestrator", target: "agent-risk-sentinel", label: "screen" },
    { source: "agent-orchestrator", target: "agent-spend-analyst", label: "analyze" },
    { source: "agent-orchestrator", target: "agent-sourcing", label: "source" },
    {
      source: "agent-sourcing",
      target: "mcp-sourcing-events",
      label: "rfx",
    },
    { source: "agent-supplier-intel", target: "steel-cortex", label: "retrieve" },
  ],
};
