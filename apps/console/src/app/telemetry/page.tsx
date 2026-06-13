"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  LiveDot,
  Panel,
  Pill,
  ReferenceBadge,
  SectionHeader,
  Spinner,
} from "@/components/ui";
import type { CostRow } from "@/lib/api";
import { COLORS, withAlpha } from "@/lib/theme";
import { usePoll } from "@/lib/usePoll";

import { AnimatedNumber } from "./_components/AnimatedNumber";
import { BarChart, type BarDatum } from "./_components/BarChart";
import {
  TELEM_DIMENSIONS,
  fetchCostsBy,
  num,
  type TelemDimension,
} from "./_components/costFetch";
import { fmtCompact, fmtUsdAxis, fmtUsdCompact } from "./_components/format";
import { LiveStrip, type LiveChannel } from "./_components/LiveStrip";
import { referenceCosts } from "./_components/referenceCosts";
import { RunCostList } from "./_components/RunCostList";
import { TOKEN_LEGEND, TokenFlow, type TokenDatum } from "./_components/TokenFlow";

const POLL_MS = 3000;
const SERIES_CAP = 36; // rolling window of poll samples per channel

// ------------------------------------------------------------------ helpers ---

interface Totals {
  cost: number;
  calls: number;
  inputTokens: number;
  outputTokens: number;
}

function totalsOf(rows: CostRow[]): Totals {
  return rows.reduce<Totals>(
    (acc, r) => ({
      cost: acc.cost + num(r.cost_usd),
      calls: acc.calls + num(r.calls),
      inputTokens: acc.inputTokens + num(r.input_tokens),
      outputTokens: acc.outputTokens + num(r.output_tokens),
    }),
    { cost: 0, calls: 0, inputTokens: 0, outputTokens: 0 },
  );
}

function push(series: number[], v: number): number[] {
  const next = [...series, v];
  return next.length > SERIES_CAP ? next.slice(next.length - SERIES_CAP) : next;
}

// --------------------------------------------------------------------- page ---

