"use client";

import { fmtUsd, type RunCostRow } from "@/lib/api";
import { systemHue, withAlpha } from "@/lib/theme";

import { resolveAgent } from "./agents";

/**
 * RunCostBars — the run's modeled spend, broken down per agent as a compact bar
 * list. Each row is tinted with its agent's system hue and sized against the
 * costliest agent, so the spend shape reads at a glance. Cost is MODELED (real
 * per-model rates × real tokens) — the panel labels it as such, no API spend.
 */
export function RunCostBars({
  costs,
  total,
}: {
  costs: RunCostRow[];
  total: number;
}) {
  if (costs.length === 0) {
    return (
      <p className="text-xs text-ink-faint">No modeled cost recorded for this run yet.</p>
    );
  }

  const rows = [...costs].sort((a, b) => b.cost_usd - a.cost_usd);
  const max = Math.max(...rows.map((r) => r.cost_usd), 1e-9);

  return (
    <div className="space-y-2.5">
      {rows.map((c) => {
        const meta = resolveAgent(c.agent);
        const hue = systemHue(meta.system);
        const pct = Math.max(2, (c.cost_usd / max) * 100);
        const tokens = (c.input_tokens ?? 0) + (c.output_tokens ?? 0);
        return (
          <div key={c.agent}>
            <div className="flex items-baseline justify-between gap-2">
              <span className="metric flex min-w-0 items-center gap-1.5 truncate text-[11px] text-ink">
                <span
                  className="h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ background: hue }}
                  aria-hidden
                />
                <span className="truncate">{meta.label}</span>
              </span>
              <span className="metric shrink-0 text-[11px] text-ink">
                {fmtUsd(c.cost_usd)}
              </span>
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-panel-2">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${pct}%`,
                  background: `linear-gradient(to right, ${withAlpha(hue, 0.55)}, ${hue})`,
                }}
              />
            </div>
            <div className="metric mt-0.5 flex items-center gap-2 text-[9.5px] text-ink-faint">
              <span>{c.calls ?? 0} call{(c.calls ?? 0) === 1 ? "" : "s"}</span>
              {tokens > 0 && <span>· {tokens.toLocaleString()} tok</span>}
            </div>
          </div>
        );
      })}

      <div className="mt-1 flex items-baseline justify-between border-t border-line pt-2.5">
        <span className="label-cap">total</span>
        <span className="metric text-[13px] font-semibold text-ink">{fmtUsd(total)}</span>
      </div>
    </div>
  );
}
