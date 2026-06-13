"use client";

import { useMemo } from "react";

import type { NetworkEdge, NetworkNode } from "@/lib/api";
import {
  COLORS,
  statusColor,
  systemHue,
  withAlpha,
  type Status,
} from "@/lib/theme";

import { computeLayout, edgePath, type LaidOutNode } from "./layout";

interface FleetGraphProps {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  /** Currently selected node id (or null). */
  selected: string | null;
  /** Status by node id (active/paused/…); defaults to active. */
  statusOf?: (id: string) => Status;
  /** Whether a node is reporting live (drives its rim brightness). */
  liveOf?: (id: string) => boolean;
  /** Edge ids that just fired from a sample run — flash bright for a beat. */
  firedEdges?: Set<string>;
  onSelect: (id: string) => void;
}

/**
 * The fleet network graph — a hand-rolled SVG node-link diagram.
 *
 * Layout is deterministic (layered left→right). Edges are bezier "cables"
 * tinted by their source system. An edge that has carried REAL A2A traffic
 * (`active`, with a `hops` count) renders bright + thicker, runs a fast data
 * packet, and shows a hop-count badge; an edge that has never fired stays dim
 * and quiet. Nodes are drawn as system-hued glyphs whose shape encodes role
 * (diamond=human, circle=agent, square=service); a dark/idle node (not live)
 * reads muted, an active one reads lit. Click to inspect.
 */
export function FleetGraph({
  nodes,
  edges,
  selected,
  statusOf,
  liveOf,
  firedEdges,
  onSelect,
}: FleetGraphProps) {
  const layout = useMemo(() => computeLayout(nodes, edges), [nodes, edges]);
  const { width, height } = layout;

  // Which nodes touch the selection — used to spotlight the active subgraph.
  const neighbors = useMemo(() => {
    const set = new Set<string>();
    if (!selected) return set;
    set.add(selected);
    for (const e of layout.edges) {
      if (e.source === selected) set.add(e.target);
      if (e.target === selected) set.add(e.source);
    }
    return set;
  }, [selected, layout.edges]);

  const dim = (id: string) => selected !== null && !neighbors.has(id);

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        style={{ minWidth: width * 0.62, display: "block" }}
        role="group"
        aria-label="Fleet network graph"
      >
        <defs>
          <radialGradient id="fg-node-core" cx="50%" cy="38%" r="65%">
            <stop offset="0%" stopColor={withAlpha(COLORS.ink, 0.16)} />
            <stop offset="100%" stopColor={withAlpha(COLORS.base, 0)} />
          </radialGradient>
          {/* per-edge motion paths for the data packets */}
          {layout.edges.map((e) => (
            <path key={`p-${e.id}`} id={`path-${e.id}`} d={edgePath(e)} fill="none" />
          ))}
        </defs>

        {/* ---- edges (cables) ---- */}
        <g>
          {layout.edges.map((e) => {
            const hue = systemHue(
              nodes.find((n) => n.id === e.source)?.system ?? "NETWORK",
            );
            // An edge is "active" when the control plane reports real A2A traffic.
            const active = Boolean(e.active) || (e.hops ?? 0) > 0;
            const fired = firedEdges?.has(e.id) ?? false;
            const involved =
              selected === null ||
              e.source === selected ||
              e.target === selected;
            // Base opacity: active edges read bright, idle edges stay faint.
            const baseOp = active ? 0.78 : 0.16;
            const op = involved ? (fired ? 1 : baseOp) : 0.1;
            const d = edgePath(e);

            return (
              <g key={e.id}>
                <path
                  d={d}
                  fill="none"
                  stroke={withAlpha(hue, op)}
                  strokeWidth={fired ? 2.6 : active ? 2 : 1.2}
                  strokeLinecap="round"
                  strokeDasharray={active ? undefined : "3 4"}
                  style={{ transition: "stroke 0.4s, stroke-width 0.4s" }}
                />
                {/* edge label, set at the midpoint */}
                {e.label && involved && (
                  <EdgeLabel e={e} hue={hue} active={active} />
                )}
                {/* hop-count badge on edges that have carried real traffic */}
                {active && involved && (e.hops ?? 0) > 0 && (
                  <HopBadge e={e} hue={hue} hops={e.hops ?? 0} />
                )}
                {/* the travelling data packet — only on live/fired edges */}
                {(active || fired) && (
                  <DataPacket
                    edgeId={e.id}
                    hue={hue}
                    fast={fired}
                    faded={!involved}
                  />
                )}
              </g>
            );
          })}
        </g>

        {/* ---- nodes ---- */}
        <g>
          {layout.nodes.map((n) => (
            <NodeGlyph
              key={n.id}
              node={n}
              status={statusOf?.(n.id) ?? "active"}
              live={liveOf?.(n.id) ?? true}
              selected={n.id === selected}
              dimmed={dim(n.id)}
              onSelect={onSelect}
            />
          ))}
        </g>
      </svg>
    </div>
  );
}

