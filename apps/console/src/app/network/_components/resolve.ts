/**
 * Joins the three data sources the Fleet page reads — the network topology
 * (nodes/edges), the registry (per-agent AgentRecord), and the reference fleet
 * (purposes + offline fallback) — into a single inspectable `NodeView`.
 *
 * Pure functions only; the page handles fetching/polling and passes results in.
 */

import type { AgentRecord, NetworkNode, RunSummary } from "@/lib/api";
import type { FleetPart } from "@/lib/fleet";
import { REFERENCE_PARTS } from "@/lib/fleet";

export interface NodeView extends NetworkNode {
  /** Full registry record when this node is a known agent; null otherwise. */
  record: AgentRecord | null;
  /** Human-readable purpose (from registry description or the fleet catalog). */
  description: string;
  /** Recent runs this agent appears in — deep-links into /runs/{id}. */
  runs: RunSummary[];
}

/** Index the reference catalog by part name for O(1) purpose lookup. */
const PART_BY_NAME: Map<string, FleetPart> = new Map(
  REFERENCE_PARTS.map((p) => [p.name, p]),
);

const FALLBACK_PURPOSE: Record<string, string> = {
  human: "The human operator — origin of every intake and the final approver at gates.",
};

/**
 * Build a `NodeView` for one topology node, preferring live registry data and
 * falling back to the built-in fleet catalog so the inspector is never empty.
 * `runsByAgent` joins in the recent runs this node took part in (for deep-links).
 */
export function resolveNode(
  node: NetworkNode,
  registry: Map<string, AgentRecord>,
  runsByAgent?: Map<string, RunSummary[]>,
): NodeView {
  const record = registry.get(node.id) ?? null;
  const part = PART_BY_NAME.get(node.id);
  const description =
    record?.description ??
    part?.purpose ??
    FALLBACK_PURPOSE[node.id] ??
    `${node.label} — part of the ${node.system} system.`;

  return {
    ...node,
    record,
    description,
    runs: runsByAgent?.get(node.id) ?? [],
  };
}

/**
 * Group the live runs feed by the agent that owns each run, newest first, so the
 * inspector can show "recent runs" with clickable /runs/{id} deep-links. Best-
 * effort: runs without an agent field are skipped (the ambient mesh still shows).
 */
export function indexRunsByAgent(
  runs: RunSummary[],
): Map<string, RunSummary[]> {
  const map = new Map<string, RunSummary[]>();
  for (const r of runs) {
    const agent = (r.agent as string | null | undefined) ?? null;
    if (!agent || !r.run_id) continue;
    const list = map.get(agent) ?? [];
    list.push(r);
    map.set(agent, list);
  }
  return map;
}

/** Turn an AgentRecord[] into a name→record map for quick joins. */
export function indexRegistry(records: AgentRecord[]): Map<string, AgentRecord> {
  return new Map(records.map((r) => [r.name, r]));
}

/**
 * Derive an AgentRecord-shaped object from a fleet part, so the offline path
 * still feeds the inspector a real record (with autonomy/skills/mandate) for
 * agent nodes. Returns null for non-agent parts.
 */
export function recordFromPart(part: FleetPart): AgentRecord | null {
  if (!part.isAgent || part.autonomy_level == null || part.pipeline == null) {
    return null;
  }
  return {
    name: part.name,
    system: part.system,
    description: part.purpose,
    autonomy_level: part.autonomy_level,
    pipeline: part.pipeline,
    skills: part.skills ?? [],
    status: part.status,
    mandate_usd: part.mandate_usd ?? null,
    scorecard: null,
  };
}

/**
 * Build the offline registry map from the reference fleet's agents — used when
 * GET /registry is unavailable so agent nodes still inspect fully.
 */
export function offlineRegistry(): Map<string, AgentRecord> {
  const map = new Map<string, AgentRecord>();
  for (const part of REFERENCE_PARTS) {
    const rec = recordFromPart(part);
    if (rec) map.set(rec.name, rec);
  }
  return map;
}
