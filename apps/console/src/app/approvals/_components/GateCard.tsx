"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "motion/react";

import { Pill, SystemBadge } from "@/components/ui";
import { COLORS, withAlpha } from "@/lib/theme";
import {
  agentSystem,
  fmtAge,
  fmtClock,
  fmtUsdFull,
  gateMeta,
  moneyAtStake,
  type Approval,
  type Verdict,
} from "./types";

interface GateCardProps {
  approval: Approval;
  /** Decide the gate. Resolves when the POST returns; card then animates out. */
  onDecide: (id: number, approve: boolean) => Promise<void>;
  /** Index in the stack — staggers the entrance so cards cascade in. */
  index: number;
  /** Shared clock tick (ms) so every card's "waiting" age advances in lockstep. */
  now: number;
}

/**
 * GateCard — one durably-paused run awaiting a human verdict.
 *
 * The card foregrounds the MONEY at stake and frames the decision as resuming a
 * parked agent: a left "pause rail" glows amber while pending, the gate is a
 * status Pill, and Approve / Reject trigger a verdict-tinted resolve animation
 * (the card seals, then slides out) before the optimistic removal + next poll.
 */
export function GateCard({ approval: a, onDecide, index, now }: GateCardProps) {
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const meta = gateMeta(a.gate);
  const stake = moneyAtStake(a);
  const title = a.payload?.title ?? a.payload?.event_id ?? `gate #${a.id}`;
  const busy = verdict !== null;

  const resolvedColor =
    verdict === "approve"
      ? COLORS.ok
      : verdict === "reject"
        ? COLORS.danger
        : COLORS.warn;

  async function decide(v: Verdict) {
    if (busy) return;
    setVerdict(v); // flips the card into its sealed/resolving state immediately
    await onDecide(a.id, v === "approve");
    // The parent removes us from the list on success; AnimatePresence plays exit.
  }

  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{
        opacity: 0,
        x: verdict === "reject" ? -40 : 40,
        scale: 0.97,
        transition: { duration: 0.32, ease: [0.4, 0, 1, 1] },
      }}
      transition={{
        duration: 0.4,
        delay: index * 0.05,
        ease: [0.22, 1, 0.36, 1],
      }}
      className="panel relative overflow-hidden"
    >
      {/* left status rail — amber heartbeat while parked, verdict hue once decided */}
      <span
        aria-hidden
        className="absolute inset-y-0 left-0 w-[3px]"
        style={{
          background: resolvedColor,
          boxShadow: `0 0 14px -2px ${resolvedColor}`,
          opacity: busy ? 1 : 0.85,
        }}
      />
      {!busy && (
        <span
          aria-hidden
          className="absolute inset-y-0 left-0 w-[3px] animate-[pulse-dot_2.2s_ease-in-out_infinite]"
          style={{ background: COLORS.warn }}
        />
      )}

      {/* a sweep of verdict color washes across as the decision lands */}
      {busy && (
        <motion.span
          aria-hidden
          className="pointer-events-none absolute inset-0"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          style={{
            background: `linear-gradient(105deg, ${withAlpha(resolvedColor, 0.16)}, transparent 60%)`,
          }}
        />
      )}

      <div className="relative p-4 pl-5 sm:p-5 sm:pl-6">
        {/* ── header: gate + title + arrival ─────────────────────────────── */}
        <div className="flex flex-wrap items-start gap-x-3 gap-y-2">
          <Pill color={meta.color} className="shrink-0">
            <LockGlyph />
            {meta.label}
          </Pill>
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-[15px] font-semibold leading-snug text-ink">
              {title}
            </h3>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-ink-faint">
              <span className="metric">{a.payload?.event_id ?? "—"}</span>
              <span aria-hidden>·</span>
              <SystemBadge system={agentSystem(a.agent)} className="contents" />
              <span className="metric truncate text-ink-muted" title={a.agent ?? ""}>
                {a.agent ?? "agent"}
              </span>
            </div>
          </div>
          <div className="shrink-0 text-right">
            <div className="metric text-[11px] text-ink-muted">{fmtClock(a.ts)}</div>
            <div
              className="metric mt-0.5 text-[10px] tracking-wide"
              style={{ color: busy ? resolvedColor : COLORS.warn }}
            >
              {busy ? "deciding…" : fmtAge(a.ts, now)}
            </div>
          </div>
        </div>

        {/* ── the money at stake — the hero of the card ──────────────────── */}
        <div className="mt-4 flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
          <div className="flex items-end gap-5">
            <div>
              <div className="label-cap">
                {stake.firm ? "best bid" : "estimated value"}
              </div>
              <div className="metric mt-1 text-3xl font-bold tracking-tight text-ink sm:text-[2rem]">
                {fmtUsdFull(stake.amount)}
              </div>
              {stake.firm && stake.supplier && (
                <div className="metric mt-0.5 text-[11px] text-ink-faint">
                  → {stake.supplier}
                </div>
              )}
            </div>

            {/* tenant + run trace, mono and quiet */}
            <dl className="hidden border-l border-line pl-5 text-[11px] sm:block">
              <div className="flex items-baseline gap-2">
                <dt className="label-cap w-12">tenant</dt>
                <dd className="metric text-ink-muted">{a.tenant_id}</dd>
              </div>
              <div className="mt-1.5 flex items-baseline gap-2">
                <dt className="label-cap w-12">run</dt>
                <dd className="min-w-0">
                  <Link
                    href={`/runs/${encodeURIComponent(a.run_id)}`}
                    title={`See this run — ${a.run_id}`}
                    className="focus-ring metric block max-w-[12rem] truncate rounded text-ink-muted underline-offset-2 transition-colors hover:text-accent hover:underline"
                  >
                    {a.run_id} <span aria-hidden>↗</span>
                  </Link>
                </dd>
              </div>
            </dl>
          </div>

          {/* ── verdict controls ─────────────────────────────────────────── */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => decide("reject")}
              disabled={busy}
              className="focus-ring inline-flex items-center gap-1.5 rounded-md border px-3.5 py-2 text-[13px] font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40"
              style={{
                borderColor: withAlpha(COLORS.danger, 0.45),
                color: COLORS.danger,
                background:
                  verdict === "reject"
                    ? withAlpha(COLORS.danger, 0.2)
                    : withAlpha(COLORS.danger, 0.07),
              }}
            >
              <XGlyph />
              Reject
            </button>
            <button
              type="button"
              onClick={() => decide("approve")}
              disabled={busy}
              className="focus-ring inline-flex items-center gap-1.5 rounded-md border px-4 py-2 text-[13px] font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-40"
              style={{
                borderColor: withAlpha(COLORS.ok, 0.5),
                color: verdict === "approve" ? COLORS.base : COLORS.ok,
                background:
                  verdict === "approve"
                    ? COLORS.ok
                    : withAlpha(COLORS.ok, 0.12),
              }}
            >
              <CheckGlyph />
              Approve
            </button>
          </div>
        </div>

        {/* ── what this decision actually does — the "it resumes a run" wow ── */}
        <div className="mt-4 flex items-start gap-2 border-t border-line pt-3">
          <ResumeGlyph color={busy ? resolvedColor : meta.color} />
          <p className="text-[12px] leading-relaxed text-ink-faint">
            {busy ? (
              <>
                {verdict === "approve" ? (
                  <>
                    Approving — resuming the parked{" "}
                    <span className="metric text-ink-muted">{a.agent ?? "run"}</span>{" "}
                    run; it {meta.resumes}.
                  </>
                ) : (
                  <>
                    Rejecting — the run stays halted and the gate is recorded as
                    denied.
                  </>
                )}
              </>
            ) : (
              <>
                This run is{" "}
                <span style={{ color: COLORS.warn }}>paused durably</span> at the{" "}
                <span className="metric text-ink-muted">{a.gate}</span> gate.
                Approving {meta.resumes}.
              </>
            )}
          </p>
        </div>
      </div>
    </motion.li>
  );
}

/* ───────────────────────────── glyphs ──────────────────────────────────── */

function LockGlyph() {
  return (
    <svg width="9" height="9" viewBox="0 0 18 18" fill="none" aria-hidden>
      <rect x="3.5" y="8" width="11" height="7" rx="1.4" stroke="currentColor" strokeWidth="1.6" />
      <path d="M5.5 8V6a3.5 3.5 0 0 1 7 0v2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function CheckGlyph() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path d="M3.5 8.5 6.5 11.5l6-7" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function XGlyph() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function ResumeGlyph({ color }: { color: string }) {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden className="mt-px shrink-0">
      <path d="M5 3.5v9l7-4.5-7-4.5Z" stroke={color} strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  );
}
