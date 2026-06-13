"use client";

import { AnimatePresence, motion } from "motion/react";

import { LiveDot } from "@/components/ui";
import type { RecentHop } from "@/lib/api";
import { COLORS } from "@/lib/theme";

interface HopsTickerProps {
  /** The live A2A activity feed from GET /network.recent_hops (newest first). */
  hops: RecentHop[];
  /** True when the mesh is reporting live traffic (drives the live dot). */
  live: boolean;
}

/**
 * The live A2A activity ticker. Reads GET /network.recent_hops and shows the
 * most-recent agent-to-agent handoffs as "orchestrator → risk-sentinel ·
 * risk.assess ✓". Entirely graceful: with no hops it renders a quiet idle note
 * rather than an error, so the mesh always reads as instrumented.
 */
export function HopsTicker({ hops, live }: HopsTickerProps) {
  const recent = hops
    .filter((h) => h.from_agent && h.to_agent)
    .slice(0, 10);

  return (
    <div className="flex items-center gap-3 px-4 py-2.5">
      <span className="inline-flex shrink-0 items-center gap-1.5">
        <LiveDot live={live && recent.length > 0} size={6} />
        <span className="label-cap">a2a activity</span>
      </span>

      {recent.length === 0 ? (
        <span className="font-mono text-[10px] text-ink-ghost">
          no hops yet — run a procurement to light up the mesh
        </span>
      ) : (
        <div className="relative min-w-0 flex-1 overflow-hidden">
          <div className="flex gap-2.5 overflow-x-auto pb-0.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            <AnimatePresence initial={false}>
              {recent.map((h, i) => (
                <motion.span
                  key={`${h.from_agent}->${h.to_agent}:${h.skill_id}:${i}`}
                  layout
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}
                  className="inline-flex shrink-0 items-center gap-1 rounded-md border border-line bg-panel-2 px-2 py-1 font-mono text-[10px]"
                >
                  <span className="text-ink-muted">{shortName(h.from_agent)}</span>
                  <span className="text-ink-ghost">→</span>
                  <span className="text-ink-muted">{shortName(h.to_agent)}</span>
                  <span className="text-ink-ghost">·</span>
                  <span className="text-ink-faint">{h.skill_id}</span>
                  <span
                    aria-hidden
                    style={{ color: h.ok ? COLORS.ok : COLORS.danger }}
                  >
                    {h.ok ? "✓" : "✕"}
                  </span>
                </motion.span>
              ))}
            </AnimatePresence>
          </div>
          {/* edge fade so the row dissolves rather than hard-clipping */}
          <span
            aria-hidden
            className="pointer-events-none absolute inset-y-0 right-0 w-10"
            style={{
              background: `linear-gradient(to right, transparent, ${COLORS.panel})`,
            }}
          />
        </div>
      )}
    </div>
  );
}

/** Trim the conventional "agent-" prefix so the ticker stays compact. */
function shortName(id: string): string {
  return id.startsWith("agent-") ? id.slice(6) : id;
}