// --------------------------------------------------------------- packets ----

function DataPacket({
  edgeId,
  hue,
  fast,
  faded,
}: {
  edgeId: string;
  hue: string;
  fast: boolean;
  faded: boolean;
}) {
  // Deterministic per-edge phase so packets don't all fire in lockstep.
  const seed = useMemo(() => hashString(edgeId), [edgeId]);
  const dur = fast ? 1.1 : 2.6 + (seed % 7) * 0.16;
  const begin = -((seed % 11) * 0.27);

  return (
    <circle
      r={fast ? 3.4 : 2.4}
      fill={hue}
      opacity={faded ? 0.18 : fast ? 1 : 0.9}
      style={{
        filter: `drop-shadow(0 0 ${fast ? 6 : 3.5}px ${withAlpha(hue, 0.9)})`,
        transition: "opacity 0.4s",
      }}
    >
      <animateMotion
        dur={`${dur}s`}
        begin={`${begin}s`}
        repeatCount="indefinite"
        rotate="auto"
        keyPoints="0;1"
        keyTimes="0;1"
        calcMode="linear"
      >
        <mpath href={`#path-${edgeId}`} />
      </animateMotion>
    </circle>
  );
}

function EdgeLabel({
  e,
  hue,
  active,
}: {
  e: { x1: number; y1: number; x2: number; y2: number; label?: string };
  hue: string;
  active: boolean;
}) {
  const mx = (e.x1 + e.x2) / 2;
  const my = (e.y1 + e.y2) / 2 - 6;
  return (
    <text
      x={mx}
      y={my}
      textAnchor="middle"
      className="metric"
      style={{
        fill: active ? hue : COLORS.inkGhost,
        fontSize: 9,
        letterSpacing: "0.06em",
        pointerEvents: "none",
      }}
    >
      {e.label}
    </text>
  );
}

/** A small "×N" hop-count badge pinned just below an active edge's midpoint. */
function HopBadge({
  e,
  hue,
  hops,
}: {
  e: { x1: number; y1: number; x2: number; y2: number };
  hue: string;
  hops: number;
}) {
  const mx = (e.x1 + e.x2) / 2;
  const my = (e.y1 + e.y2) / 2 + 9;
  const text = `${hops} hop${hops === 1 ? "" : "s"}`;
  const w = text.length * 5.4 + 10;
  return (
    <g pointerEvents="none">
      <rect
        x={mx - w / 2}
        y={my - 7}
        width={w}
        height={13}
        rx={6.5}
        fill={withAlpha(hue, 0.16)}
        stroke={withAlpha(hue, 0.4)}
        strokeWidth={0.75}
      />
      <text
        x={mx}
        y={my + 2.5}
        textAnchor="middle"
        className="metric"
        style={{ fill: hue, fontSize: 8.5, letterSpacing: "0.04em" }}
      >
        {text}
      </text>
    </g>
  );
}

// ----------------------------------------------------------------- nodes ----

const NODE_R = 22;

