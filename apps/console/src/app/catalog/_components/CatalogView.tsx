"use client";

import { AnimatePresence, motion } from "motion/react";
import { useMemo, useState } from "react";

import { EmptyState, LiveDot, Pill, SectionHeader } from "@/components/ui";
import { fetchRegistry, type AgentRecord } from "@/lib/api";
import { usePoll } from "@/lib/usePoll";
import { buildCatalog, headlineStats, type CatalogPart } from "./data";
import { DetailPanel } from "./DetailPanel";
import { Diagram } from "./Diagram";
import { HeadlineBand } from "./HeadlineBand";

/**
 * The Catalog cockpit — hero of the console. Polls /registry every 8s, merges
 * it onto the reference fleet, and renders the exploded-vehicle blueprint with a
 * live headline band and a slide-in part inspector. Falls back silently to the
 * reference fleet whenever the registry is unreachable.
 */
export function CatalogView() {
  const { data: registry, offline, loaded } = usePoll<AgentRecord[]>(
    fetchRegistry,
    8000,
  );

  const { systems, live } = useMemo(() => buildCatalog(registry), [registry]);
  const stats = useMemo(() => headlineStats(systems), [systems]);

  const [selected, setSelected] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);

  const selectedPart: CatalogPart | null = useMemo(() => {
    if (!selected) return null;
    for (const s of systems) {
      const p = s.parts.find((pt) => pt.name === selected);
      if (p) return p;
    }
    return null;
  }, [selected, systems]);

  // Live only when the registry actually answered this session.
  const isLive = live && !offline;

  return (
    <div className="space-y-6">
      <SectionHeader
        kicker="parts catalog"
        title="The vehicle"
        subtitle="JAI is built like a car: six systems, every part named, standalone, and rippable as an MCP plug-and-play module. This is the cockpit's exploded view — hover a part to trace it, click to open its dossier."
        action={
          <div className="flex items-center gap-2.5">
            {isLive ? (
              <LiveDot live label="REGISTRY LIVE" />
            ) : (
              <span className="flex items-center gap-2">
                <LiveDot live={false} color="var(--ink-faint)" />
                <span className="metric text-[10px] tracking-wider text-ink-faint">
                  REFERENCE FLEET
                </span>
              </span>
            )}
          </div>
        }
      />

      {/* quiet offline note — never a crash or blank */}
      <AnimatePresence>
        {loaded && !isLive && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="flex items-center gap-2 rounded-md border border-line bg-base-2 px-3 py-2 text-[11px] text-ink-faint">
              <span
                className="inline-block h-1.5 w-1.5 rounded-full bg-warn/70"
                aria-hidden
              />
              live telemetry offline — showing the built-in reference fleet
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <HeadlineBand stats={stats} systems={systems} />

      {/* diagram + inspector */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="panel telem-grid relative overflow-hidden p-3 sm:p-5">
          {/* corner accent sweep */}
          <span
            aria-hidden
            className="pointer-events-none absolute inset-x-0 top-0 h-px"
            style={{
              background:
                "linear-gradient(to right, transparent, var(--accent), transparent)",
            }}
          />
          <div className="mb-2 flex items-center justify-between px-1">
            <span className="label-cap">platform schematic</span>
            <span className="metric text-[10px] tracking-wider text-ink-faint">
              {stats.partsTotal} parts · {stats.systemsTotal} systems
            </span>
          </div>
          <Diagram
            systems={systems}
            selected={selected}
            hovered={hovered}
            onSelect={(name) => setSelected((cur) => (cur === name ? null : name))}
            onHover={setHovered}
          />
        </div>

        {/* inspector rail */}
        <div className="lg:sticky lg:top-24 lg:self-start">
          {selectedPart ? (
            <DetailPanel part={selectedPart} onClose={() => setSelected(null)} />
          ) : (
            <div className="panel flex h-full min-h-[260px] items-center">
              <EmptyState
                title="Select a part"
                hint="Click any node in the schematic to open its dossier — purpose, status, and (for agents) autonomy, pipeline, skills, and the latest scorecard."
                icon={
                  <svg width="34" height="34" viewBox="0 0 34 34" fill="none">
                    <rect
                      x="4"
                      y="4"
                      width="26"
                      height="26"
                      rx="6"
                      stroke="currentColor"
                      strokeWidth="1.4"
                    />
                    <circle cx="17" cy="17" r="3.2" fill="currentColor" />
                    <path
                      d="M17 4v6M17 24v6M4 17h6M24 17h6"
                      stroke="currentColor"
                      strokeWidth="1.4"
                    />
                  </svg>
                }
              />
            </div>
          )}
        </div>
      </div>

      {/* legend */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-1 text-ink-faint">
        <span className="label-cap">legend</span>
        <span className="flex items-center gap-1.5 text-[11px]">
          <span className="inline-block h-2 w-1 rounded-sm bg-ok" /> active
        </span>
        <span className="flex items-center gap-1.5 text-[11px]">
          <span className="inline-block h-2 w-1 rounded-sm bg-warn" /> paused
        </span>
        <span className="flex items-center gap-1.5 text-[11px]">
          <span className="inline-block h-2 w-1 rounded-sm bg-ink-ghost" /> planned
        </span>
        <span className="flex items-center gap-1.5 text-[11px]">
          <span className="flex gap-px">
            <span className="inline-block h-1 w-1 rounded-sm bg-autonomy" />
            <span className="inline-block h-1 w-1 rounded-sm bg-autonomy" />
            <span className="inline-block h-1 w-1 rounded-sm bg-ink-ghost" />
          </span>
          autonomy L1–L5
        </span>
        <span className="flex items-center gap-1.5 text-[11px]">
          <Pill tone="autonomy" className="!text-[9px]">
            agent
          </Pill>
          carries a scorecard
        </span>
      </div>
    </div>
  );
}
