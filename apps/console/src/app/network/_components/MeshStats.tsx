"use client";

import { Spinner, Stat } from "@/components/ui";
import { COLORS, systemHue } from "@/lib/theme";

interface MeshStatsProps {
  /** Agents currently registered in the control plane. */
  agentsRegistered: number;
  /** Total A2A hops observed across the whole mesh. */
  totalHops: number;
  /** Number of links (edges) in the topology. */
  edges: number;
  /** True when the topology endpoint is answering live. */
  live: boolean;
  /** Sample run in flight. */
  launching: boolean;
  /** Error copy when the sample run couldn't reach the control plane. */
  launchErr: string | null;
  onRunSample: () => void;
}

/**
 * The mesh stat strip — three live counters (agents registered, total A2A hops,
 * links) plus a one-click "run a sample procurement" affordance. Running a sample
 * fires real A2A traffic across the mesh, then the page flashes the edges that
 * just traversed. Graceful: the button still renders offline and surfaces a quiet
 * inline error rather than throwing.
 */
export function MeshStats({
  agentsRegistered,
  totalHops,
  edges,
  live,
  launching,
  launchErr,
  onRunSample,
}: MeshStatsProps) {
  const netHue = systemHue("NETWORK");

  return (
    <div className="grid grid-cols-1 gap-px overflow-hidden rounded-lg border border-line bg-line md:grid-cols-[repeat(3,minmax(0,1fr))_auto]">
      <div className="bg-panel p-4">
        <Stat
          label="agents registered"
          value={agentsRegistered}
          color={netHue}
        />
      </div>
      <div className="bg-panel p-4">
        <Stat
          label="total a2a hops"
          value={totalHops.toLocaleString()}
          unit={live ? "observed" : "reference"}
          color={COLORS.accent}
        />
      </div>
      <div className="bg-panel p-4">
        <Stat label="mesh links" value={edges} color={COLORS.inkMuted} />
      </div>

      {/* run-a-sample affordance — fills the trailing cell on wide screens */}
      <div className="flex flex-col justify-center gap-1.5 bg-panel p-4 md:items-end">
        <button
          type="button"
          onClick={onRunSample}
          disabled={launching}
          title="Launch a sample procurement — it fires real A2A hops, then the mesh flashes the edges it traversed."
          className="focus-ring group relative inline-flex items-center gap-2 overflow-hidden rounded-lg border border-accent/50 bg-accent/10 px-4 py-2.5 text-[13px] font-medium text-ink transition-colors hover:bg-accent/20 disabled:cursor-wait disabled:opacity-80"
        >
          <span
            aria-hidden
            className="absolute inset-0 opacity-0 transition-opacity group-hover:opacity-100"
            style={{ boxShadow: "var(--glow-accent)" }}
          />
          {launching ? (
            <Spinner size={14} />
          ) : (
            <span className="relative text-accent" aria-hidden>
              ▶
            </span>
          )}
          <span className="relative whitespace-nowrap">
            {launching ? "firing the mesh…" : "Run a sample procurement"}
          </span>
        </button>
        {launchErr && (
          <span className="font-mono text-[10px] text-warn">{launchErr}</span>
        )}
        {!launchErr && (
          <span className="font-mono text-[10px] text-ink-ghost">
            fires real a2a hops · flashes the edges
          </span>
        )}
      </div>
    </div>
  );
}
