"use client";

import { useCallback, useState } from "react";
import { OfflineBanner } from "../../components/OfflineBanner";
import { API_BASE, fmtTs, fmtUsd } from "../../lib/api";
import { usePoll } from "../../lib/usePoll";

interface Approval {
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

async function fetchApprovals(): Promise<Approval[]> {
  const res = await fetch(`${API_BASE}/approvals`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET /approvals -> ${res.status}`);
  return (await res.json()) as Approval[];
}

export default function ApprovalsPage() {
  const [deciding, setDeciding] = useState<number | null>(null);
  const [decided, setDecided] = useState<number[]>([]);
  const { data, offline } = usePoll<Approval[]>(fetchApprovals, 3000);

  const decide = useCallback(async (id: number, approve: boolean) => {
    setDeciding(id);
    try {
      await fetch(`${API_BASE}/approvals/${id}/decide`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          approver: "console.user",
          approve,
          note: approve ? "approved from console" : "rejected from console",
        }),
      });
      setDecided((d) => [...d, id]); // optimistic; the next poll confirms
    } finally {
      setDeciding(null);
    }
  }, []);

  const rows = (data ?? []).filter((a) => !decided.includes(a.id));
  return (
    <main className="mx-auto max-w-4xl space-y-4">
      <OfflineBanner show={offline} />
      <div className="flex items-baseline justify-between">
        <h1 className="text-lg font-semibold text-zinc-100">Approvals inbox</h1>
        <span className="text-xs text-zinc-500">
          gates pause agents durably — deciding here lets the run resume
        </span>
      </div>

      {rows.length === 0 ? (
        <p className="rounded-lg border border-zinc-800 bg-zinc-950 p-6 text-sm text-zinc-500">
          Nothing pending. Run <code className="text-zinc-400">make demo-p2</code> (or start a
          sourcing event) and the publish/award gates will land here.
        </p>
      ) : (
        <ul className="space-y-3">
          {rows.map((a) => (
            <li
              key={a.id}
              className="rounded-lg border border-zinc-800 bg-zinc-950 p-4 text-sm"
            >
              <div className="flex items-center gap-2">
                <span className="rounded-full border border-amber-700/60 bg-amber-950/40 px-2 py-0.5 text-[11px] text-amber-300">
                  {a.gate}
                </span>
                <span className="font-medium text-zinc-100">
                  {a.payload?.title ?? a.payload?.event_id ?? `approval #${a.id}`}
                </span>
                <span className="ml-auto text-[11px] text-zinc-600">{fmtTs(a.ts)}</span>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-1 text-[12px] text-zinc-400 sm:grid-cols-4">
                <span>tenant {a.tenant_id}</span>
                <span>agent {a.agent ?? "—"}</span>
                <span>event {a.payload?.event_id ?? "—"}</span>
                <span>
                  {a.payload?.best_bid
                    ? `best bid ${fmtUsd(a.payload.best_bid.total_usd)}`
                    : `est ${fmtUsd(a.payload?.est_value_usd)}`}
                </span>
              </div>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => decide(a.id, true)}
                  disabled={deciding === a.id}
                  className="rounded-md bg-emerald-700 px-3 py-1 text-xs font-medium text-emerald-50 hover:bg-emerald-600 disabled:opacity-40"
                >
                  Approve
                </button>
                <button
                  onClick={() => decide(a.id, false)}
                  disabled={deciding === a.id}
                  className="rounded-md bg-rose-900 px-3 py-1 text-xs font-medium text-rose-100 hover:bg-rose-800 disabled:opacity-40"
                >
                  Reject
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
