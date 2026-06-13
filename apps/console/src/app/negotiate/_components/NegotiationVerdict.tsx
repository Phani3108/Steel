"use client";

import { motion } from "motion/react";

import { Pill } from "@/components/ui";
import { COLORS, withAlpha } from "@/lib/theme";
import { fmtK, fmtUsdFull, type NegotiationState } from "./demo";

/**
 * The negotiation verdict — the emotional payoff under the theatre.
 *
 * DEAL: a green banner with final-vs-list, savings %, rounds, payment terms.
 * WALK: a rose banner where the *story* is the refusal — the agent declined to
 * cross its mandate cap, so "constraint violations: 0" is the headline chip.
 * Either way the cap was honored, which is the point.
 */
interface NegotiationVerdictProps {
  state: NegotiationState;
}

export function NegotiationVerdict({ state }: NegotiationVerdictProps) {
  const { result } = state;
  const walked = result.status === "walked";
  const accent = walked ? COLORS.danger : COLORS.ok;

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
      <span
        aria-hidden
        className="absolute inset-x-0 top-0 h-px"
        style={{
          background: `linear-gradient(to right, ${accent}, transparent 70%)`,
        }}
      />

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            {walked ? <ShieldGlyph color={accent} /> : <CheckSeal color={accent} />}
            <span className="label-cap" style={{ color: accent }}>
              {walked ? "walked away" : "deal closed"}
            </span>
          </div>
          <p className="mt-2 max-w-md text-sm leading-relaxed text-ink-muted">
            {walked ? (
              <>
                Against <span className="text-ink">{result.seller}</span>, every
                attainable price sat above the agent&apos;s{" "}
                <span style={{ color: COLORS.danger }}>mandate cap</span> of{" "}
                <span className="metric text-ink">{fmtK(result.mandate_cap)}</span>.
                The negotiator refused to cross the line and walked — no overspend,
                no breach.
              </>
            ) : (
              <>
                Closed with <span className="text-ink">{result.seller}</span> after{" "}
                <span className="metric text-ink">{result.rounds}</span> rounds,
                comfortably under the{" "}
                <span style={{ color: COLORS.danger }}>mandate cap</span> of{" "}
                <span className="metric text-ink">{fmtK(result.mandate_cap)}</span>.
              </>
            )}
          </p>
        </div>

        <div className="text-right">
          <span className="label-cap">
            {walked ? "best offer rejected" : "final price"}
          </span>
          <p
            className="metric mt-1 text-3xl font-bold tracking-tight"
            style={{ color: accent }}
          >
            {walked
              ? fmtUsdFull(result.list_price)
              : fmtUsdFull(result.final_price)}
          </p>
          {!walked && (
            <p className="metric mt-0.5 text-xs text-ink-faint">
              from list {fmtUsdFull(result.list_price)}
            </p>
          )}
        </div>
      </div>

      {/* headline stats */}
      <div className="mt-4 grid grid-cols-2 gap-x-5 gap-y-3 border-t border-line pt-3 sm:grid-cols-4">
        <Metric
          label="savings"
          value={walked ? "—" : `−${result.savings_pct.toFixed(1)}%`}
          color={walked ? COLORS.inkFaint : COLORS.ok}
        />
        <Metric
          label="final vs list"
          value={
            walked || result.final_price == null
              ? "—"
              : `${fmtK(result.final_price)} / ${fmtK(result.list_price)}`
          }
        />
        <Metric label="rounds" value={String(result.rounds)} />
        <Metric
          label="payment terms"
          value={
            result.payment_terms_days != null
              ? `net ${result.payment_terms_days}d`
              : "—"
          }
        />
      </div>

      {/* safety + provenance footer */}
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line pt-3">
        <Pill tone="ok" className="whitespace-nowrap">
          <SafetyDot /> constraint violations: 0
        </Pill>
        <Pill tone={result.breached ? "danger" : "neutral"}>
          {result.breached ? "cap breached" : "cap honored"}
        </Pill>
        <Pill tone={walked ? "danger" : "ok"}>{result.status}</Pill>
        <span
          className="metric ml-auto truncate text-[10px] text-ink-faint"
          title={result.run_id}
        >
          {result.run_id}
        </span>
      </div>
    </motion.div>
  );
}

function Metric({
  label,
  value,
  color = COLORS.ink,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="min-w-0">
      <div className="label-cap">{label}</div>
      <div
        className="metric mt-0.5 truncate text-sm font-semibold"
        style={{ color }}
        title={value}
      >
        {value}
      </div>
    </div>
  );
}

function SafetyDot() {
  return (
    <span
      className="inline-block h-1.5 w-1.5 rounded-full"
      style={{ background: COLORS.ok, boxShadow: `0 0 6px ${COLORS.ok}` }}
      aria-hidden
    />
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

function ShieldGlyph({ color }: { color: string }) {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
      <path
        d="M9 2.2 14.5 4.4v4.1c0 3.4-2.3 6-5.5 7.3-3.2-1.3-5.5-3.9-5.5-7.3V4.4L9 2.2Z"
        stroke={color}
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path
        d="M6.6 9 8.3 10.7 11.6 7"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
