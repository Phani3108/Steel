"use client";

import { AnimatePresence, motion } from "motion/react";

import {
  AutonomyMeter,
  Chip,
  GaugeRing,
  Panel,
  Pill,
  SystemBadge,
} from "@/components/ui";
import { fmtTs, fmtUsd } from "@/lib/api";
import { COLORS, systemHue, withAlpha } from "@/lib/theme";
import type { CatalogPart } from "./data";

interface DetailPanelProps {
  part: CatalogPart | null;
  onClose: () => void;
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5">
      <span className="label-cap">{label}</span>
      <span className="text-right text-xs text-ink">{children}</span>
    </div>
  );
}

/**
 * The part inspector — slides in beside the diagram when a node is selected.
 * Shows the universal facts for any part, and the full agent dossier (autonomy,
 * pipeline, skills, mandate, latest scorecard) for the fleet.
 */
export function DetailPanel({ part, onClose }: DetailPanelProps) {
  return (
    <AnimatePresence mode="wait">
      {part && (
        <motion.div
          key={part.name}
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 16 }}
          transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
        >
          <Panel
            accent={part.system}
            title={
              <div className="flex items-center gap-2">
                <SystemBadge system={part.system} dotOnly />
                <span className="metric text-[13px] font-semibold text-ink">
                  {part.name}
                </span>
              </div>
            }
            action={
              <button
                onClick={onClose}
                aria-label="close detail"
                className="focus-ring rounded-md px-1.5 text-ink-faint transition-colors hover:text-ink"
              >
                ✕
              </button>
            }
          >
            <div className="flex items-center gap-2">
              <Pill status={part.status}>{part.status}</Pill>
              <Pill tone={part.isAgent ? "autonomy" : "neutral"}>
                {part.isAgent ? "agent" : "part"}
              </Pill>
              {part.live ? (
                <Pill tone="accent">live</Pill>
              ) : (
                <Pill tone="neutral">reference</Pill>
              )}
            </div>

            <p className="mt-3 text-sm leading-relaxed text-ink-muted">
              {part.purpose}
            </p>

            <div className="mt-3 hairline" />

            {part.isAgent ? (
              <div className="mt-2">
                {/* scorecard hero */}
                {part.scorecard ? (
                  <div className="flex items-center gap-4 rounded-md border border-line bg-base-2 p-3">
                    <GaugeRing
                      value={part.scorecard.pass_rate}
                      size={76}
                      caption="pass"
                    />
                    <div className="min-w-0">
                      <div className="label-cap">latest scorecard</div>
                      <div className="metric mt-1 text-sm text-ink">
                        {part.scorecard.n_passed}/{part.scorecard.n_cases} cases
                      </div>
                      <div className="mt-0.5 truncate font-mono text-[11px] text-ink-faint">
                        {part.scorecard.suite}
                      </div>
                      <div className="mt-0.5 font-mono text-[10px] text-ink-ghost">
                        {fmtTs(part.scorecard.ts)}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-md border border-dashed border-line bg-base-2 px-3 py-2.5 text-center font-mono text-[11px] text-ink-faint">
                    no scorecard yet — no ship without one
                  </div>
                )}

                <div className="mt-3 space-y-0.5">
                  <Row label="autonomy">
                    <AutonomyMeter
                      level={part.autonomy_level ?? 1}
                      size="sm"
                      className="justify-end"
                    />
                  </Row>
                  <Row label="pipeline">
                    <span className="metric text-ink-muted">
                      {part.pipeline ?? "—"}
                    </span>
                  </Row>
                  <Row label="mandate">
                    <span
                      className="metric"
                      style={{
                        color:
                          part.mandate_usd != null ? COLORS.ok : COLORS.inkFaint,
                      }}
                    >
                      {part.mandate_usd != null ? fmtUsd(part.mandate_usd) : "none"}
                    </span>
                  </Row>
                </div>

                {part.skills && part.skills.length > 0 && (
                  <div className="mt-3">
                    <div className="label-cap mb-2">skills</div>
                    <div className="flex flex-wrap gap-1.5">
                      {part.skills.map((s) => (
                        <Chip
                          key={s}
                          color={systemHue(part.system)}
                          title={s}
                        >
                          {s}
                        </Chip>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="mt-2 space-y-0.5">
                <Row label="system">
                  <SystemBadge system={part.system} showTagline />
                </Row>
                <Row label="role">
                  <span className="metric text-ink-muted">infrastructure</span>
                </Row>
                <div
                  className="mt-3 rounded-md border px-3 py-2.5 text-[11px] leading-relaxed text-ink-faint"
                  style={{
                    borderColor: withAlpha(systemHue(part.system), 0.25),
                    background: withAlpha(systemHue(part.system), 0.05),
                  }}
                >
                  A standalone part of the {part.system.toLowerCase()} system —
                  rippable as an MCP plug-and-play module.
                </div>
              </div>
            )}
          </Panel>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
