import type { ReactNode } from "react";

import { SectionHeader } from "@/components/ui";
import { AgentBuilder } from "./_components/AgentBuilder";
import { MaturityLadder } from "./_components/MaturityLadder";
import { TransparencyCard } from "./_components/TransparencyCard";

export const metadata = {
  title: "Studio · JAI",
  description:
    "Design-time + governance — author a schema-valid agent manifest, watch autonomy earned through scorecards, and see the EU AI Act transparency posture.",
};

/**
 * /studio — STUDIO (design-time + governance).
 *
 * The quieter counterpart to the live instruments: where the cockpit's other
 * screens watch agents act, this one is where they are *designed* and *trusted*.
 * Three sections, one page:
 *   1. Build an agent  — compose a real jai/v1 AgentManifest, validated live.
 *   2. Maturity ladder — autonomy proven by scorecards, never edited in.
 *   3. Transparency    — the EU AI Act Art. 50 disclosure, made visible.
 */
export default function StudioPage() {
  return (
    <div className="space-y-8">
      <SectionHeader
        kicker="cockpit · design-time"
        title="Studio"
        subtitle="Where agents are designed and trusted. Author a schema-valid manifest the platform could compile, watch autonomy earned through evals, and see the governance posture the whole fleet operates under."
      />

      <SectionLead n="01" title="Build an agent">
        Compose a real, schema-valid manifest — the same contract jai-engine
        compiles. The studio is design-time, not a no-code runtime.
      </SectionLead>
      <AgentBuilder />

      <SectionLead n="02" title="Maturity ladder">
        Autonomy is earned. An agent climbs a level only when its scorecards
        clear the gate — governance proven by evals, never edited in.
      </SectionLead>
      <MaturityLadder />

      <SectionLead n="03" title="Transparency">
        The compliance posture made visible — the EU AI Act Article 50
        disclosure the platform serves on every screen.
      </SectionLead>
      <TransparencyCard />
    </div>
  );
}

/** A small numbered lead-in above each section — keeps the long page legible. */
function SectionLead({
  n,
  title,
  children,
}: {
  n: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="flex items-baseline gap-3 border-b border-line pb-2.5">
      <span className="metric text-sm font-bold text-autonomy">{n}</span>
      <div>
        <h2 className="text-base font-semibold tracking-tight text-ink">
          {title}
        </h2>
        <p className="mt-0.5 max-w-2xl text-[12px] leading-relaxed text-ink-faint">
          {children}
        </p>
      </div>
    </div>
  );
}