export default function TelemetryPage() {
  const [by, setBy] = useState<TelemDimension>("agent");

  const fetcher = useCallback(() => fetchCostsBy(by), [by]);
  const { data, offline, loaded } = usePoll<CostRow[]>(fetcher, POLL_MS, by);

  // True only when we have NOTHING live to show → fall back to reference fleet.
  const usingReference = offline && (data === null || data.length === 0);
  const rows: CostRow[] = usingReference ? referenceCosts(by) : (data ?? []);

  // The run pivot becomes "cost per procurement" — a navigable list, not a chart.
  const byRun = by === "run_id";

  const t = totalsOf(rows);

  // Rolling live series (spend / calls / tokens), keyed off totals on each poll.
  const [spendSeries, setSpendSeries] = useState<number[]>([]);
  const [callsSeries, setCallsSeries] = useState<number[]>([]);
  const [tokenSeries, setTokenSeries] = useState<number[]>([]);
  const lastStampRef = useRef<string>("");

  // Reset live series at render time when the link drops to reference or the
  // pivot changes (mirrors usePoll's render-time reset — avoids stitching two
  // unrelated windows and keeps setState out of an effect body).
  const seriesKey = usingReference ? `ref` : `live:${by}`;
  const [prevSeriesKey, setPrevSeriesKey] = useState(seriesKey);
  if (prevSeriesKey !== seriesKey) {
    setPrevSeriesKey(seriesKey);
    setSpendSeries([]);
    setCallsSeries([]);
    setTokenSeries([]);
  }

  useEffect(() => {
    if (!loaded || usingReference) return;
    // Sample once per settled poll; the key dedupes within a window and the
    // dependency array fires only when totals actually change.
    const stamp = `${seriesKey}|${t.cost}|${t.calls}|${t.inputTokens}|${t.outputTokens}`;
    if (stamp === lastStampRef.current) return;
    lastStampRef.current = stamp;
    setSpendSeries((s) => push(s, t.cost));
    setCallsSeries((s) => push(s, t.calls));
    setTokenSeries((s) => push(s, t.inputTokens + t.outputTokens));
  }, [loaded, usingReference, seriesKey, t.cost, t.calls, t.inputTokens, t.outputTokens]);

  const channels: LiveChannel[] = [
    {
      label: "modeled cost / window",
      series: spendSeries,
      current: fmtUsdCompact(t.cost),
      color: COLORS.warn,
    },
    {
      label: "calls / window",
      series: callsSeries,
      current: fmtCompact(t.calls),
      color: COLORS.ok,
    },
    {
      label: "tokens / window",
      series: tokenSeries,
      current: fmtCompact(t.inputTokens + t.outputTokens),
      color: COLORS.autonomy,
    },
  ];

  // Bar chart data — cost by the selected dimension.
  const barData: BarDatum[] = rows
    .map((r) => ({
      key: r.key,
      value: num(r.cost_usd),
      meta: `${fmtCompact(num(r.calls))} calls`,
    }))
    .sort((a, b) => b.value - a.value);

  const tokenData: TokenDatum[] = rows
    .map((r) => ({
      key: r.key,
      input: num(r.input_tokens),
      output: num(r.output_tokens),
    }))
    .filter((d) => d.input + d.output > 0)
    .sort((a, b) => b.input + b.output - (a.input + a.output));

  const shownCount = Math.min(barData.length, 9);
  const overflow = barData.length - shownCount;

  const ratio =
    t.inputTokens + t.outputTokens > 0
      ? t.outputTokens / (t.inputTokens + t.outputTokens)
      : 0;

  const liveLabel = usingReference
    ? "REFERENCE"
    : offline
      ? "STALE"
      : loaded
        ? "LIVE"
        : "SYNC";

  return (
    <div className="space-y-6">
      <SectionHeader
        kicker="jai-meter · diagnostics"
        title="Telemetry"
        subtitle="The meter — real calls and tokens counted on every model invocation, sampled every 3 seconds. Cost is modeled from real per-model rates × those real tokens (no live API spend)."
        action={
          <div className="flex flex-wrap items-center justify-end gap-2">
            <ReferenceBadge mode={usingReference ? "reference" : "modeled"} />
            <LiveDot
              live={!offline}
              color={usingReference ? COLORS.warn : undefined}
              label={liveLabel}
            />
          </div>
        }
      />

      {usingReference && (
        <div
          className="flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2 text-xs"
          style={{
            borderColor: withAlpha(COLORS.autonomy, 0.35),
            background: withAlpha(COLORS.autonomy, 0.08),
            color: COLORS.autonomy,
          }}
        >
          <ReferenceBadge mode="reference" />
          <span>live telemetry unreachable — showing a reference fleet snapshot</span>
        </div>
      )}

      {/* headline instruments */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <HeadlineStat
          label="model calls"
          value={t.calls}
          format={(n) => fmtCompact(Math.round(n))}
          accent={COLORS.ok}
          sub="real · counted live"
        />
        <HeadlineStat
          label="tokens processed"
          value={t.inputTokens + t.outputTokens}
          format={(n) => fmtCompact(Math.round(n))}
          accent={COLORS.autonomy}
          sub={`real · ${(ratio * 100).toFixed(0)}% output`}
        />
        <HeadlineStat
          label="modeled cost"
          value={t.cost}
          format={fmtUsdCompact}
          accent={COLORS.warn}
          sub="rates × real tokens"
          glow
        />
      </div>

      {/* live sparkline strip */}
      <Panel
        accent="accent"
        flush
        title="live readout"
        action={
          <span className="label-cap" style={{ color: COLORS.inkFaint }}>
            rolling {SERIES_CAP}× · {POLL_MS / 1000}s
          </span>
        }
      >
        <LiveStrip channels={channels} />
      </Panel>

      {/* cost by dimension — the centerpiece. "run" pivots to cost-per-procurement. */}
      <Panel
        accent="accent"
        flush
        title={byRun ? "cost per procurement" : "modeled cost by dimension"}
        action={
          <div className="flex flex-wrap items-center justify-end gap-2.5">
            <ReferenceBadge mode={usingReference ? "reference" : "modeled"} />
            <div
              className="flex rounded-md border p-0.5"
              style={{ borderColor: COLORS.line }}
              role="tablist"
              aria-label="cost pivot dimension"
            >
              {TELEM_DIMENSIONS.map((d) => {
                const active = by === d.value;
                return (
                  <button
                    key={d.value}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    onClick={() => setBy(d.value)}
                    className="focus-ring metric rounded px-2.5 py-1 text-[11px] tracking-wide transition-colors"
                    style={{
                      background: active ? withAlpha(COLORS.accent, 0.14) : "transparent",
                      color: active ? COLORS.accent : COLORS.inkFaint,
                    }}
                  >
                    {d.label}
                  </button>
                );
              })}
            </div>
          </div>
        }
      >
        {byRun ? (
          rows.length > 0 ? (
            <>
              <RunCostList rows={rows} linked={!usingReference} max={10} />
              <div className="flex items-center justify-between border-t border-line px-4 py-2.5">
                <span className="label-cap">
                  {usingReference
                    ? "reference runs · click disabled offline"
                    : "each run → its full audit trail"}
                </span>
                <span className="metric text-[10px]" style={{ color: COLORS.inkFaint }}>
                  total {fmtUsdCompact(t.cost)} modeled
                </span>
              </div>
            </>
          ) : (
            <EmptyPlot loaded={loaded} />
          )
        ) : barData.length > 0 ? (
          <div className="px-3 py-3">
            <BarChart data={barData} format={fmtUsdAxis} max={9} />
            <div className="mt-1 flex items-center justify-between px-1">
              <span className="label-cap">
                {TELEM_DIMENSIONS.find((d) => d.value === by)?.keyHeader} · modeled cost (usd)
              </span>
              {overflow > 0 && (
                <span className="metric text-[10px]" style={{ color: COLORS.inkFaint }}>
                  +{overflow} more · total {fmtUsdCompact(t.cost)}
                </span>
              )}
            </div>
          </div>
        ) : (
          <EmptyPlot loaded={loaded} />
        )}
      </Panel>

      {/* token throughput */}
      <Panel
        accent="NETWORK"
        flush
        title="token throughput — input vs output"
        action={
          <div className="flex items-center gap-3">
            {TOKEN_LEGEND.map((l) => (
              <span key={l.label} className="flex items-center gap-1.5">
                <span
                  className="inline-block h-2 w-2 rounded-sm"
                  style={{ background: l.color }}
                  aria-hidden
                />
                <span className="label-cap" style={{ color: COLORS.inkFaint }}>
                  {l.label}
                </span>
              </span>
            ))}
          </div>
        }
      >
        {tokenData.length > 0 ? (
          <div className="px-3 py-3">
            <TokenFlow data={tokenData} format={fmtCompact} max={8} />
            <div className="mt-2 flex flex-wrap items-center gap-x-6 gap-y-1 px-1">
              <ThroughputTag
                label="input"
                value={fmtCompact(t.inputTokens)}
                color={COLORS.accent}
              />
              <ThroughputTag
                label="output"
                value={fmtCompact(t.outputTokens)}
                color={COLORS.autonomy}
              />
              <Pill tone="neutral">
                {fmtCompact(t.inputTokens + t.outputTokens)} total
              </Pill>
            </div>
          </div>
        ) : (
          <EmptyPlot loaded={loaded} />
        )}
      </Panel>
    </div>
  );
}

// ---------------------------------------------------------------- subviews ----

function HeadlineStat({
  label,
  value,
  format,
  accent,
  sub,
  glow = false,
}: {
  label: string;
  value: number;
  format: (n: number) => string;
  accent: string;
  sub?: string;
  glow?: boolean;
}) {
  return (
    <Panel className={glow ? "glow" : ""}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="label-cap">{label}</div>
          <div className="mt-2 flex items-baseline gap-2">
            <AnimatedNumber
              value={value}
              format={format}
              className="metric text-3xl font-semibold"
            />
          </div>
          {sub && (
            <div className="metric mt-1.5 text-[11px]" style={{ color: COLORS.inkFaint }}>
              {sub}
            </div>
          )}
        </div>
        <span
          aria-hidden
          className="mt-1 inline-block h-9 w-1 rounded-full"
          style={{
            background: `linear-gradient(to bottom, ${accent}, ${withAlpha(accent, 0)})`,
          }}
        />
      </div>
    </Panel>
  );
}

function ThroughputTag({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <span className="flex items-baseline gap-1.5">
      <span className="label-cap" style={{ color: withAlpha(color, 0.8) }}>
        {label}
      </span>
      <span className="metric text-xs font-semibold" style={{ color: COLORS.ink }}>
        {value}
      </span>
    </span>
  );
}

function EmptyPlot({ loaded }: { loaded: boolean }) {
  return (
    <div className="flex items-center justify-center px-6 py-14">
      {loaded ? (
        <span className="metric text-xs" style={{ color: COLORS.inkFaint }}>
          no spend recorded on this pivot yet
        </span>
      ) : (
        <Spinner label="acquiring telemetry…" />
      )}
    </div>
  );
}
