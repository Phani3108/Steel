"use client";

import { AnimatePresence, motion } from "motion/react";

import { Panel, SectionHeader } from "@/components/ui";
import { JourneyBar } from "@/components/JourneyBar";
import { COLORS } from "@/lib/theme";
import { MissionForm } from "./_components/MissionForm";
import { MissionIdle } from "./_components/MissionIdle";
import { MissionTimeline } from "./_components/MissionTimeline";
import { useMission } from "./_components/useMission";

/**
 * /orchestrate — MISSION CONTROL.
 *
 * Launch an intake → POST /orchestrate → watch the orchestrator fan out to its
 * specialists as a live, staged mission timeline; the run either awards or pauses
 * at an approval gate. When the control plane is offline, a scripted "reference
 * run" plays over the fleet so the page is always a compelling demo.
 */
export default function OrchestratePage() {
  const { state, busy, launch, reset } = useMission();
  const referenceMode = state?.source === "reference";

  return (
    <div className="space-y-6">
      <SectionHeader
        kicker="cockpit · mission control"
        title="Mission"
        subtitle="Launch a procurement intake and watch the STEEL-Orchestrator route it across the fleet — every specialist, every hop, one shared trace, in real time."
        action={
          referenceMode ? (
            <span
              className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px]"
              style={{
                borderColor: "color-mix(in srgb, var(--autonomy) 35%, transparent)",
                color: COLORS.autonomy,
                background: "color-mix(in srgb, var(--autonomy) 10%, transparent)",
              }}
              title="POST /orchestrate is unreachable — replaying a scripted run over the reference fleet."
            >
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{ background: COLORS.autonomy }}
              />
              live telemetry offline — reference run
            </span>
          ) : null
        }
      />

      <Panel accent="accent" title="procurement journey · you are here">
        <JourneyBar current="orchestrate" size="sm" linked />
      </Panel>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)] lg:items-start">
        {/* intake — sticky on wide screens so it stays in reach while the run scrolls */}
        <div className="lg:sticky lg:top-6">
          <MissionForm
            onLaunch={launch}
            busy={busy}
            hasMission={state !== null}
            onReset={reset}
          />
        </div>

        {/* the mission board */}
        <div className="min-w-0">
          <AnimatePresence mode="wait">
            {state ? (
              <motion.div
                key="timeline"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
              >
                <MissionTimeline state={state} />
              </motion.div>
            ) : (
              <motion.div
                key="idle"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
              >
                <MissionIdle />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
