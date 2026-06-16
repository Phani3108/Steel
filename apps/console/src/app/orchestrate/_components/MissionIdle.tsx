"use client";

import { Panel } from "@/components/ui";
import { COLORS } from "@/lib/theme";
import { FanoutDiagram } from "./FanoutDiagram";

/** The three phases of an orchestrated mission, narrated for the idle state. */
const STEPS = [
  {
    n: "01",
    title: "Route",
    body: "The orchestrator parses your intake and fans out to the right specialists.",
  },
  {
    n: "02",
    title: "Compose",
    body: "Triage, risk, spend and sourcing each do their part over A2A — one shared trace.",
  },
  {
    n: "03",
    title: "Resolve",
    body: "It awards within mandate, or pauses at an approval gate when the spend is large.",
  },
] as const;

/**
 * Idle state — shown before a mission launches. The orchestrator fan-out hero
 * plus a three-beat explanation of what a mission does. Keeps the empty page a
 * compelling demo of the STEEL-Orchestrator story.
 */
export function MissionIdle() {
  return (
    <Panel grid accent="NETWORK" title="orchestrator standing by">
      <div className="py-2">
        <FanoutDiagram />
      </div>

      <div className="mt-4 grid gap-3 border-t border-line pt-4 sm:grid-cols-3">
        {STEPS.map((s) => (
          <div key={s.n} className="rounded-md border border-line bg-base-2/50 p-3">
            <div className="flex items-center gap-2">
              <span
                className="metric text-sm font-bold"
                style={{ color: COLORS.autonomy }}
              >
                {s.n}
              </span>
              <span className="text-sm font-medium text-ink">{s.title}</span>
            </div>
            <p className="mt-1.5 text-[12px] leading-relaxed text-ink-faint">
              {s.body}
            </p>
          </div>
        ))}
      </div>

      <p className="mt-4 text-center text-[12px] text-ink-faint">
        Fill the intake and{" "}
        <span className="text-accent">launch a mission</span> to watch the fleet
        coordinate in real time.
      </p>
    </Panel>
  );
}
