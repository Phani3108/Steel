"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { AuditEvent } from "@/lib/api";
import { fmtTs } from "@/lib/api";
import { COLORS, outcomeColor, systemHue, withAlpha } from "@/lib/theme";

import { resolveAgent, type AgentMeta } from "./agents";

/**
 * RunReplay — THE innovative instrument of the single-run view.
 *
 * It lays out every agent this run touched as system-hued glyphs on a ring, then
 * *replays the actual run*: each audit event becomes a stop, and a packet travels
 * from agent to agent in the true recorded order, leaving a lit trail behind it.
 * You literally watch the procurement flow across the fleet — the orchestrator
 * lighting up its specialists, the hop into sourcing, the handoff back.
 *
 * Everything is derived from `events` (chronological). No external animation lib
 * beyond CSS — the packet is positioned each tick from a self-paced clock, so
 * play / pause / scrub stays in our hands and respects reduced-motion.
 */

interface ReplayStop {
  /** Index into the events array this stop corresponds to. */
  eventIndex: number;
  /** The agent id active at this stop. */
  agentId: string;
  action: string;
  outcome: AuditEvent["outcome"];
  ts: string;
}

interface RunReplayProps {
  events: AuditEvent[];
  /** Fallback agent roster when events carry no agent field. */
  agents: string[];
}

const VIEW_W = 560;
const VIEW_H = 320;
const CENTER = { x: VIEW_W / 2, y: VIEW_H / 2 + 6 };
const NODE_R = 17;
/** Milliseconds the packet spends travelling between two stops. */
const HOP_MS = 1100;
/** Pause held on each node before departing for the next. */
const DWELL_MS = 320;

/** Lay agents out evenly around a ring; the human/origin sits at top. */
function ringLayout(metas: AgentMeta[]): Record<string, { x: number; y: number }> {
  const n = metas.length;
  const pos: Record<string, { x: number; y: number }> = {};
  if (n === 1) {
    pos[metas[0].id] = { x: CENTER.x, y: CENTER.y };
    return pos;
  }
  const rx = VIEW_W / 2 - NODE_R - 64;
  const ry = VIEW_H / 2 - NODE_R - 30;
  // Start at the top (-90°) so the operator/origin anchors the crown.
  for (let i = 0; i < n; i++) {
    const a = -Math.PI / 2 + (i / n) * Math.PI * 2;
    pos[metas[i].id] = {
      x: CENTER.x + Math.cos(a) * rx,
      y: CENTER.y + Math.sin(a) * ry,
    };
  }
  return pos;
}

