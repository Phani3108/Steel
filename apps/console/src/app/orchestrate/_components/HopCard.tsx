"use client";

import Link from "next/link";
import { motion } from "motion/react";

import { Chip, Pill, SystemBadge } from "@/components/ui";
import { fmtUsd } from "@/lib/api";
import { COLORS, systemHue, withAlpha } from "@/lib/theme";
import { agentMeta } from "./agents";
import type { StagedHop } from "./demo";

interface HopCardProps {
  hop: StagedHop;
  index: number;
  /** True for the last hop in the trace (drops the connecting rail tail). */
  isLast: boolean;
}

/**
 * One hop in the mission timeline: the receiving agent (SystemBadge), the skill
 * invoked, an ok/denied Pill, a one-line summary, and the cost — anchored on a
 * glowing rail node that pulses while running and locks in when done.
 */
export function HopCard({ hop, index, isLast }: HopCardProps) {
  const to = agentMeta(hop.to_agent);
  const from = agentMeta(hop.from_agent);
  const hue = systemHue(to.system);
  const running = hop.phase === "running";
  const denied = !hop.ok;

  const nodeColor = denied ? COLORS.danger : running ? COLORS.accent : hue;

  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.34, ease: [0.22, 1, 0.36, 1] }}
      className="relative pb-4 pl-8 last:pb-0"
    >
      {/* connecting rail */}
      {!isLast && (
        <span
          aria-hidden
          className="absolute left-[7px] top-4 h-full w-px"
          style={{ background: withAlpha(COLORS.lineStrong, 0.9) }}
        />
      )}

      {/* rail node */}
      <span
        aria-hidden
        className="absolute left-0 top-[3px] flex h-[15px] w-[15px] items-center justify-center"
      >
        {running && (
          <motion.span
            className="absolute inset-0 rounded-full"
            style={{ background: withAlpha(nodeColor, 0.5) }}
            animate={{ scale: [1, 1.9], opacity: [0.6, 0] }}
            transition={{ duration: 1.1, repeat: Infinity, ease: "easeOut" }}
          />
        )}
        <span
          className="relative h-[9px] w-[9px] rounded-full"
          style={{
            background: nodeColor,
            boxShadow: `0 0 8px -1px ${nodeColor}`,
          }}
        />
      </span>

      {/* hop body */}
      <div
        className="rounded-md border bg-base-2/70 px-3 py-2.5 transition-colors"
        style={{
          borderColor: denied
            ? withAlpha(COLORS.danger, 0.4)
            : running
              ? withAlpha(COLORS.accent, 0.35)
              : "var(--line)",
          boxShadow: running ? `0 0 18px -10px ${COLORS.accent}` : "none",
        }}
      >
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5">
          <span className="metric text-[10px] text-ink-ghost">
            {String(index + 1).padStart(2, "0")}
          </span>
          <SystemBadge system={to.system} dotOnly />
          <Link
            href="/network"
            title={`See ${to.label} in the live agent network`}
            className="focus-ring rounded text-sm font-medium text-ink underline-offset-2 transition-colors hover:text-accent hover:underline"
          >
            {to.label}
          </Link>
          <Chip color={hue} className="ml-0.5">
            {hop.skill_id}
          </Chip>

          <div className="ml-auto flex items-center gap-2">
            <span className="metric text-[11px] text-ink-faint">
              {fmtUsd(hop.cost_usd)}
            </span>
            {running ? (
              <Pill tone="accent">
                <motion.span
                  className="inline-block h-1.5 w-1.5 rounded-full bg-accent"
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                />
                running
              </Pill>
            ) : denied ? (
              <Pill tone="danger">denied</Pill>
            ) : (
              <Pill tone="ok">ok</Pill>
            )}
          </div>
        </div>

        <p className="mt-1.5 text-[13px] leading-relaxed text-ink-muted">
          {hop.summary}
        </p>

        <div className="mt-1 flex items-center gap-1.5 text-[10px] text-ink-ghost">
          <span className="metric">{from.label}</span>
          <Arrow />
          <span className="metric">{to.label}</span>
        </div>
      </div>
    </motion.li>
  );
}

function Arrow() {
  return (
    <svg width="14" height="8" viewBox="0 0 14 8" fill="none" aria-hidden>
      <path
        d="M0 4h12M9 1.5 12.5 4 9 6.5"
        stroke="currentColor"
        strokeWidth="1.1"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
