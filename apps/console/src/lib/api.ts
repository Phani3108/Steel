/**
 * Tiny typed fetch helpers for the JAI control-plane API.
 *
 * Base URL comes from NEXT_PUBLIC_JAI_API_URL (default http://localhost:8400).
 * All helpers throw on network/HTTP failure; pages catch and show the
 * "control plane offline" banner while keeping the last known state.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_JAI_API_URL ?? "http://localhost:8400";

export type CostDimension = "agent" | "tenant_id";

/** One aggregated line of GET /costs (mirrors jai-meter's CostRow). */
export interface CostRow {
  key: string;
  calls?: number;
  input_tokens?: number;
  output_tokens?: number;
  cost_usd: number | string;
}

/** One run summary from GET /runs. Fields beyond run_id are optional. */
export interface RunSummary {
  run_id: string;
  tenant_id?: string;
  agent?: string | null;
  actor_id?: string;
  started_at?: string;
  last_ts?: string;
  event_count?: number;
  cost_usd?: number | string;
  [key: string]: unknown;
}

export type Outcome = "ok" | "denied" | "error" | "escalated" | "pending_approval";

/** One audit event from GET /runs/{id}/events (mirrors jai_manifest.AuditEvent). */
export interface AuditEvent {
  seq?: number;
  event_id: string;
  ts: string;
  tenant_id: string;
  actor_id: string;
  actor_role: string;
  agent?: string | null;
  run_id: string;
  trace_id: string;
  action: string;
  outcome: Outcome;
  policy_version?: string | null;
  input_sha256?: string | null;
  detail?: Record<string, unknown>;
  hash?: string;
  prev_hash?: string;
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`GET ${path} -> HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

/** The control plane may return a bare list or wrap it ({items: [...]}) — accept both. */
function asList<T>(data: unknown, ...wrapperKeys: string[]): T[] {
  if (Array.isArray(data)) return data as T[];
  if (data && typeof data === "object") {
    for (const key of [...wrapperKeys, "items", "data"]) {
      const value = (data as Record<string, unknown>)[key];
      if (Array.isArray(value)) return value as T[];
    }
  }
  return [];
}

export async function fetchCosts(by: CostDimension): Promise<CostRow[]> {
  return asList<CostRow>(await getJSON(`/costs?by=${by}`), "costs", "rows");
}

export async function fetchRuns(): Promise<RunSummary[]> {
  return asList<RunSummary>(await getJSON("/runs"), "runs");
}

export async function fetchRunEvents(runId: string): Promise<AuditEvent[]> {
  return asList<AuditEvent>(
    await getJSON(`/runs/${encodeURIComponent(runId)}/events`),
    "events",
  );
}

/** Render a USD amount that may arrive as a JSON number or a Decimal-as-string. */
export function fmtUsd(value: number | string | undefined | null): string {
  const n = typeof value === "string" ? Number(value) : value;
  if (n === undefined || n === null || Number.isNaN(n)) return "—";
  return `$${n.toFixed(n >= 1 ? 2 : 6)}`;
}

/** Render an ISO timestamp compactly; pass through anything unparseable. */
export function fmtTs(ts: string | undefined): string {
  if (!ts) return "—";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}
