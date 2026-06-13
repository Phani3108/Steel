"use client";

import { AnimatePresence, motion } from "motion/react";

import { COLORS, withAlpha } from "@/lib/theme";
import { fmtK, type NegotiationState } from "./demo";

/**
 * The transcript log — a compact, rolling textual record of each round that
 * reveals in lockstep with the theatre. Buyer offers in accent, seller counters
 * in rose, the action verb spelled out so the bargaining reads clearly.
 */
interface TranscriptLogProps {
  state: NegotiationState;
}

const ACTION_LABEL: Record<string, string> = {
  counter_up: "buyer raises · seller holds",
  accept_counter: "buyer accepts counter",
  seller_accepts: "seller accepts",
};

export function TranscriptLog({ state }: TranscriptLogProps) {
  const { result, revealed } = state;
  const rows = result.transcript.slice(0, revealed);

  return (
    <div className="flex flex-col gap-1.5">
      <AnimatePresence initial={false}>
        {rows.map((t) => {
          const accepts = t.action === "seller_accepts" || t.action === "accept_counter";
          return (
            <motion.div
              key={t.round}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
              className="flex items-center gap-3 rounded-md border px-2.5 py-1.5"
              style={{
                borderColor: accepts
                  ? withAlpha(COLORS.ok, 0.35)
                  : "var(--line)",
                background: accepts
                  ? withAlpha(COLORS.ok, 0.06)
                  : "var(--base-2)",
              }}
            >
              <span className="metric text-[10px] text-ink-ghost">
                R{t.round}
              </span>
              <span className="metric text-xs font-semibold" style={{ color: COLORS.accent }}>
                {fmtK(t.offer)}
              </span>
              <Arrows accepts={accepts} />
              <span className="metric text-xs font-semibold" style={{ color: COLORS.danger }}>
                {fmtK(t.counter)}
              </span>
              <span className="ml-auto truncate text-[10px] text-ink-faint">
                {ACTION_LABEL[t.action] ?? t.action}
              </span>
            </motion.div>
          );
        })}
      </AnimatePresence>

      {rows.length === 0 && (
        <p className="py-2 text-center text-[11px] text-ink-faint">
          opening offers…
        </p>
      )}
    </div>
  );
}

function Arrows({ accepts }: { accepts: boolean }) {
  const c = accepts ? COLORS.ok : COLORS.inkFaint;
  return (
    <svg width="22" height="10" viewBox="0 0 22 10" fill="none" aria-hidden className="shrink-0">
      {/* buyer up-arrow */}
      <path d="M5 8 5 2M3 4l2-2 2 2" stroke={COLORS.accent} strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
      {/* convergence tie */}
      <path d="M8 5h6" stroke={withAlpha(c, 0.7)} strokeWidth="1" strokeDasharray={accepts ? undefined : "2 2"} />
      {/* seller down-arrow */}
      <path d="M17 2 17 8M15 6l2 2 2-2" stroke={COLORS.danger} strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
