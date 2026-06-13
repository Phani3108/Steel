"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { Fragment } from "react";

import { COLORS, withAlpha } from "@/lib/theme";

/**
 * JourneyBar — the procurement journey, made visible. Five steps on a rail:
 *
 *   Intake → Orchestrate → Approve → Award → Audit
 *
 * `current` highlights the active step (accent); everything before it is treated
 * as completed (filled). Used small + quiet on Mission / Gates / Audit, and large
 * + animated with live counts on Home (each step links to its screen).
 */

export type JourneyStep =
  | "intake"
  | "orchestrate"
  | "approve"
  | "award"
  | "audit";

interface StepDef {
  key: JourneyStep;
  label: string;
  href: string;
  /** One-line "what happens here" shown under the label on the large variant. */
  blurb: string;
}

const STEPS: StepDef[] = [
  { key: "intake", label: "Intake", href: "/orchestrate", blurb: "a request arrives" },
  {
    key: "orchestrate",
    label: "Orchestrate",
    href: "/orchestrate",
    blurb: "agents source & negotiate",
  },
  { key: "approve", label: "Approve", href: "/approvals", blurb: "a human signs off" },
  { key: "award", label: "Award", href: "/runs", blurb: "the supplier is chosen" },
  { key: "audit", label: "Audit", href: "/runs", blurb: "every step, hash-chained" },
];

const ORDER: JourneyStep[] = STEPS.map((s) => s.key);

interface JourneyBarProps {
  /** The active step — accent-highlighted; earlier steps render as completed. */
  current?: JourneyStep;
  /** Big animated treatment with blurbs + counts (Home) vs. compact rail. */
  size?: "sm" | "lg";
  /** Live counts keyed by step — rendered as a pill on the large variant. */
  counts?: Partial<Record<JourneyStep, number>>;
  /** Make each step a link to its screen (default true on lg, false on sm). */
  linked?: boolean;
  className?: string;
}

export function JourneyBar({
  current,
  size = "sm",
  counts,
  linked,
  className = "",
}: JourneyBarProps) {
  const lg = size === "lg";
  const isLinked = linked ?? lg;
  const currentIdx = current ? ORDER.indexOf(current) : -1;

  const dot = lg ? 40 : 22;

  return (
    <div className={`w-full ${className}`}>
      <div className="flex items-start">
        {STEPS.map((step, i) => {
          const done = currentIdx >= 0 && i < currentIdx;
          const active = i === currentIdx;
          const color = active || done ? COLORS.accent : COLORS.inkGhost;
          const count = counts?.[step.key];

          const node = (
            <motion.span
              initial={{ scale: 0.6, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: i * 0.09, duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
              className="relative flex items-center justify-center rounded-full border"
              style={{
                width: dot,
                height: dot,
                borderColor: active || done ? color : COLORS.line,
                background:
                  active || done ? withAlpha(color, active ? 0.22 : 0.12) : COLORS.panel,
                boxShadow: active ? `0 0 16px -2px ${withAlpha(color, 0.7)}` : "none",
              }}
            >
              {active && (
                <span
                  aria-hidden
                  className="absolute inset-0 rounded-full animate-[pulse-dot_1.8s_ease-in-out_infinite]"
                  style={{ background: withAlpha(color, 0.18) }}
                />
              )}
              {done ? (
                <svg
                  width={lg ? 18 : 11}
                  height={lg ? 18 : 11}
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-hidden
                >
                  <path
                    d="M5 13l4 4L19 7"
                    stroke={color}
                    strokeWidth="2.6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              ) : (
                <span
                  className="metric font-semibold"
                  style={{
                    color: active ? color : COLORS.inkFaint,
                    fontSize: lg ? 13 : 10,
                  }}
                >
                  {i + 1}
                </span>
              )}
            </motion.span>
          );

          const labelBlock = (
            <span className={`mt-2 flex flex-col items-center text-center ${lg ? "gap-1" : ""}`}>
              <span
                className="metric tracking-wide"
                style={{
                  color: active ? COLORS.ink : done ? COLORS.inkMuted : COLORS.inkFaint,
                  fontSize: lg ? 12 : 10,
                  fontWeight: active ? 600 : 500,
                }}
              >
                {step.label}
              </span>
              {lg && (
                <span className="text-[10.5px] leading-tight text-ink-faint">
                  {step.blurb}
                </span>
              )}
              {lg && count !== undefined && (
                <span
                  className="metric mt-0.5 rounded-full border px-2 py-0.5 text-[10px] leading-none"
                  style={{
                    color: count > 0 ? color : COLORS.inkFaint,
                    borderColor: withAlpha(count > 0 ? color : COLORS.inkGhost, 0.5),
                    background: withAlpha(count > 0 ? color : COLORS.inkGhost, 0.1),
                  }}
                >
                  {count}
                </span>
              )}
            </span>
          );

          const stepInner = (
            <span
              className={`flex flex-col items-center ${
                isLinked ? "transition-transform hover:-translate-y-0.5" : ""
              }`}
            >
              {node}
              {labelBlock}
            </span>
          );

          return (
            <Fragment key={step.key}>
              <div className="flex flex-col items-center" style={{ flex: "0 0 auto" }}>
                {isLinked ? (
                  <Link
                    href={step.href}
                    className="focus-ring rounded-md"
                    aria-label={`${step.label} — ${step.blurb}`}
                  >
                    {stepInner}
                  </Link>
                ) : (
                  stepInner
                )}
              </div>

              {/* rail between nodes */}
              {i < STEPS.length - 1 && (
                <div
                  className="relative mx-1 sm:mx-2"
                  style={{ flex: "1 1 0%", height: dot, minWidth: lg ? 24 : 12 }}
                >
                  <span
                    aria-hidden
                    className="absolute left-0 right-0 top-1/2 h-px -translate-y-1/2"
                    style={{ background: COLORS.line }}
                  />
                  <motion.span
                    aria-hidden
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: i < currentIdx ? 1 : 0 }}
                    transition={{ delay: i * 0.09 + 0.15, duration: 0.45 }}
                    className="absolute left-0 right-0 top-1/2 h-px origin-left -translate-y-1/2"
                    style={{
                      background: `linear-gradient(to right, ${COLORS.accent}, ${withAlpha(
                        COLORS.accent,
                        0.4,
                      )})`,
                    }}
                  />
                </div>
              )}
            </Fragment>
          );
        })}
      </div>
    </div>
  );
}
