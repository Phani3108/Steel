"use client";

import Link from "next/link";
import { motion } from "motion/react";

import { Chip } from "@/components/ui";
import { COLORS, withAlpha } from "@/lib/theme";
import { fmtUsd, type ChatReply, type ChatCitation } from "@/lib/api";

export interface Turn {
  who: "user" | "agent";
  text: string;
  reply?: ChatReply;
  /** True only for the local "control plane unreachable" notice. */
  transportError?: boolean;
}

interface MessageBubbleProps {
  turn: Turn;
}

const ENTRANCE = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.32, ease: [0.22, 1, 0.36, 1] as const },
};

/** Compact source glyph keyed off the citation's source_type. */
function citationColor(sourceType: string): string {
  const t = sourceType.toLowerCase();
  if (t.includes("supplier")) return COLORS.accent;
  if (t.includes("contract")) return COLORS.info;
  if (t.includes("policy")) return COLORS.autonomy;
  if (t.includes("news")) return COLORS.warn;
  if (t.includes("item") || t.includes("catalog")) return COLORS.ok;
  return COLORS.inkMuted;
}

function Citations({ citations }: { citations: ChatCitation[] }) {
  if (citations.length === 0) return null;
  return (
    <div className="mt-3 border-t border-line/60 pt-2.5">
      <div className="label-cap mb-1.5">
        sources · {citations.length}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {citations.slice(0, 10).map((c, i) => (
          <Chip
            key={`${c.source_id}-${i}`}
            color={citationColor(c.source_type)}
            title={c.snippet}
          >
            {c.source_type}:{c.source_id}
          </Chip>
        ))}
        {citations.length > 10 && (
          <span className="metric self-center text-[10px] text-ink-faint">
            +{citations.length - 10}
          </span>
        )}
      </div>
    </div>
  );
}

function AnswerFooter({ reply }: { reply: ChatReply }) {
  return (
    <div className="mt-2.5 flex items-center gap-2 text-[10px]">
      <span
        className="metric text-ink-faint"
        title="Modeled from real per-model rates × real token counts — no live API spend."
      >
        modeled cost{" "}
        <span className="text-ink-muted">{fmtUsd(reply.cost_usd)}</span>
      </span>
      <span className="text-ink-ghost" aria-hidden>
        ·
      </span>
      <Link
        href={`/runs/${encodeURIComponent(reply.run_id)}`}
        title={`Inspect the full audit trail for ${reply.run_id}`}
        className="focus-ring metric inline-flex items-center gap-1 rounded text-ink-faint underline-offset-2 transition-colors hover:text-accent hover:underline"
      >
        {reply.run_id}
        <span className="tracking-wider text-ink-ghost">trace &rarr;</span>
      </Link>
    </div>
  );
}

function RefusalGlyph() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 16 16"
      className="h-3.5 w-3.5 shrink-0"
      fill="none"
    >
      <circle cx="8" cy="8" r="6.2" stroke="currentColor" strokeWidth="1.2" />
      <path
        d="M5.5 5.5 10.5 10.5"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </svg>
  );
}

/**
 * MessageBubble — one turn in the conversation. User turns sit right, accented;
 * agent answers sit left on a panel surface with citation chips and a cost/run
 * footer. Refusals are styled as a distinct amber alert — the visible proof that
 * permission enforcement runs below the model.
 */
export function MessageBubble({ turn }: MessageBubbleProps) {
  if (turn.who === "user") {
    return (
      <motion.div {...ENTRANCE} className="flex justify-end pl-10">
        <div
          className="max-w-[80%] rounded-lg rounded-br-sm px-3.5 py-2.5 text-sm leading-relaxed text-accent-ink"
          style={{
            background: `linear-gradient(135deg, ${COLORS.accent}, ${withAlpha(
              COLORS.accent,
              0.82,
            )})`,
          }}
        >
          {turn.text}
        </div>
      </motion.div>
    );
  }

  const refused = turn.reply?.refused ?? false;
  const transportError = turn.transportError ?? false;

  if (refused) {
    return (
      <motion.div {...ENTRANCE} className="flex justify-start pr-10">
        <div
          className="max-w-[85%] rounded-lg rounded-bl-sm border px-3.5 py-3"
          style={{
            background: withAlpha(COLORS.warn, 0.08),
            borderColor: withAlpha(COLORS.warn, 0.45),
          }}
        >
          <div
            className="mb-1.5 flex items-center gap-1.5"
            style={{ color: COLORS.warn }}
          >
            <RefusalGlyph />
            <span className="label-cap" style={{ color: COLORS.warn }}>
              permission denied
            </span>
          </div>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">
            {turn.text}
          </p>
          <p className="mt-2 text-[11px] leading-relaxed text-ink-faint">
            This persona isn&rsquo;t authorized for that. Switch role above to a
            wider mandate, or rephrase within scope.
          </p>
          {turn.reply && <AnswerFooter reply={turn.reply} />}
        </div>
      </motion.div>
    );
  }

  if (transportError) {
    return (
      <motion.div {...ENTRANCE} className="flex justify-start pr-10">
        <div
          className="max-w-[85%] rounded-lg rounded-bl-sm border px-3.5 py-3"
          style={{
            background: withAlpha(COLORS.danger, 0.07),
            borderColor: withAlpha(COLORS.danger, 0.4),
          }}
        >
          <div
            className="mb-1.5 flex items-center gap-1.5"
            style={{ color: COLORS.danger }}
          >
            <RefusalGlyph />
            <span className="label-cap" style={{ color: COLORS.danger }}>
              control plane offline
            </span>
          </div>
          <p className="text-sm leading-relaxed text-ink-muted">{turn.text}</p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div {...ENTRANCE} className="flex justify-start pr-10">
      <div className="panel-2 max-w-[85%] px-3.5 py-3">
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">
          {turn.text}
        </p>
        {turn.reply && <Citations citations={turn.reply.citations} />}
        {turn.reply && <AnswerFooter reply={turn.reply} />}
      </div>
    </motion.div>
  );
}
