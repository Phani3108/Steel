"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";

import { EmptyState, Panel, SectionHeader, Spinner } from "@/components/ui";
import { JourneyBar } from "@/components/JourneyBar";
import { COLORS, withAlpha } from "@/lib/theme";
import { API_BASE, startSampleProcurement } from "@/lib/api";
import { usePoll } from "@/lib/usePoll";

import { GateCard } from "./_components/GateCard";
import { fmtUsdFull, moneyAtStake, type Approval } from "./_components/types";

/** A resolved gate, kept on screen as a confirmation that links to its run. */
interface Confirmation {
  id: number;
  approve: boolean;
  runId: string;
  gate: string;
}

async function fetchApprovals(): Promise<Approval[]> {
  const res = await fetch(`${API_BASE}/approvals`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET /approvals -> ${res.status}`);
  return (await res.json()) as Approval[];
}

/**
 * /approvals — GATES.
 *
 * The human-in-the-loop inbox for jai-brakes. Every row is an agent run that hit
 * a policy gate (over-mandate award, RFx publish) and PAUSED ITSELF DURABLY mid-
 * flight; it is sitting in Postgres waiting on a verdict. Approving or rejecting
 * here is what lets the parked run resume — that's the story the page tells.
 *
 * Polls GET /approvals (~3s). Decisions POST /approvals/{id}/decide and are
 * optimistically removed (a verdict-tinted resolve animation), confirmed by the
 * next poll. Falls back to a quiet "telemetry offline" note, never a crash.
 */
export default function ApprovalsPage() {
  const [decided, setDecided] = useState<number[]>([]);
  const [confirmations, setConfirmations] = useState<Confirmation[]>([]);
  const [now, setNow] = useState(() => Date.now());
  const { data, offline, loaded } = usePoll<Approval[]>(fetchApprovals, 3000);

  // Shared clock so each card's "Nm waiting" age advances together, once a second.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const decide = useCallback(
    async (id: number, approve: boolean): Promise<void> => {
      // Snapshot the run we're resolving so the confirmation can deep-link to it.
      const row = (data ?? []).find((a) => a.id === id);
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
      } finally {
        // Optimistic: drop it now; the next poll confirms it's gone server-side.
        setDecided((d) => (d.includes(id) ? d : [...d, id]));
        if (row?.run_id) {
          setConfirmations((c) => [
            { id, approve, runId: row.run_id, gate: row.gate },
            ...c.filter((x) => x.id !== id),
          ]);
        }
      }
    },
    [data],
  );

  const dismissConfirmation = useCallback((id: number) => {
    setConfirmations((c) => c.filter((x) => x.id !== id));
  }, []);

  // Hide anything we've optimistically decided. The `decided` set only ever needs
  // ids the server is *still* returning (those are the in-flight removals); once a
  // poll drops an id it's gone from `data` regardless, so we never have to prune.
  const rows = (data ?? []).filter((a) => !decided.includes(a.id));

  const totalAtStake = rows.reduce(
    (sum, a) => sum + (moneyAtStake(a).amount ?? 0),
    0,
  );

  return (
    <div className="space-y-6">
      <SectionHeader
        kicker="cockpit · human-in-the-loop"
        title="Gates"
        subtitle="Runs that hit a policy gate pause themselves durably and wait here. Your verdict is what resumes a parked agent — approve to let it proceed, reject to keep it halted."
        action={
          offline && loaded ? (
            <span
              className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px]"
              style={{
                borderColor: withAlpha(COLORS.autonomy, 0.35),
                color: COLORS.autonomy,
                background: withAlpha(COLORS.autonomy, 0.1),
              }}
              title="GET /approvals is unreachable — showing the last known queue."
            >
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{ background: COLORS.autonomy }}
              />
              live telemetry offline
            </span>
          ) : (
            <CountBadge count={rows.length} totalUsd={totalAtStake} />
          )
        }
      />

      <Panel accent="accent" title="procurement journey · you are here">
        <JourneyBar current="approve" size="sm" linked />
      </Panel>

      {/* confirmations — a decided gate stays visible just long enough to trace it */}
      <AnimatePresence initial={false}>
        {confirmations.map((c) => (
          <ConfirmationStrip
            key={c.id}
            confirmation={c}
            onDismiss={() => dismissConfirmation(c.id)}
          />
        ))}
      </AnimatePresence>

      {!loaded ? (
        <div className="panel telem-grid">
          <SkeletonStack />
        </div>
      ) : rows.length === 0 ? (
        <div className="panel telem-grid">
          <EmptyState
            icon={<ClearGlyph />}
            title="No runs are waiting on you"
            hint={
              <>
                Approvals appear here when an agent run pauses for a human
                decision — an over-mandate award or an RFx publish. Your verdict
                is what resumes the parked run.
              </>
            }
            action={<SampleProcurementButton />}
          />
        </div>
      ) : (
        <motion.ul layout className="space-y-3.5">
          <AnimatePresence mode="popLayout" initial={false}>
            {rows.map((a, i) => (
              <GateCard
                key={a.id}
                approval={a}
                onDecide={decide}
                index={i}
                now={now}
              />
            ))}
          </AnimatePresence>
        </motion.ul>
      )}
    </div>
  );
}

/** Live pending count + aggregate stake, rendered in the masthead action slot. */
function CountBadge({ count, totalUsd }: { count: number; totalUsd: number }) {
  const live = count > 0;
  const color = live ? COLORS.warn : COLORS.ok;
  return (
    <div className="flex items-center gap-3">
      {count > 0 && (
        <span className="metric hidden text-[11px] text-ink-faint sm:inline">
          {fmtUsdFull(totalUsd)} at stake
        </span>
      )}
      <span
        className="inline-flex items-center gap-2 rounded-full border px-3 py-1"
        style={{
          borderColor: withAlpha(color, 0.4),
          background: withAlpha(color, 0.1),
        }}
      >
        <span className="relative inline-flex h-2 w-2" aria-hidden>
          {live && (
            <span
              className="absolute inset-0 rounded-full opacity-60 animate-[pulse-dot_1.8s_ease-in-out_infinite]"
              style={{ background: color }}
            />
          )}
          <span
            className="relative inline-block h-2 w-2 rounded-full"
            style={{ background: color, boxShadow: `0 0 8px -1px ${color}` }}
          />
        </span>
        <span className="metric text-[13px] font-semibold" style={{ color }}>
          {count}
        </span>
        <span className="label-cap">{count === 1 ? "gate" : "gates"}</span>
      </span>
    </div>
  );
}

/**
 * A decided gate, surfaced as a confirmation that the parked run resumed — with a
 * deep-link to its full audit trail so the operator can follow it onward.
 */
function ConfirmationStrip({
  confirmation: c,
  onDismiss,
}: {
  confirmation: Confirmation;
  onDismiss: () => void;
}) {
  const color = c.approve ? COLORS.ok : COLORS.danger;
  const verb = c.approve ? "approved" : "rejected";
  const outcome = c.approve
    ? "run resumed"
    : "run stays halted";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0, marginBottom: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border px-4 py-2.5"
      style={{
        borderColor: withAlpha(color, 0.4),
        background: withAlpha(color, 0.08),
      }}
    >
      <span
        className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full"
        style={{ background: withAlpha(color, 0.18), color }}
        aria-hidden
      >
        {c.approve ? (
          <svg width="11" height="11" viewBox="0 0 16 16" fill="none">
            <path
              d="M3.5 8.5 6.5 11.5l6-7"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        ) : (
          <svg width="10" height="10" viewBox="0 0 16 16" fill="none">
            <path
              d="M4 4l8 8M12 4l-8 8"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
            />
          </svg>
        )}
      </span>
      <span className="text-[13px] text-ink">
        <span className="font-semibold" style={{ color }}>
          {verb}
        </span>{" "}
        — {outcome} at the{" "}
        <span className="metric text-ink-muted">{c.gate}</span> gate.
      </span>
      <Link
        href={`/runs/${encodeURIComponent(c.runId)}`}
        className="focus-ring metric ml-auto rounded text-[12px] text-accent underline-offset-2 transition-colors hover:underline"
      >
        View run detail →
      </Link>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="dismiss"
        className="focus-ring rounded p-1 text-ink-faint transition-colors hover:text-ink"
      >
        <svg width="11" height="11" viewBox="0 0 16 16" fill="none" aria-hidden>
          <path
            d="M4 4l8 8M12 4l-8 8"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
        </svg>
      </button>
    </motion.div>
  );
}

/**
 * One-click "produce a gate to act on" — launches a sample procurement; an
 * over-mandate run lands a fresh approval in this very inbox (next poll picks it
 * up). On failure it just falls quiet — this is a convenience, not a load-bearing
 * path.
 */
function SampleProcurementButton() {
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  async function run() {
    if (busy) return;
    setBusy(true);
    try {
      await startSampleProcurement();
      setDone(true);
    } catch {
      /* offline — nothing to surface; the empty state stays as-is */
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <p className="metric text-[12px] text-ok">
        sample launched — watch for a gate to appear above ↑
      </p>
    );
  }

  return (
    <button
      type="button"
      onClick={run}
      disabled={busy}
      className="focus-ring inline-flex items-center gap-2 rounded-md border px-3.5 py-2 text-[13px] font-medium transition-colors disabled:opacity-50"
      style={{
        borderColor: withAlpha(COLORS.accent, 0.5),
        color: COLORS.accent,
        background: withAlpha(COLORS.accent, 0.1),
      }}
    >
      {busy ? (
        <Spinner size={14} label="launching…" />
      ) : (
        <>
          <PlayGlyph />
          Run a sample procurement
        </>
      )}
    </button>
  );
}

function PlayGlyph() {
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M5 3.5v9l7-4.5-7-4.5Z"
        fill="currentColor"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** A calm loading shimmer while the first poll is in flight. */
function SkeletonStack() {
  return (
    <div className="space-y-3 p-4">
      {[0, 1].map((i) => (
        <div
          key={i}
          className="h-28 rounded-lg border border-line bg-panel-2"
          style={{
            backgroundImage:
              "linear-gradient(100deg, transparent 20%, rgb(255 255 255 / 0.03) 50%, transparent 80%)",
            backgroundSize: "200% 100%",
          }}
        >
          <span
            className="block h-full w-full rounded-lg animate-[shimmer_1.6s_linear_infinite]"
            style={{
              backgroundImage:
                "linear-gradient(100deg, transparent 30%, rgb(34 211 238 / 0.04) 50%, transparent 70%)",
              backgroundSize: "200% 100%",
            }}
          />
        </div>
      ))}
    </div>
  );
}

function ClearGlyph() {
  return (
    <svg width="34" height="34" viewBox="0 0 32 32" fill="none" aria-hidden>
      <circle cx="16" cy="16" r="13" stroke={COLORS.inkGhost} strokeWidth="1.4" />
      <path
        d="M10.5 16.5 14.5 20.5l7.5-9"
        stroke={COLORS.ok}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={0.8}
      />
    </svg>
  );
}
