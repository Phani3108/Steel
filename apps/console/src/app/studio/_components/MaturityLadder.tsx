"use client";

import { motion } from "motion/react";

import {
  AutonomyMeter,
  GaugeRing,
  Panel,
  Pill,
  SystemBadge,
} from "@/components/ui";
import { fetchMaturity, type MaturityRow } from "@/lib/api";
import { REFERENCE_AGENTS } from "@/lib/fleet";
import { systemHue, COLORS } from "@/lib/theme";
import { usePoll } from "@/lib/usePoll";

const POLL_MS = 15_000;

/**
 * A reference maturity table derived from the reference fleet — shown when
 * GET /maturity is unreachable so the governance story always reads. Each agent
 * sits at its current level; a couple have proven scorecards that earn a
 * promotion, one has none yet (the honest "not eligible" case).
 */
const REFERENCE_MATURITY: MaturityRow[] = REFERENCE_AGENTS.map((a, i) => {
  const level = a.autonomy_level ?? 1;
  // Deterministic, plausible pass-rates so the dials look alive offline.
  const passRates = [0.96, 0.91, 0.88, 0.0, 0.93, 0.84];
  const pass = passRates[i % passRates.length];
  const hasScorecard = pass > 0;
  const promote = hasScorecard && pass >= 0.9 && level < 5;
  return {
    agent: a.name,
    current_level: level,
    has_scorecard: hasScorecard,
    pass_rate: hasScorecard ? pass : undefined,
    promote,
    to_level: promote ? level + 1 : undefined,
    reasons: promote
      ? [`pass-rate ${(pass * 100).toFixed(0)}% ≥ 90% gate`, "0 policy violations"]
      : hasScorecard
        ? [`pass-rate ${(pass * 100).toFixed(0)}% below 90% gate`]
        : ["no scorecard on file"],
  };
});

/** Map a maturity row's agent name back to its system hue, via the fleet. */
function systemOf(agent: string): string {
  const part = REFERENCE_AGENTS.find((a) => a.name === agent);
  return part?.system ?? "NETWORK";
}

/**
 * SECTION 2 — "Maturity ladder" (eval-gated autonomy).
 *
 * Every agent is a row: which system it belongs to, the autonomy level it
 * currently holds, the scorecard pass-rate that earned it, and a promotion
 * verdict. The governance point lives in the verdict copy: promotion is PROVEN
 * by scorecards, never edited in.
 */
export function MaturityLadder() {
  const { data, loaded } = usePoll<MaturityRow[]>(fetchMaturity, POLL_MS);

  const live = data && data.length > 0;
  const rows = live ? data : REFERENCE_MATURITY;
  const usingReference = !live;

  const promotable = rows.filter((r) => r.promote).length;

  return (
    <Panel
      accent="SAFETY"
      title="maturity ladder"
      action={
        <span
          className="metric text-[10px] tracking-wide"
          style={{ color: promotable ? COLORS.accent : COLORS.inkFaint }}
        >
          {promotable > 0
            ? `${promotable} earning promotion`
            : "ladder stable"}
        </span>
      }
    >
      <p className="mb-4 max-w-2xl text-[12px] leading-relaxed text-ink-faint">
        Autonomy is earned, not assigned. An agent climbs a level only when its
        jai-dyno scorecards clear the gate — no scorecard, no ship; below target,
        no promotion. This ladder is read directly off the evals, never edited.
      </p>

      <div className="divide-y divide-line">
        {rows.map((row, i) => (
          <MaturityItem
            key={row.agent}
            row={row}
            delay={loaded ? 0 : i * 0.04}
          />
        ))}
      </div>

      {usingReference && (
        <p className="mt-4 text-[11px] text-ink-faint">
          <span style={{ color: COLORS.autonomy }}>● </span>
          live maturity feed offline — showing the reference ladder.
        </p>
      )}
    </Panel>
  );
}

function MaturityItem({ row, delay }: { row: MaturityRow; delay: number }) {
  const hue = systemHue(systemOf(row.agent));
  const pass = row.pass_rate ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
      className="flex flex-wrap items-center gap-x-5 gap-y-3 py-3.5"
    >
      {/* identity */}
      <div className="min-w-[200px] flex-1">
        <div className="flex items-center gap-2">
          <span className="metric text-sm text-ink">{row.agent}</span>
        </div>
        <div className="mt-1.5">
          <SystemBadge system={systemOf(row.agent)} />
        </div>
      </div>

      {/* current autonomy */}
      <div className="flex min-w-[150px] flex-col gap-1">
        <span className="label-cap">holds</span>
        <AutonomyMeter level={row.current_level} size="sm" />
      </div>

      {/* scorecard gauge */}
      <div className="flex min-w-[84px] justify-center">
        {row.has_scorecard ? (
          <GaugeRing
            value={pass}
            size={68}
            thickness={6}
            caption="pass"
          />
        ) : (
          <div className="flex h-[68px] w-[68px] flex-col items-center justify-center rounded-full border border-dashed border-line">
            <span className="text-[10px] text-ink-ghost">no</span>
            <span className="text-[10px] text-ink-ghost">card</span>
          </div>
        )}
      </div>

      {/* verdict */}
      <div className="min-w-[200px] flex-1">
        <Verdict row={row} hue={hue} />
      </div>
    </motion.div>
  );
}

function Verdict({ row, hue }: { row: MaturityRow; hue: string }) {
  if (!row.has_scorecard) {
    return (
      <div>
        <Pill tone="neutral">no scorecard yet</Pill>
        <p className="mt-1.5 text-[11px] leading-relaxed text-ink-faint">
          Not eligible to promote until evals run. This is the honest state —
          unproven agents do not advance.
        </p>
      </div>
    );
  }

  if (row.promote && row.to_level) {
    const label = LEVEL_LABELS[row.to_level] ?? "";
    return (
      <div>
        <span
          className="metric text-sm font-semibold"
          style={{ color: COLORS.accent }}
        >
          earns L{row.to_level}
          {label && <span className="text-ink-muted"> · {label}</span>}
        </span>
        <ul className="mt-1.5 space-y-0.5">
          {(row.reasons ?? []).map((r, i) => (
            <li
              key={i}
              className="flex items-start gap-1.5 text-[11px] text-ink-faint"
            >
              <span style={{ color: COLORS.ok }}>✓</span>
              <span>{r}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  // Has a scorecard but isn't clearing the gate (or already at the ceiling).
  const atCeiling = row.current_level >= 5;
  return (
    <div>
      <Pill color={hue}>{atCeiling ? "at ceiling · L5" : "holds level"}</Pill>
      <ul className="mt-1.5 space-y-0.5">
        {(row.reasons ?? []).map((r, i) => (
          <li
            key={i}
            className="flex items-start gap-1.5 text-[11px] text-ink-faint"
          >
            <span className="text-ink-ghost">·</span>
            <span>{r}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const LEVEL_LABELS: Record<number, string> = {
  1: "advise",
  2: "draft",
  3: "act · approval",
  4: "act · notify",
  5: "autonomous",
};
