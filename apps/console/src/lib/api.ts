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

/** Persona metadata from GET /meta. */
export interface Meta {
  tenants: { id: string; name: string }[];
  roles: string[];
}

export async function fetchMeta(): Promise<Meta> {
  return await getJSON<Meta>("/meta");
}

/** One citation on a chat answer (mirrors jai-cortex's Citation). */
export interface ChatCitation {
  source_type: string;
  source_id: string;
  snippet?: string;
}

export interface ChatReply {
  text: string;
  citations: ChatCitation[];
  refused: boolean;
  cost_usd: number;
  run_id: string;
}

export async function postChat(
  message: string,
  role: string,
  tenantId: string,
): Promise<ChatReply> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, role, tenant_id: tenantId }),
  });
  if (!res.ok) {
    throw new Error(`POST /chat -> HTTP ${res.status}`);
  }
  return (await res.json()) as ChatReply;
}

// ====================================================================
// Phase-1 additions — registry, network, orchestration, health.
// All throw on failure; callers catch and fall back to the reference fleet.
// ====================================================================

/** Health ping (GET /health). */
export interface Health {
  status: string;
  postgres?: boolean;
}

export async function fetchHealth(): Promise<Health> {
  return await getJSON<Health>("/health");
}

/** One agent's scorecard (mirrors jai-dyno's scorecard shape). */
export interface Scorecard {
  suite: string;
  pass_rate: number;
  n_cases: number;
  n_passed: number;
  ts: string;
}

/** One agent/part record from GET /registry. */
export interface AgentRecord {
  name: string;
  system: "POWERTRAIN" | "CHASSIS" | "DRIVETRAIN" | "SAFETY" | "NETWORK" | "COCKPIT";
  description: string;
  autonomy_level: 1 | 2 | 3 | 4 | 5;
  pipeline: "direct" | "rag" | "sourcing" | "orchestrate";
  skills: string[];
  status: "active" | "paused" | "killed" | "planned";
  mandate_usd: number | null;
  scorecard: Scorecard | null;
  updated_at?: string;
}

export async function fetchRegistry(): Promise<AgentRecord[]> {
  return asList<AgentRecord>(await getJSON("/registry"), "registry", "agents");
}

/** A node in the fleet graph (GET /network). */
export interface NetworkNode {
  id: string;
  label: string;
  system: AgentRecord["system"];
  role: "human" | "agent" | "service";
}

/** A directed edge in the fleet graph. */
export interface NetworkEdge {
  source: string;
  target: string;
  label?: string;
}

export interface NetworkTopology {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

export async function fetchNetwork(): Promise<NetworkTopology> {
  const data = await getJSON<Partial<NetworkTopology>>("/network");
  return {
    nodes: Array.isArray(data?.nodes) ? data.nodes : [],
    edges: Array.isArray(data?.edges) ? data.edges : [],
  };
}

/** One hop in an orchestration trace. */
export interface OrchestrateHop {
  from_agent: string;
  to_agent: string;
  skill_id: string;
  ok: boolean;
  cost_usd: number;
  summary: string;
}

/** Request body for POST /orchestrate. */
export interface OrchestrateBody {
  title: string;
  category: string;
  est_value_usd: number;
  tenant_id: string;
  role: string;
}

/** Result of POST /orchestrate. */
export interface OrchestrateResult {
  run_id: string;
  trace_id: string;
  status: string;
  hops: OrchestrateHop[];
  event_id?: string;
  award: { supplier_id: string; total_usd: number } | null;
  paused_gate: string | null;
}

export async function postOrchestrate(
  body: OrchestrateBody,
): Promise<OrchestrateResult> {
  const res = await fetch(`${API_BASE}/orchestrate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`POST /orchestrate -> HTTP ${res.status}`);
  }
  return (await res.json()) as OrchestrateResult;
}

// ====================================================================
// Phase-2 additions — negotiation, maturity gates, transparency, manifest.
// Same contract as above: helpers throw on failure; callers catch and fall
// back to a static reference so every screen stays meaningful offline.
// ====================================================================

/** One exchanged offer/counter in a negotiation transcript. */
export interface NegotiationTurn {
  round: number;
  offer: number;
  counter: number;
  action: "counter_up" | "accept_counter" | "seller_accepts";
}

/** A seller the negotiator can engage (skill-routed). */
export interface NegotiationSeller {
  skill_id: string;
  name: string;
}

/** Request body for POST /negotiate. */
export interface NegotiationBody {
  list_price: number;
  seller: number;
  tenant_id?: string;
  role?: string;
}

/** Result of POST /negotiate (mirrors the negotiate pipeline shape). */
export interface NegotiationResult {
  status: "deal" | "no_deal" | "walked";
  seller: string;
  list_price: number;
  final_price: number | null;
  savings_pct: number;
  payment_terms_days: number | null;
  rounds: number;
  mandate_cap: number | null;
  breached: boolean;
  closed: boolean;
  transcript: NegotiationTurn[];
  run_id: string;
  sellers: NegotiationSeller[];
}

export async function postNegotiate(
  body: NegotiationBody,
): Promise<NegotiationResult> {
  const res = await fetch(`${API_BASE}/negotiate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`POST /negotiate -> HTTP ${res.status}`);
  }
  return (await res.json()) as NegotiationResult;
}

/** One agent's maturity-gate row from GET /maturity. */
export interface MaturityRow {
  agent: string;
  current_level: 1 | 2 | 3 | 4 | 5;
  has_scorecard: boolean;
  pass_rate?: number;
  promote?: boolean;
  to_level?: number;
  reasons?: string[];
}

export async function fetchMaturity(): Promise<MaturityRow[]> {
  return asList<MaturityRow>(await getJSON("/maturity"), "maturity", "agents");
}

/** EU AI Act Article 50 transparency disclosure (GET /transparency). */
export interface Transparency {
  ai_system: boolean;
  notice: string;
  regulation: string;
  data: string;
  human_oversight: string;
}

export async function fetchTransparency(): Promise<Transparency> {
  return await getJSON<Transparency>("/transparency");
}

/** Result of POST /manifest/validate — a parsed/validated agent manifest. */
export interface ManifestCheck {
  valid: boolean;
  name?: string;
  autonomy_level?: number;
  pipeline?: string;
  skills?: string[];
  error?: string;
}

export async function postManifestValidate(yaml: string): Promise<ManifestCheck> {
  const res = await fetch(`${API_BASE}/manifest/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yaml }),
  });
  if (!res.ok) {
    throw new Error(`POST /manifest/validate -> HTTP ${res.status}`);
  }
  return (await res.json()) as ManifestCheck;
}