export function RunReplay({ events, agents }: RunReplayProps) {
  // ---- derive the ordered list of stops + the unique agent roster ----
  const { stops, metas } = useMemo(() => {
    const seq: ReplayStop[] = [];
    let lastAgent: string | null = null;
    events.forEach((e, i) => {
      const agentId = e.agent ?? lastAgent ?? "human";
      // Collapse consecutive events on the same agent into one visual stop,
      // but keep the latest action/outcome so the readout tracks the run.
      if (seq.length > 0 && seq[seq.length - 1].agentId === agentId) {
        seq[seq.length - 1] = {
          eventIndex: i,
          agentId,
          action: e.action,
          outcome: e.outcome,
          ts: e.ts,
        };
      } else {
        seq.push({ eventIndex: i, agentId, action: e.action, outcome: e.outcome, ts: e.ts });
      }
      lastAgent = agentId;
    });

    // Roster = every agent that appears, in first-seen order, seeded with the
    // run's declared agents so even un-hopped specialists show on the ring.
    const order: string[] = [];
    const push = (id: string) => {
      if (!order.includes(id)) order.push(id);
    };
    // Origin first if any stop starts at the human.
    if (seq.some((s) => s.agentId === "human")) push("human");
    seq.forEach((s) => push(s.agentId));
    agents.forEach(push);

    return { stops: seq, metas: order.map(resolveAgent) };
  }, [events, agents]);

  const pos = useMemo(() => ringLayout(metas), [metas]);
  const hopCount = Math.max(0, stops.length - 1);

  // ---- the self-paced replay clock ----
  const [playing, setPlaying] = useState(true);
  // progress is a float in [0, hopCount]; integer part = current stop index.
  const [progress, setProgress] = useState(0);
  const rafRef = useRef<number | null>(null);
  const lastTsRef = useRef<number | null>(null);

  const reduceMotion =
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  // Reset the clock when the run's shape changes — done at render time (the same
  // idiom usePoll uses) rather than in an effect, which would cascade renders.
  const [shapeKey, setShapeKey] = useState(hopCount);
  if (shapeKey !== hopCount) {
    setShapeKey(hopCount);
    setProgress(0);
    setPlaying(!reduceMotion && hopCount > 0);
  }

  useEffect(() => {
    if (!playing || hopCount === 0) return;
    const cycle = HOP_MS + DWELL_MS;
    const step = (now: number) => {
      if (lastTsRef.current == null) lastTsRef.current = now;
      const dt = now - lastTsRef.current;
      lastTsRef.current = now;
      setProgress((p) => {
        let np = p + dt / cycle;
        if (np >= hopCount) np = 0; // loop the replay
        return np;
      });
      rafRef.current = requestAnimationFrame(step);
    };
    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
      lastTsRef.current = null;
    };
  }, [playing, hopCount]);

  // ---- packet position + active stop from progress ----
  const segIdx = Math.min(Math.floor(progress), Math.max(0, hopCount - 1));
  // Within-segment t, with a dwell hold at the arrival node.
  const cycle = HOP_MS + DWELL_MS;
  const localMs = (progress - segIdx) * cycle;
  const travelT = Math.min(1, localMs / HOP_MS); // 0..1 during travel, then 1 during dwell
  const eased = easeInOut(travelT);

  const fromStop = stops[segIdx];
  const toStop = stops[Math.min(segIdx + 1, stops.length - 1)];
  // The "current" stop the readout describes is the arrival end once we're past
  // the midpoint, else the departure end — feels like the packet "lands".
  const activeStop = hopCount === 0 ? stops[0] : eased > 0.5 ? toStop : fromStop;

  const fromPos = fromStop ? pos[fromStop.agentId] : CENTER;
  const toPos = toStop ? pos[toStop.agentId] : CENTER;
  const packet =
    fromPos && toPos
      ? { x: lerp(fromPos.x, toPos.x, eased), y: lerp(fromPos.y, toPos.y, eased) }
      : CENTER;

  // Which agents have been "visited" up to (and including) the active stop —
  // drives the lit/dim state of nodes and the trail edges.
  const visitedUpto = hopCount === 0 ? 0 : eased > 0.5 ? segIdx + 1 : segIdx;

  const hue = activeStop ? systemHue(resolveAgent(activeStop.agentId).system) : COLORS.accent;

  if (stops.length === 0) {
    return (
      <div className="flex h-44 items-center justify-center text-center text-xs text-ink-faint">
        no hops to replay — this run left no agent trail
      </div>
    );
  }

  return (
    <div>
      <div className="relative">
        <svg
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          width="100%"
          style={{ display: "block" }}
          role="group"
          aria-label="Run replay — agents this run touched and the path it took"
        >
          <defs>
            <radialGradient id="rr-core" cx="50%" cy="38%" r="65%">
              <stop offset="0%" stopColor={withAlpha(COLORS.ink, 0.16)} />
              <stop offset="100%" stopColor={withAlpha(COLORS.base, 0)} />
            </radialGradient>
          </defs>

          {/* ---- trail edges: each hop in the true sequence ---- */}
          <g>
            {stops.slice(0, -1).map((s, i) => {
              const a = pos[s.agentId];
              const b = pos[stops[i + 1].agentId];
              if (!a || !b) return null;
              const lit = i < visitedUpto;
              const c = outcomeColor(stops[i + 1].outcome);
              return (
                <line
                  key={`edge-${i}`}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke={lit ? withAlpha(c, 0.55) : withAlpha(COLORS.line, 0.8)}
                  strokeWidth={lit ? 1.6 : 1}
                  strokeLinecap="round"
                  style={{ transition: "stroke 0.4s, stroke-width 0.4s" }}
                />
              );
            })}
          </g>

          {/* ---- agent nodes on the ring ---- */}
          <g>
            {metas.map((m) => {
              const p = pos[m.id];
              if (!p) return null;
              const nodeHue = systemHue(m.system);
              const isActive = activeStop?.agentId === m.id;
              // A node is "touched" once the sequence has reached it.
              const touched = stops
                .slice(0, visitedUpto + 1)
                .some((s) => s.agentId === m.id);
              return (
                <g
                  key={m.id}
                  transform={`translate(${p.x} ${p.y})`}
                  style={{ transition: "opacity 0.35s" }}
                  opacity={touched ? 1 : 0.42}
                >
                  {isActive && (
                    <NodeShape
                      role={m.role}
                      r={NODE_R + 6}
                      fill="none"
                      stroke={withAlpha(nodeHue, 0.55)}
                      strokeWidth={1.5}
                      style={{ filter: `drop-shadow(0 0 7px ${withAlpha(nodeHue, 0.6)})` }}
                    />
                  )}
                  <NodeShape role={m.role} r={NODE_R} fill={COLORS.panel} stroke={withAlpha(nodeHue, 0.5)} strokeWidth={1.4} />
                  <NodeShape role={m.role} r={NODE_R} fill="url(#rr-core)" stroke="none" />
                  <NodeShape
                    role={m.role}
                    r={NODE_R}
                    fill="none"
                    stroke={withAlpha(nodeHue, touched ? 0.9 : 0.6)}
                    strokeWidth={isActive ? 2 : 1.4}
                    style={{ transition: "stroke 0.3s, stroke-width 0.3s" }}
                  />
                  <CenterGlyph role={m.role} hue={nodeHue} />
                  <text
                    y={NODE_R + 14}
                    textAnchor="middle"
                    className="metric"
                    style={{
                      fill: isActive ? COLORS.ink : COLORS.inkMuted,
                      fontSize: 10,
                      fontWeight: isActive ? 600 : 500,
                      transition: "fill 0.3s",
                      pointerEvents: "none",
                    }}
                  >
                    {m.label}
                  </text>
                </g>
              );
            })}
          </g>

          {/* ---- the travelling packet ---- */}
          {hopCount > 0 && (
            <circle
              cx={packet.x}
              cy={packet.y}
              r={4}
              fill={hue}
              style={{ filter: `drop-shadow(0 0 6px ${withAlpha(hue, 0.95)})` }}
            />
          )}
        </svg>
      </div>

      {/* ---- transport + readout ---- */}
      <div className="flex items-center gap-3 border-t border-line px-4 py-2.5">
        <button
          type="button"
          onClick={() => {
            if (hopCount === 0) return;
            lastTsRef.current = null;
            setPlaying((v) => !v);
          }}
          disabled={hopCount === 0}
          aria-label={playing ? "pause replay" : "play replay"}
          className="focus-ring flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-line text-ink-muted transition-colors hover:text-ink disabled:opacity-40"
        >
          {playing ? (
            <svg width="11" height="11" viewBox="0 0 24 24" aria-hidden>
              <rect x="6" y="5" width="4" height="14" rx="1" fill="currentColor" />
              <rect x="14" y="5" width="4" height="14" rx="1" fill="currentColor" />
            </svg>
          ) : (
            <svg width="11" height="11" viewBox="0 0 24 24" aria-hidden>
              <path d="M7 5l12 7-12 7V5z" fill="currentColor" />
            </svg>
          )}
        </button>

        {/* scrubber */}
        <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-panel-2">
          <div
            className="absolute inset-y-0 left-0 rounded-full"
            style={{
              width: `${hopCount === 0 ? 100 : (progress / hopCount) * 100}%`,
              background: `linear-gradient(to right, ${withAlpha(COLORS.accent, 0.5)}, ${hue})`,
              transition: "width 0.08s linear",
            }}
          />
        </div>

        {/* live readout of the active stop */}
        <div className="flex min-w-0 shrink-0 items-center gap-2">
          <span
            className="h-1.5 w-1.5 shrink-0 rounded-full"
            style={{ background: outcomeColor(activeStop?.outcome) }}
            aria-hidden
          />
          <span className="metric max-w-[14rem] truncate text-[11px] text-ink">
            {activeStop?.action ?? "—"}
          </span>
          <span className="metric hidden text-[10px] text-ink-faint sm:inline">
            {fmtTs(activeStop?.ts)}
          </span>
        </div>
      </div>

      <p className="px-4 pb-3 text-[10.5px] leading-relaxed text-ink-faint">
        {hopCount === 0
          ? "A single-agent run — the packet rests at the one agent that handled it."
          : `Replaying ${hopCount} hop${hopCount === 1 ? "" : "s"} across ${metas.length} agents, in the exact order the recorder logged them.`}
      </p>
    </div>
  );
}

