/**
 * Shared types + small presentational helpers for the /approvals (Gates) screen.
 *
 * An "approval" is a durably-paused agent run: steel-brakes parked the run at a
 * human-in-the-loop gate and is waiting on a verdict. Deciding here RESUMES the
 * run — that's the wow this screen exists to convey.
 */

import { COLORS } from "@/lib/theme";

/** One pending gate row from GET /approvals (mirrors the API contract). */
export interface Approval {
  id: number;
  ts: string;
  tenant_id: string;
  gate: string;
  agent?: string | null;
  run_id: string;
  thread_id: string;
  requested_by: string;
  payload: {
    event_id?: string;
    title?: string;
    est_value_usd?: number;
    best_bid?: { supplier_id?: string; total_usd?: number } | null;
  };
}

/** A resolved card mid-animation: which way it went, so the exit can be tinted. */
export type Verdict = "approve" | "reject";

/** Per-gate copy: a human label + the one-line stake the operator is unblocking. */
interface GateMeta {
  label: string;
  /** What approving this gate actually does, in plain procurement language. */
  resumes: string;
  color: string;
}

const GATES: Record<string, GateMeta> = {
  rfx_publish: {
    label: "RFx publish",
    resumes: "publishes the sourcing event to suppliers and opens bidding",
    color: COLORS.info,
  },
  award_approval: {
    label: "award approval",
    resumes: "awards the event to the leading bid and closes sourcing",
    color: COLORS.ok,
  },
};

/** Resolve a gate id to its display metadata, with a safe fallback. */
export function gateMeta(gate: string): GateMeta {
  return (
    GATES[gate] ?? {
      label: gate.replace(/_/g, " "),
      resumes: "resumes the paused run from this gate",
      color: COLORS.accent,
    }
  );
}

/** Map an agent name to its car system for the SystemBadge. */
export function agentSystem(agent?: string | null): string {
  if (!agent) return "NETWORK";
  // Every shipped agent lives in the NETWORK fleet; services elsewhere.
  if (agent.startsWith("agent-")) return "NETWORK";
  if (agent.startsWith("mcp-")) return "DRIVETRAIN";
  return "NETWORK";
}

/**
 * The money at stake on a gate — prefer a concrete best bid, fall back to the
 * estimate. Returns the amount plus whether it's a firm bid or an estimate.
 */
export function moneyAtStake(a: Approval): {
  amount: number | undefined;
  firm: boolean;
  supplier?: string;
} {
  const bid = a.payload?.best_bid;
  if (bid && typeof bid.total_usd === "number") {
    return { amount: bid.total_usd, firm: true, supplier: bid.supplier_id };
  }
  return { amount: a.payload?.est_value_usd, firm: false };
}

/** Whole-dollar USD, grouped — the headline money on each card. */
export function fmtUsdFull(n: number | undefined): string {
  if (n === undefined || Number.isNaN(n)) return "—";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

/** Compact "Jun 13, 10:42:07" timestamp for the gate's arrival time. */
export function fmtClock(ts: string | undefined): string {
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

/** "4m ago" relative age — shows how long a run has been parked at the gate. */
export function fmtAge(ts: string | undefined, now: number): string {
  if (!ts) return "";
  const then = new Date(ts).getTime();
  if (Number.isNaN(then)) return "";
  const secs = Math.max(0, Math.round((now - then) / 1000));
  if (secs < 60) return `${secs}s waiting`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m waiting`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h waiting`;
  return `${Math.floor(hrs / 24)}d waiting`;
}
