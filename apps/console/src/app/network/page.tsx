"use client";

import { useCallback, useMemo, useState } from "react";

import { Panel, Pill, ReferenceBadge, SectionHeader, Spinner } from "@/components/ui";
import {
  fetchNetwork,
  fetchRegistry,
  fetchRuns,
  startSampleProcurement,
  type AgentRecord,
  type NetworkTopology,
  type RunSummary,
} from "@/lib/api";
import { REFERENCE_NETWORK } from "@/lib/fleet";
import type { Status } from "@/lib/theme";
import { usePoll } from "@/lib/usePoll";

import { FleetGraph } from "./_components/FleetGraph";
import { HopsTicker } from "./_components/HopsTicker";
import { Legend } from "./_components/Legend";
import { MeshStats } from "./_components/MeshStats";
import { NodeDetail } from "./_components/NodeDetail";
import {
  indexRegistry,
  indexRunsByAgent,
  offlineRegistry,
  resolveNode,
  type NodeView,
} from "./_components/resolve";

/** How long a freshly-fired edge stays lit after a sample run. */
const FIRE_HOLD_MS = 6000;

export default function NetworkPage() {
  const [selected, setSelected] = useState<string | null>(null);

  // One-click "run a sample procurement" affordance.
  const [launching, setLaunching] = useState(false);
  const [launchErr, setLaunchErr] = useState<string | null>(null);
  const [firedEdges, setFiredEdges] = useState<Set<string>>(new Set());

  // --- live topology (falls back to the reference fleet) ---
  const net = usePoll<NetworkTopology>(fetchNetwork, 6000);
  const topology: NetworkTopology = useMemo(() => {
    const live = net.data;
    if (live && live.nodes.length > 0) return live;
    // The reference fleet has no live counters — coerce it into the live shape.
    return {
      ...REFERENCE_NETWORK,
      live: false,
      agents_registered: REFERENCE_NETWORK.nodes.filter((n) =>
        n.id.startsWith("agent-"),
      ).length,
      total_hops: 0,
      recent_hops: [],
    } as NetworkTopology;
  }, [net.data]);

  // --- live registry (falls back to fleet-derived records) ---
  const reg = usePoll<AgentRecord[]>(fetchRegistry, 8000);
  const registry: Map<string, AgentRecord> = useMemo(() => {
    if (reg.data && reg.data.length > 0) return indexRegistry(reg.data);
    return offlineRegistry();
  }, [reg.data]);

  // --- live runs feed — joins recent runs onto each agent for deep-links ---
  const runsFetch = useCallback(() => fetchRuns(), []);
  const runs = usePoll<RunSummary[]>(runsFetch, 5000);
  const runsByAgent = useMemo(
    () => indexRunsByAgent(runs.data ?? []),
    [runs.data],
  );

  // The structural feeds drive the offline state; the runs feed is best-effort.
  const offline = net.offline || reg.offline;
  // First paint: hold a spinner until the topology has resolved at least once.
  const booting = !net.loaded && net.data === null;
  // "live" mode when the control plane is answering the topology endpoint.
  const isLive = !net.offline && net.data !== null && net.data.nodes.length > 0;

  // Resolve every topology node into a full inspectable view (record + runs).
  const nodeViews: NodeView[] = useMemo(
    () => topology.nodes.map((n) => resolveNode(n, registry, runsByAgent)),
    [topology.nodes, registry, runsByAgent],
  );
  const selectedView = useMemo(
    () => nodeViews.find((n) => n.id === selected) ?? null,
    [nodeViews, selected],
  );

  // Status accessor for the graph (registry status → node ring color).
  const statusOf = useCallback(
    (id: string): Status => {
      const rec = registry.get(id);
      const node = topology.nodes.find((n) => n.id === id);
      return (rec?.status as Status) ?? (node?.status as Status) ?? "active";
    },
    [registry, topology.nodes],
  );

  // Live/dark accessor — a node reads lit when the control plane reports it in.
  const liveOf = useCallback(
    (id: string): boolean => {
      const node = topology.nodes.find((n) => n.id === id);
      // When live data is present, honor the per-node flag; otherwise all on.
      if (isLive) return node?.live ?? false;
      return true;
    },
    [topology.nodes, isLive],
  );

  // ---- run a sample procurement, then flash the edges it just traversed ----
  const runSample = useCallback(async () => {
    setLaunching(true);
    setLaunchErr(null);
    try {
      const res = await startSampleProcurement();
      // Light up every edge the orchestration trace traversed for a beat.
      if (res?.hops?.length) {
        const fired = new Set(
          res.hops.map((h) => `${h.from_agent}->${h.to_agent}`),
        );
        setFiredEdges(fired);
        setTimeout(() => setFiredEdges(new Set()), FIRE_HOLD_MS);
      }
      setLaunching(false);
    } catch {
      setLaunchErr("control plane offline — couldn't run a sample");
      setLaunching(false);
    }
  }, []);

  const agentCount = topology.agents_registered;

  return (
    <div className="flex flex-col gap-6">
      <SectionHeader
        kicker="network · the fleet"
        title="Fleet"
        subtitle="The agent-to-agent mesh, live. Watch intake flow from the operator through the orchestrator out to the specialists and the MCP services. Edges that have carried real A2A traffic light up and carry a hop count; click any node to inspect its mandate, autonomy, scorecard, and the runs it touched."
        action={
          <div className="flex flex-wrap items-center justify-end gap-2">
            <ReferenceBadge mode={isLive ? "live" : "reference"} />
            <Pill tone="accent">{agentCount} agents</Pill>
            <Pill tone="neutral">{topology.edges.length} links</Pill>
          </div>
        }
      />

      {/* --- mesh stats: agents registered + total A2A hops + sample CTA --- */}
      <MeshStats
        agentsRegistered={topology.agents_registered}
        totalHops={topology.total_hops}
        edges={topology.edges.length}
        live={isLive}
        launching={launching}
        launchErr={launchErr}
        onRunSample={runSample}
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        {/* --- the graph --- */}
        <Panel
          accent="NETWORK"
          grid
          flush
          title="fleet mesh"
          action={
            <span className="metric text-[10px] tracking-wider text-ink-faint">
              {isLive ? "a2a · live" : "a2a · reference"}
            </span>
          }
        >
          {booting ? (
            <div className="flex h-[480px] items-center justify-center">
              <Spinner label="resolving fleet topology…" />
            </div>
          ) : (
            <div className="px-2 pt-3 pb-1">
              <FleetGraph
                nodes={topology.nodes}
                edges={topology.edges}
                selected={selected}
                statusOf={statusOf}
                liveOf={liveOf}
                firedEdges={firedEdges}
                onSelect={(id) => setSelected((s) => (s === id ? null : id))}
              />
            </div>
          )}
          <div className="border-t border-line">
            <HopsTicker hops={topology.recent_hops} live={isLive} />
          </div>
          <div className="border-t border-line">
            <Legend />
          </div>
        </Panel>

        {/* --- the inspector --- */}
        <Panel
          accent={selectedView ? selectedView.system : "none"}
          title="node inspector"
          action={
            selected ? (
              <button
                onClick={() => setSelected(null)}
                className="focus-ring rounded px-1.5 py-0.5 font-mono text-[10px] text-ink-faint transition-colors hover:text-ink"
              >
                clear
              </button>
            ) : undefined
          }
          flush
        >
          <NodeDetail node={selectedView} offline={offline} />
        </Panel>
      </div>
    </div>
  );
}
