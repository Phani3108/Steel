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

/** POST a JSON body and parse the JSON reply. Throws on network/HTTP failure. */
async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`POST ${path} -> HTTP ${res.status}`);
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

/**
 * A node in the fleet graph (GET /network). NOW LIVE — `live`/`status` reflect the
 * control-plane registry, so a node can be dark even when the topology resolves.
 */
export interface NetworkNode {
  id: string;
  label: string;
  system: AgentRecord["system"];
  role: "human" | "agent" | "service";
  /** True when the node's agent/service is reporting in. */
  live?: boolean;
  /** Lifecycle status string (active/paused/…) or null when unknown. */
  status?: string | null;
}

/**
 * A directed edge in the fleet graph. Edges now carry REAL hop counts: `hops` is
 * how many times this A2A handoff has actually fired, `active` lights it up.
 */
export interface NetworkEdge {
  source: string;
  target: string;
  label?: string;
  /** Number of real A2A hops observed across this edge. */
  hops?: number;
  /** True when this handoff has fired recently. */
  active?: boolean;
}

/** One entry in the live A2A activity feed (GET /network.recent_hops). */
export interface RecentHop {
  from_agent: string;
  to_agent: string;
  skill_id: string;
  ok: boolean;
}

export interface NetworkTopology {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  /** True when the mesh is reporting live A2A traffic. */
  live: boolean;
  /** How many agents are registered in the control plane. */
  agents_registered: number;
  /** Total A2A hops observed across the whole mesh. */
  total_hops: number;
  /** Most-recent A2A handoffs, newest first — a live activity feed. */
  recent_hops: RecentHop[];
}

export async function fetchNetwork(): Promise<NetworkTopology> {
  const data = await getJSON<Partial<NetworkTopology>>("/network");
  return {
    nodes: Array.isArray(data?.nodes) ? data.nodes : [],
    edges: Array.isArray(data?.edges) ? data.edges : [],
    live: Boolean(data?.live),
    agents_registered:
      typeof data?.agents_registered === "number" ? data.agents_registered : 0,
    total_hops: typeof data?.total_hops === "number" ? data.total_hops : 0,
    recent_hops: Array.isArray(data?.recent_hops) ? data.recent_hops : [],
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

/** Request body for POST /orchestrate. Only `title` is required by the API. */
export interface OrchestrateBody {
  title: string;
  category?: string;
  est_value_usd?: number;
  tenant_id?: string;
  role?: string;
  /** Skip the human gate and auto-approve over-mandate awards (demo path). */
  auto_approve?: boolean;
}

/** Result of POST /orchestrate. */
export interface OrchestrateResult {
  run_id: string;
  trace_id: string;
  status: string;
  hops: OrchestrateHop[];
  /** Memo lines composed by the orchestrator (optional). */
  memos?: string[];
  event_id?: string;
  award: { supplier_id: string; total_usd: number } | null;
  paused_gate: string | null;
  /** Total modeled cost of the run (no real API spend). */
  total_cost_usd?: number;
}

export async function postOrchestrate(
  body: OrchestrateBody,
): Promise<OrchestrateResult> {
  return postJSON<OrchestrateResult>("/orchestrate", body);
}

/**
 * One-click demo: launch a sensible sample procurement end-to-end. Used by Home's
 * "▶ Run a sample procurement" button — the caller routes to /runs/{run_id} on the
 * returned result so a newcomer sees the whole journey work in a single click.
 */
export async function startSampleProcurement(): Promise<OrchestrateResult> {
  return postOrchestrate({
    title: "Sample: Line-2 PPE refresh",
    est_value_usd: 120_000,
    role: "cpo",
    auto_approve: true,
  });
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

// ====================================================================
// Run detail — the deep-linkable single-run view (GET /runs/{id}/detail).
// The whole story of one procurement: summary, hash-chained events, modeled
// per-agent cost, and the approval gates it passed through. Throws on failure;
// the page renders a graceful "run not found / offline" state.
// ====================================================================

/** Rolled-up summary of a single run (GET /runs/{id}/detail.summary). */
export interface RunDetailSummary {
  first_ts: string | null;
  last_ts: string | null;
  tenant_id: string | null;
  events: number;
  outcome: string | null;
  agents: string[];
}

/** One modeled per-agent cost line for a run. */
export interface RunCostRow {
  agent: string;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

/** One approval gate this run passed through. */
export interface RunApproval {
  id: number;
  gate: string;
  status: string;
  agent: string | null;
  thread_id: string | null;
  requested_by: string | null;
  decided_by: string | null;
  payload: Record<string, unknown> | null;
  ts: string | null;
  decided_at: string | null;
}

/** Full single-run detail (GET /runs/{id}/detail). */
export interface RunDetail {
  run_id: string;
  found: boolean;
  summary: RunDetailSummary;
  events: AuditEvent[];
  costs: RunCostRow[];
  cost_total_usd: number;
  approvals: RunApproval[];
}

export async function fetchRunDetail(runId: string): Promise<RunDetail> {
  const data = await getJSON<Partial<RunDetail>>(
    `/runs/${encodeURIComponent(runId)}/detail`,
  );
  return {
    run_id: data?.run_id ?? runId,
    found: Boolean(data?.found),
    summary: {
      first_ts: data?.summary?.first_ts ?? null,
      last_ts: data?.summary?.last_ts ?? null,
      tenant_id: data?.summary?.tenant_id ?? null,
      events: data?.summary?.events ?? 0,
      outcome: data?.summary?.outcome ?? null,
      agents: Array.isArray(data?.summary?.agents) ? data.summary.agents : [],
    },
    events: Array.isArray(data?.events) ? data.events : [],
    costs: Array.isArray(data?.costs) ? data.costs : [],
    cost_total_usd:
      typeof data?.cost_total_usd === "number" ? data.cost_total_usd : 0,
    approvals: Array.isArray(data?.approvals) ? data.approvals : [],
  };
}
