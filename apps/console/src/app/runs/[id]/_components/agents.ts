/**
 * Run-detail agent helpers — resolve an agent *name* (as it appears in a run's
 * events / cost rows / summary, e.g. "agent-orchestrator") into the metadata the
 * single-run view needs: its car system (for the system hue + SystemBadge) and a
 * short human label (for the replay glyph). Pure, offline-safe — keyed off the
 * built-in reference fleet so it works even with the control plane down.
 */

import type { FleetPart, NetworkNode } from "@/lib/fleet";
import { REFERENCE_NETWORK, REFERENCE_PARTS } from "@/lib/fleet";
import type { System } from "@/lib/theme";

const PART_BY_NAME: Map<string, FleetPart> = new Map(
  REFERENCE_PARTS.map((p) => [p.name, p]),
);

const NODE_BY_ID: Map<string, NetworkNode> = new Map(
  REFERENCE_NETWORK.nodes.map((n) => [n.id, n]),
);

export interface AgentMeta {
  /** Canonical id/name as it appears in the run record. */
  id: string;
  /** Short, title-cased display label (e.g. "Orchestrator"). */
  label: string;
  /** The car system this agent/part belongs to (drives the hue). */
  system: System;
  /** Node role — human | agent | service — drives the replay glyph shape. */
  role: "human" | "agent" | "service";
}

/** Title-case an agent id into a compact label: agent-risk-sentinel → Risk Sentinel. */
function labelFromId(id: string): string {
  const cleaned = id
    .replace(/^agent-/, "")
    .replace(/^mcp-/, "")
    .replace(/^steel-/, "");
  return cleaned
    .split(/[-_]/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Best-effort system guess for an unknown name — agents live on the NETWORK. */
function guessSystem(id: string): System {
  if (id === "human" || id === "operator") return "COCKPIT";
  if (id.startsWith("mcp-")) return "DRIVETRAIN";
  if (id.startsWith("agent-")) return "NETWORK";
  return "NETWORK";
}

function guessRole(id: string): AgentMeta["role"] {
  if (id === "human" || id === "operator") return "human";
  if (id.startsWith("mcp-") || id.startsWith("steel-")) return "service";
  return "agent";
}

/**
 * Resolve one agent name to its display metadata, preferring the reference fleet
 * (system + label) and falling back to a derived guess so an agent the catalog
 * has never heard of still renders sensibly.
 */
export function resolveAgent(id: string): AgentMeta {
  const node = NODE_BY_ID.get(id);
  const part = PART_BY_NAME.get(id);
  const system = node?.system ?? part?.system ?? guessSystem(id);
  const role = node?.role ?? guessRole(id);
  const label = node?.label ?? labelFromId(id);
  return { id, label, system, role };
}
