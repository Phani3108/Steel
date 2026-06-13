"use client";

import Link from "next/link";
import { useMemo } from "react";

import { Pill, SystemBadge } from "@/components/ui";
import { fmtTs, fmtUsd, type Outcome, type RunSummary } from "@/lib/api";
import { REFERENCE_PARTS } from "@/lib/fleet";
import { COLORS, outcomeColor, withAlpha, type System } from "@/lib/theme";

/** name → system, built once from the reference fleet (for the per-run badge). */
const PART_SYSTEM: Record<string, System> = Object.fromEntries(
  REFERENCE_PARTS.map((p) => [p.name, p.system]),
);

const KNOWN_OUTCOMES: ReadonlySet<string> = new Set<Outcome>([
  "ok",
  "denied",
  "error",
  "escalated",
  "pending_approval",
]);

/** The /runs contract carries `outcome`, but RunSummary types it loosely — read it safely. */
function runOutcome(run: RunSummary): Outcome | null {
  const o = (run as { outcome?: unknown }).outcome;
  return typeof o === "string" && KNOWN_OUTCOMES.has(o) ? (o as Outcome) : null;
}

function eventCount(run: RunSummary): number | null {
  const direct = run.event_count;
  if (typeof direct === "number") return direct;
  const alt = (run as { events?: unknown }).events;
  return typeof alt === "number" ? alt : null;
}

interface RunListProps {
  runs: RunSummary[];
  selected: string | null;
  onSelect: (id: string) => void;
  loaded: boolean;
}

/**
 * RunList — the flight-recorder index. A polling list of runs, each a row with
 * its agent's SystemBadge, an outcome Pill, event count, last-seen time, and
 * cost. The active row gets an accent rail and tinted fill.
 */
export function RunList({ runs, selected, onSelect, loaded }: RunListProps) {
  const rows = useMemo(
    () =>
      runs.map((run) => ({
        run,
        outcome: runOutcome(run),
        system: run.agent ? PART_SYSTEM[run.agent] : undefined,
        events: eventCount(run),
        ts: run.last_ts ?? run.started_at,
      })),
    [runs],
  );

  if (rows.length === 0) {
    return (
      <div className="px-4 py-12 text-center text-sm text-ink-faint">
        {loaded ? "no runs recorded yet" : "loading flight log…"}
      </div>
    );
  }

  return (
    <ul className="divide-y divide-line/70">
      {rows.map(({ run, outcome, system, events, ts }) => {
        const active = run.run_id === selected;
        const oc = outcome ? outcomeColor(outcome) : COLORS.inkFaint;
        return (
          <li key={run.run_id} className="group/row relative">
            {active && (
              <span
                aria-hidden
                className="absolute inset-y-0 left-0 w-0.5"
                style={{ background: oc, boxShadow: `0 0 8px -1px ${oc}` }}
              />
            )}
            {/* deep-link to the standalone run-detail view (a run_id you can click).
                Always visible so the audit index reads as navigable — the row's own
                click still drives the inline master-detail preview beside it. */}
            <Link
              href={`/runs/${encodeURIComponent(run.run_id)}`}
              onClick={(e) => e.stopPropagation()}
              aria-label={`Open run ${run.run_id} detail`}
              title="open full run detail →"
              className="focus-ring absolute right-2 top-2 z-10 rounded border border-line bg-panel-2/80 px-1.5 py-0.5 font-mono text-[10px] text-ink-faint opacity-70 transition-all hover:border-accent/50 hover:text-accent group-hover/row:opacity-100"
            >
              open →
            </Link>
            <button
              type="button"
              onClick={() => onSelect(run.run_id)}
              className={`focus-ring block w-full px-4 py-3 text-left transition-colors ${
                active ? "bg-panel-2" : "hover:bg-panel-2/60"
              }`}
              style={active ? { background: withAlpha(oc, 0.06) } : undefined}
              aria-current={active ? "true" : undefined}
            >
              <div className="flex items-center justify-between gap-3 pr-12">
                <span className="metric truncate text-[13px] text-ink">
                  {run.run_id}
                </span>
                {outcome && (
                  <Pill outcome={outcome} className="shrink-0">
                    {outcome}
                  </Pill>
                )}
              </div>

              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5">
                {run.agent ? (
                  system ? (
                    <span className="inline-flex items-center gap-1.5">
                      <SystemBadge system={system} dotOnly />
                      <span className="metric text-[11px] text-ink-muted">
                        {run.agent}
                      </span>
                    </span>
                  ) : (
                    <span className="metric text-[11px] text-ink-muted">
                      {run.agent}
                    </span>
                  )
                ) : (
                  <span className="metric text-[11px] text-ink-faint">—</span>
                )}

                {run.tenant_id && (
                  <span className="text-[11px] text-ink-faint">
                    {run.tenant_id}
                  </span>
                )}
                {events !== null && (
                  <span className="metric text-[11px] text-ink-faint">
                    {events} ev
                  </span>
                )}
                {run.cost_usd !== undefined && run.cost_usd !== null && (
                  <span className="metric ml-auto text-[11px] text-ok">
                    {fmtUsd(run.cost_usd)}
                  </span>
                )}
              </div>

              <div className="mt-1 text-[10px] text-ink-ghost">{fmtTs(ts)}</div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
