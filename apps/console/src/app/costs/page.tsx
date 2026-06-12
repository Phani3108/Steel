"use client";

import { useCallback, useState } from "react";

import { OfflineBanner } from "../../components/OfflineBanner";
import { fetchCosts, fmtUsd, type CostDimension, type CostRow } from "../../lib/api";
import { usePoll } from "../../lib/usePoll";

const DIMENSIONS: { value: CostDimension; label: string }[] = [
  { value: "agent", label: "by agent" },
  { value: "tenant_id", label: "by tenant" },
];

function num(v: number | undefined): string {
  return v === undefined ? "—" : v.toLocaleString();
}

export default function CostsPage() {
  const [by, setBy] = useState<CostDimension>("agent");
  const fetcher = useCallback(() => fetchCosts(by), [by]);
  const { data, offline, loaded } = usePoll<CostRow[]>(fetcher, 2000, by);

  const rows = data ?? [];
  const total = rows.reduce((sum, r) => {
    const n = typeof r.cost_usd === "string" ? Number(r.cost_usd) : r.cost_usd;
    return sum + (Number.isNaN(n) ? 0 : n);
  }, 0);

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-50">Costs</h1>
          <p className="mt-1 text-sm text-zinc-400">
            The meter — what every action cost, refreshed every 2s.
          </p>
        </div>
        <div className="flex rounded-md border border-zinc-800 p-0.5">
          {DIMENSIONS.map((d) => (
            <button
              key={d.value}
              onClick={() => setBy(d.value)}
              className={`rounded px-3 py-1.5 font-mono text-xs transition-colors ${
                by === d.value
                  ? "bg-zinc-800 text-zinc-50"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6">
        <OfflineBanner show={offline} />

        <div className="overflow-x-auto rounded-lg border border-zinc-800">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-zinc-800 bg-zinc-900/60 font-mono text-[11px] uppercase tracking-wider text-zinc-500">
              <tr>
                <th className="px-4 py-2.5">{by === "agent" ? "agent" : "tenant"}</th>
                <th className="px-4 py-2.5 text-right">calls</th>
                <th className="px-4 py-2.5 text-right">input tokens</th>
                <th className="px-4 py-2.5 text-right">output tokens</th>
                <th className="px-4 py-2.5 text-right">cost (usd)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/70">
              {rows.map((row) => (
                <tr key={row.key} className="hover:bg-zinc-900/40">
                  <td className="px-4 py-2.5 font-mono text-zinc-200">{row.key}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-zinc-400">
                    {num(row.calls)}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-zinc-400">
                    {num(row.input_tokens)}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-zinc-400">
                    {num(row.output_tokens)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-emerald-400">
                    {fmtUsd(row.cost_usd)}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-sm text-zinc-500">
                    {loaded ? "no spend recorded yet" : "loading…"}
                  </td>
                </tr>
              )}
            </tbody>
            {rows.length > 0 && (
              <tfoot className="border-t border-zinc-800 bg-zinc-900/60">
                <tr>
                  <td className="px-4 py-2.5 font-mono text-xs text-zinc-500">total</td>
                  <td colSpan={3} />
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-emerald-300">
                    {fmtUsd(total)}
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>
    </div>
  );
}
