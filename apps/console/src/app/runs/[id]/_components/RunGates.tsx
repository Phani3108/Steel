"use client";

import Link from "next/link";

import { Pill } from "@/components/ui";
import { fmtTs, type RunApproval } from "@/lib/api";
import { COLORS } from "@/lib/theme";

/** A gate is still open if nobody has decided it yet. */
function isPending(status: string): boolean {
  return status === "pending" || status === "requested" || status === "open";
}

function gateTone(status: string): "ok" | "danger" | "info" {
  if (status === "approved") return "ok";
  if (status === "rejected" || status === "denied") return "danger";
  return "info";
}

/**
 * RunGates — the human approval gates this run passed through. Each row shows the
 * gate name, its decision pill, and who decided it (or that it's still waiting).
 * A pending gate gets a direct "review in approvals →" deep-link so the run story
 * connects straight to the action it needs — solving the dead-end run_id.
 */
export function RunGates({ approvals }: { approvals: RunApproval[] }) {
  if (approvals.length === 0) {
    return (
      <p className="text-xs text-ink-faint">
        This run cleared without hitting a human gate.
      </p>
    );
  }

  return (
    <ul className="space-y-2.5">
      {approvals.map((a) => {
        const pending = isPending(a.status);
        return (
          <li key={a.id} className="rounded-md border border-line bg-panel-2 px-3 py-2">
            <div className="flex items-center justify-between gap-2">
              <span className="metric truncate text-[12px] text-ink">
                {a.gate.replace(/_/g, " ")}
              </span>
              <Pill tone={gateTone(a.status)}>{a.status}</Pill>
            </div>
            <div className="metric mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] text-ink-faint">
              {a.requested_by && <span>by {a.requested_by}</span>}
              {a.decided_by ? (
                <span>· decided {a.decided_by}</span>
              ) : pending ? (
                <span style={{ color: COLORS.info }}>· awaiting decision</span>
              ) : null}
              {(a.decided_at || a.ts) && <span>· {fmtTs(a.decided_at ?? a.ts ?? undefined)}</span>}
            </div>
            {pending && (
              <Link
                href="/approvals"
                className="focus-ring mt-1.5 inline-flex items-center gap-1 rounded text-[10.5px] text-accent transition-opacity hover:opacity-80"
              >
                review in approvals →
              </Link>
            )}
          </li>
        );
      })}
    </ul>
  );
}
