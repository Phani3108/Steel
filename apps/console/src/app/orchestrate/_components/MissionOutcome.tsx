"use client";

import Link from "next/link";
import { motion } from "motion/react";

import { Pill } from "@/components/ui";
import { COLORS, withAlpha } from "@/lib/theme";
import { rollupCost, type MissionState } from "./demo";

interface MissionOutcomeProps {
  state: MissionState;
}

function fmtUsdFull(n: number): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

/**
 * The mission verdict: an award (supplier + total, prominent) OR a paused
 * approval gate (link to /approvals), framed by the rolled-up total cost.
 */
export function MissionOutcome({ state }: MissionOutcomeProps) {
  const { result } = state;
  const total = rollupCost(state.hops);
  const awarded = result.award != null;
  const paused = result.paused_gate != null;

  const accent = awarded ? COLORS.ok : paused ? COLORS.warn : COLORS.info;

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      className="relative overflow-hidden rounded-lg border p-4"
      style={{
        borderColor: withAlpha(accent, 0.4),
        background: `linear-gradient(160deg, ${withAlpha(accent, 0.08)}, transparent 70%)`,
        boxShadow: `0 0 32px -16px ${accent}`,
      }}
    >
      {/* top hairline in the verdict hue */}
      <span
        aria-hidden
        className="absolute inset-x-0 top-0 h-px"
        style={{
          background: `linear-gradient(to right, ${accent}, transparent 70%)`,
        }}
      />

      {awarded && result.award ? (
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <CheckSeal color={accent} />
              <span className="label-cap" style={{ color: accent }}>
                awarded
              </span>
            </div>
            <p className="mt-2 text-sm text-ink-muted">
              Orchestrator composed the run and recommended an award to
            </p>
            <p className="metric mt-0.5 text-lg font-semibold text-ink">
              {result.award.supplier_id}
            </p>
          </div>
          <div className="text-right">
            <span className="label-cap">award total</span>
            <p
              className="metric mt-1 text-3xl font-bold tracking-tight"
              style={{ color: accent }}
            >
              {fmtUsdFull(result.award.total_usd)}
            </p>
          </div>
        </div>
      ) : paused ? (
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <GateGlyph color={accent} />
              <span className="label-cap" style={{ color: accent }}>
                paused at gate
              </span>
            </div>
            <p className="mt-2 max-w-md text-sm text-ink-muted">
              Recommendation exceeds the agent&apos;s spend mandate. The run is
              paused durably at the{" "}
              <span className="metric text-ink">{result.paused_gate}</span> gate —
              a human must approve before it resumes.
            </p>
          </div>
          <Link
            href="/approvals"
            className="focus-ring inline-flex items-center gap-2 rounded-md border px-3.5 py-2 text-sm font-medium transition-colors"
            style={{
              borderColor: withAlpha(accent, 0.5),
              color: accent,
              background: withAlpha(accent, 0.1),
            }}
          >
            Open Gates
            <Arrow />
          </Link>
        </div>
      ) : (
        <div>
          <span className="label-cap" style={{ color: accent }}>
            {result.status}
          </span>
          <p className="mt-2 text-sm text-ink-muted">
            Mission completed with status{" "}
            <span className="metric text-ink">{result.status}</span>.
          </p>
        </div>
      )}

      {/* rollup footer */}
      <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-line pt-3">
        <Metric label="hops" value={String(state.hops.length)} />
        <Metric
          label="total cost"
          value={`$${total.toFixed(4)}`}
          color={COLORS.accent}
        />
        <Metric
          label="run"
          value={result.run_id}
          mono
          color={COLORS.inkMuted}
        />
        <div className="ml-auto">
          <Pill tone={awarded ? "ok" : paused ? "warn" : "info"}>
            {result.status}
          </Pill>
        </div>
      </div>

      {/* next-step links — this is where the journey continues */}
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line pt-3">
        <Link
          href={`/runs/${encodeURIComponent(result.run_id)}`}
          className="focus-ring inline-flex items-center gap-2 rounded-md border px-3.5 py-2 text-[13px] font-semibold transition-colors"
          style={{
            borderColor: withAlpha(COLORS.accent, 0.5),
            color: COLORS.accent,
            background: withAlpha(COLORS.accent, 0.1),
          }}
        >
          <TrailGlyph />
          View full audit trail
          <Arrow />
        </Link>
        {paused && (
          <Link
            href="/approvals"
            className="focus-ring inline-flex items-center gap-2 rounded-md border px-3.5 py-2 text-[13px] font-medium transition-colors"
            style={{
              borderColor: withAlpha(COLORS.warn, 0.5),
              color: COLORS.warn,
              background: withAlpha(COLORS.warn, 0.1),
            }}
          >
            Awaiting approval at {result.paused_gate}
            <Arrow />
          </Link>
        )}
      </div>
    </motion.div>
  );
}

function Metric({
  label,
  value,
  color = COLORS.ink,
  mono = false,
}: {
  label: string;
  value: string;
  color?: string;
  mono?: boolean;
}) {
  return (
    <div>
      <div className="label-cap">{label}</div>
      <div
        className={`${mono ? "metric truncate max-w-[14rem]" : "metric"} mt-0.5 text-sm font-semibold`}
        style={{ color }}
        title={value}
      >
        {value}
      </div>
    </div>
  );
}

function CheckSeal({ color }: { color: string }) {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
      <circle cx="9" cy="9" r="8" stroke={color} strokeWidth="1.4" opacity={0.5} />
      <path
        d="M5.5 9.2 8 11.5l4.5-5"
        stroke={color}
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function GateGlyph({ color }: { color: string }) {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
      <rect
        x="3.5"
        y="8"
        width="11"
        height="7"
        rx="1.4"
        stroke={color}
        strokeWidth="1.4"
      />
      <path
        d="M5.5 8V6a3.5 3.5 0 0 1 7 0v2"
        stroke={color}
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

function Arrow() {
  return (
    <svg width="14" height="10" viewBox="0 0 14 10" fill="none" aria-hidden>
      <path
        d="M1 5h11M9 1.5 12.5 5 9 8.5"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function TrailGlyph() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M3 4h10M3 8h10M3 12h6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}