// ----------------------------------------------------------------- glyphs ----

function NodeShape({
  role,
  r,
  fill,
  stroke,
  strokeWidth = 1,
  style,
}: {
  role: "human" | "agent" | "service";
  r: number;
  fill: string;
  stroke: string;
  strokeWidth?: number;
  style?: React.CSSProperties;
}) {
  const common = { fill, stroke, strokeWidth, style };
  if (role === "service") {
    const s = r * 1.7;
    return <rect x={-s / 2} y={-s / 2} width={s} height={s} rx={r * 0.32} {...common} />;
  }
  if (role === "human") {
    const d = r * 1.32;
    return <path d={`M 0 ${-d} L ${d} 0 L 0 ${d} L ${-d} 0 Z`} strokeLinejoin="round" {...common} />;
  }
  return <circle cx={0} cy={0} r={r} {...common} />;
}

function CenterGlyph({ role, hue }: { role: "human" | "agent" | "service"; hue: string }) {
  if (role === "human") {
    return (
      <g stroke={hue} strokeWidth={1.5} fill="none" strokeLinecap="round">
        <circle cx={0} cy={-3} r={3.2} />
        <path d="M -5 6 C -5 1.5, 5 1.5, 5 6" />
      </g>
    );
  }
  if (role === "service") {
    return (
      <g stroke={hue} strokeWidth={1.4} fill="none" strokeLinecap="round">
        <ellipse cx={0} cy={-4} rx={5.5} ry={2.1} />
        <path d="M -5.5 -4 V 4 C -5.5 5.3, 5.5 5.3, 5.5 4 V -4" />
        <path d="M -5.5 0 C -5.5 1.3, 5.5 1.3, 5.5 0" />
      </g>
    );
  }
  return (
    <g fill="none" stroke={hue}>
      <circle cx={0} cy={0} r={5} strokeWidth={1.3} opacity={0.7} />
      <circle cx={0} cy={0} r={1.9} fill={hue} stroke="none" />
    </g>
  );
}

// ----------------------------------------------------------------- math ----

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function easeInOut(t: number): number {
  return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
}