function NodeGlyph({
  node,
  status,
  live,
  selected,
  dimmed,
  onSelect,
}: {
  node: LaidOutNode;
  status: Status;
  live: boolean;
  selected: boolean;
  dimmed: boolean;
  onSelect: (id: string) => void;
}) {
  const hue = systemHue(node.system);
  const ring = statusColor(status);
  const { x, y } = node;
  // A node that isn't reporting live reads muted — its hue rim and status dot dim.
  const rimAlpha = live ? (selected ? 0.95 : 0.7) : 0.28;

  return (
    <g
      transform={`translate(${x} ${y})`}
      onClick={() => onSelect(node.id)}
      role="button"
      tabIndex={0}
      aria-label={`${node.label} — ${node.system} ${node.role}${live ? "" : " (offline)"}`}
      aria-pressed={selected}
      onKeyDown={(ev) => {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          onSelect(node.id);
        }
      }}
      style={{
        cursor: "pointer",
        opacity: dimmed ? 0.32 : live ? 1 : 0.72,
        transition: "opacity 0.35s",
        outline: "none",
      }}
      className="fg-node"
    >
      {/* selection halo */}
      {selected && (
        <Shape
          role={node.role}
          r={NODE_R + 7}
          fill="none"
          stroke={withAlpha(hue, 0.5)}
          strokeWidth={1.5}
          extra={{
            style: { filter: `drop-shadow(0 0 8px ${withAlpha(hue, 0.6)})` },
          }}
        />
      )}

      {/* body */}
      <Shape role={node.role} r={NODE_R} fill={COLORS.panel} stroke={live ? ring : COLORS.inkGhost} strokeWidth={1.5} />
      <Shape role={node.role} r={NODE_R} fill="url(#fg-node-core)" stroke="none" />
      {/* hue accent rim */}
      <Shape
        role={node.role}
        r={NODE_R}
        fill="none"
        stroke={withAlpha(hue, rimAlpha)}
        strokeWidth={selected ? 2 : 1.5}
        extra={{ style: { transition: "stroke 0.3s, stroke-width 0.3s" } }}
      />

      {/* role glyph in the center */}
      <CenterGlyph role={node.role} hue={live ? hue : COLORS.inkFaint} />

      {/* label below */}
      <text
        y={NODE_R + 16}
        textAnchor="middle"
        className="metric"
        style={{
          fill: selected ? COLORS.ink : live ? COLORS.inkMuted : COLORS.inkFaint,
          fontSize: 11,
          fontWeight: selected ? 600 : 500,
          transition: "fill 0.3s",
          pointerEvents: "none",
        }}
      >
        {node.label}
      </text>
      {/* status dot tucked at the node's shoulder — pulses when live */}
      <circle
        cx={NODE_R * 0.62}
        cy={-NODE_R * 0.62}
        r={3}
        fill={live ? ring : COLORS.inkGhost}
        stroke={COLORS.base}
        strokeWidth={1}
        style={{
          filter: live ? `drop-shadow(0 0 4px ${withAlpha(ring, 0.8)})` : "none",
        }}
      >
        {live && (
          <animate
            attributeName="opacity"
            values="1;0.45;1"
            dur="2.4s"
            repeatCount="indefinite"
          />
        )}
      </circle>
    </g>
  );
}

/** Draws the node outline in the shape that encodes its role. */
function Shape({
  role,
  r,
  fill,
  stroke,
  strokeWidth = 1,
  extra,
}: {
  role: "human" | "agent" | "service";
  r: number;
  fill: string;
  stroke: string;
  strokeWidth?: number;
  extra?: { style?: React.CSSProperties };
}) {
  const common = { fill, stroke, strokeWidth, ...extra };
  if (role === "agent") {
    return <circle cx={0} cy={0} r={r} {...common} />;
  }
  if (role === "service") {
    const s = r * 1.7;
    return (
      <rect x={-s / 2} y={-s / 2} width={s} height={s} rx={r * 0.32} {...common} />
    );
  }
  // human — diamond
  const d = r * 1.32;
  return (
    <path
      d={`M 0 ${-d} L ${d} 0 L 0 ${d} L ${-d} 0 Z`}
      strokeLinejoin="round"
      {...common}
    />
  );
}

function CenterGlyph({
  role,
  hue,
}: {
  role: "human" | "agent" | "service";
  hue: string;
}) {
  if (role === "human") {
    // operator mark
    return (
      <g stroke={hue} strokeWidth={1.6} fill="none" strokeLinecap="round">
        <circle cx={0} cy={-4} r={4} />
        <path d="M -6 8 C -6 2, 6 2, 6 8" />
      </g>
    );
  }
  if (role === "service") {
    // stacked db / server mark
    return (
      <g stroke={hue} strokeWidth={1.5} fill="none" strokeLinecap="round">
        <ellipse cx={0} cy={-5} rx={7} ry={2.6} />
        <path d="M -7 -5 V 5 C -7 6.6, 7 6.6, 7 5 V -5" />
        <path d="M -7 0 C -7 1.6, 7 1.6, 7 0" />
      </g>
    );
  }
  // agent — concentric "intelligence" dot
  return (
    <g fill="none" stroke={hue}>
      <circle cx={0} cy={0} r={6.5} strokeWidth={1.4} opacity={0.7} />
      <circle cx={0} cy={0} r={2.4} fill={hue} stroke="none" />
    </g>
  );
}

// ---------------------------------------------------------------- helpers ----

function hashString(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (h * 31 + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}
