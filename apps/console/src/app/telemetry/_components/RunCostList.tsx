"use client";

import Link from "next/link";

import type { CostRow } from "@/lib/api";
import { COLORS, withAlpha } from "@/lib/theme";

import { num } from "./costFetch";
import { fmtCompact, fmtUsdCompact } from "./format";

/**
 * RunCostList — the "cost per procurement" pivot. The bar chart is pure SVG and
 * can't carry per-row links, so when telemetry is pivoted by `run_id` we render
 * the rows as a navigable list instead: each run is a link to /runs/{run_id}
 * (closing the un-clickable run_id gap from the audit). Real metrics lead —
 * calls and tokens were always real — with the modeled cost flush-right.
 */

interface RunCostListProps {
  rows: CostRow[];
  /** When offline-reference, rows are synthetic — don't link them anywhere. */
  linked: boolean;
  max?: number;
}

export function RunCostList({ rows, linked, max = 10 }: RunCostListProps) {
  const sorted = [...rows]
    .sort((a, b) => num(b.cost_usd) - num(a.cost_usd))
    .slice(0, max);
  const peak = sorted.reduce((m, r) => Math.max(m, num(r.cost_usd)), 0);

  if (sorted.length === 0) return null;

  return (
    <ul className="divide-y divide-line/70">
      {sorted.map((r) => {
        const cost = num(r.cost_usd);
        const calls = num(r.calls);
        const tokens = num(r.input_tokens) + num(r.output_tokens);
        const frac = peak > 0 ? cost / peak : 0;

        const body = (
          <div className="relative px-4 py-3">
            {/* faint cost-share rail behind each row */}
            <span
              aria-hidden
              className="absolute inset-y-0 left-0"
              style={{
                width: `${Math.max(frac * 100, cost > 0 ? 3 : 0)}%`,
                background: withAlpha(COLORS.accent, 0.07),
              }}
            />
            <div className="relative flex items-center justify-between gap-3">
              <span className="metric truncate text-[13px] text-ink">{r.key}</span>
              <span
                className="metric shrink-0 text-[13px] font-semibold"
                style={{ color: COLORS.warn }}
                title="modeled cost · no API spend"
              >
                {fmtUsdCompact(cost)}
              </span>
            </div>
            <div className="relative mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="metric text-[11px] text-ink-muted">
                {fmtCompact(calls)} calls
              </span>
              <span className="metric text-[11px] text-ink-muted">
                {fmtCompact(tokens)} tokens
              </span>
              <span className="metric text-[10px] text-ink-faint">
                in {fmtCompact(num(r.input_tokens))} · out{" "}
                {fmtCompact(num(r.output_tokens))}
              </span>
              {linked && (
                <span className="metric ml-auto text-[10px] text-ink-faint transition-colors group-hover/run:text-accent">
                  open run →
                </span>
              )}
            </div>
          </div>
        );

        return (
          <li key={r.key} className="group/run relative">
            {linked ? (
              <Link
                href={`/runs/${encodeURIComponent(r.key)}`}
                aria-label={`Open run ${r.key} — modeled cost ${fmtUsdCompact(cost)}`}
                title="open full run detail →"
                className="focus-ring block transition-colors hover:bg-panel-2/60"
              >
                {body}
              </Link>
            ) : (
              body
            )}
          </li>
        );
      })}
    </ul>
  );
}
