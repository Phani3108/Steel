"use client";

import { motion } from "motion/react";

import { GaugeRing, Panel } from "@/components/ui";
import { COLORS, SYSTEMS, systemHue, withAlpha } from "@/lib/theme";
import type { CatalogSystem, HeadlineStats } from "./data";

interface HeadlineBandProps {
  stats: HeadlineStats;
  systems: CatalogSystem[];
}

function BigStat({
  label,
  value,
  sub,
  color = COLORS.ink,
  delay,
}: {
  label: string;
  value: string;
  sub?: string;
  color?: string;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="flex flex-col justify-center px-5 py-4"
    >
      <div className="label-cap">{label}</div>
      <div className="mt-1.5 flex items-baseline gap-1.5">
        <span
          className="metric text-3xl font-semibold leading-none"
          style={{ color }}
        >
          {value}
        </span>
      </div>
      {sub && <div className="mt-1.5 font-mono text-[11px] text-ink-faint">{sub}</div>}
    </motion.div>
  );
}

/**
 * The top telemetry band: headline counts + an average pass-rate gauge + a
 * six-segment "systems online" indicator. Sets the tone before the diagram.
 */
export function HeadlineBand({ stats, systems }: HeadlineBandProps) {
  const onlineBySystem = new Map(
    systems.map((s) => [s.system, s.parts.some((p) => p.status === "active")]),
  );

  return (
    <Panel grid flush className="overflow-hidden">
      <div className="grid grid-cols-2 divide-x divide-y divide-line md:grid-cols-4 md:divide-y-0 lg:grid-cols-[repeat(3,minmax(0,1fr))_auto_auto]">
        <BigStat
          label="parts built"
          value={`${stats.partsActive}`}
          sub={`of ${stats.partsTotal} cataloged`}
          color={COLORS.ink}
          delay={0.04}
        />
        <BigStat
          label="agents active"
          value={`${stats.agentsActive}`}
          sub={`of ${stats.agentsTotal} in the fleet`}
          color={COLORS.autonomy}
          delay={0.09}
        />
        <BigStat
          label="systems online"
          value={`${stats.systemsOnline}`}
          sub={`of ${stats.systemsTotal} subsystems`}
          color={COLORS.accent}
          delay={0.14}
        />

        {/* avg pass-rate gauge */}
        <motion.div
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.18, duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          className="flex items-center justify-center px-5 py-4"
        >
          {stats.avgPassRate != null ? (
            <GaugeRing
              value={stats.avgPassRate}
              size={92}
              caption={`${stats.scoredAgents} scored`}
            />
          ) : (
            <GaugeRing value={0} size={92} label="—" caption="no scores" />
          )}
        </motion.div>

        {/* systems-online segmented readout */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.22, duration: 0.45 }}
          className="hidden flex-col justify-center gap-1.5 px-5 py-4 lg:flex"
        >
          <div className="label-cap mb-0.5">subsystems</div>
          {SYSTEMS.map((sys) => {
            const online = onlineBySystem.get(sys) ?? false;
            const hue = systemHue(sys);
            return (
              <div key={sys} className="flex items-center gap-2">
                <span
                  className="inline-block h-1.5 w-1.5 rounded-full"
                  style={{
                    background: online ? hue : COLORS.inkGhost,
                    boxShadow: online ? `0 0 6px -1px ${hue}` : "none",
                  }}
                />
                <span
                  className="font-mono text-[10px] tracking-wider"
                  style={{ color: online ? withAlpha(hue, 0.9) : COLORS.inkFaint }}
                >
                  {sys}
                </span>
              </div>
            );
          })}
        </motion.div>
      </div>
    </Panel>
  );
}
