"use client";

import { motion } from "motion/react";

import { COLORS, systemHue, withAlpha } from "@/lib/theme";

/** The specialists the orchestrator fans out to (matches the reference topology). */
const SPECIALISTS = [
  { id: "agent-intake-triage", label: "Triage" },
  { id: "agent-risk-sentinel", label: "Risk" },
  { id: "agent-spend-analyst", label: "Spend" },
  { id: "agent-sourcing", label: "Sourcing" },
] as const;

/**
 * Idle hero — a bespoke SVG of the orchestrator fanning out to its specialists,
 * with a packet of light traveling each spoke on a loop. Shown when no mission
 * is running, so the empty state still tells the STEEL-Orchestrator story.
 */
export function FanoutDiagram() {
  const W = 520;
  const H = 230;
  const human = { x: 48, y: H / 2 };
  const orch = { x: 200, y: H / 2 };
  const netHue = systemHue("NETWORK");

  // distribute specialists vertically on the right
  const rightX = 430;
  const ys = SPECIALISTS.map(
    (_, i) => 40 + (i * (H - 80)) / (SPECIALISTS.length - 1),
  );

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="h-auto w-full"
      role="img"
      aria-label="Orchestrator fan-out topology"
    >
      <defs>
        <radialGradient id="orch-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor={withAlpha(netHue, 0.5)} />
          <stop offset="100%" stopColor={withAlpha(netHue, 0)} />
        </radialGradient>
      </defs>

      {/* human → orchestrator */}
      <line
        x1={human.x}
        y1={human.y}
        x2={orch.x}
        y2={orch.y}
        stroke={withAlpha(COLORS.accent, 0.35)}
        strokeWidth={1.2}
      />
      <Packet
        x1={human.x}
        y1={human.y}
        x2={orch.x}
        y2={orch.y}
        color={COLORS.accent}
        delay={0}
      />

      {/* orchestrator → specialists */}
      {SPECIALISTS.map((s, i) => {
        const hue = systemHue("NETWORK");
        const ty = ys[i];
        return (
          <g key={s.id}>
            <path
              d={spoke(orch.x, orch.y, rightX, ty)}
              fill="none"
              stroke={withAlpha(hue, 0.3)}
              strokeWidth={1.2}
            />
            <Packet
              curved
              x1={orch.x}
              y1={orch.y}
              x2={rightX}
              y2={ty}
              color={hue}
              delay={0.4 + i * 0.22}
            />
            {/* specialist node */}
            <g>
              <circle
                cx={rightX}
                cy={ty}
                r={6}
                fill={COLORS.base}
                stroke={hue}
                strokeWidth={1.4}
              />
              <motion.circle
                cx={rightX}
                cy={ty}
                r={6}
                fill="none"
                stroke={hue}
                strokeWidth={1.2}
                animate={{ r: [6, 12], opacity: [0.6, 0] }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  delay: 0.4 + i * 0.22,
                  ease: "easeOut",
                }}
              />
              <text
                x={rightX + 13}
                y={ty + 3.5}
                fontSize={11}
                className="metric"
                fill={COLORS.inkMuted}
              >
                {s.label}
              </text>
            </g>
          </g>
        );
      })}

      {/* human node */}
      <circle cx={human.x} cy={human.y} r={5} fill={COLORS.accent} />
      <text
        x={human.x}
        y={human.y + 20}
        fontSize={10}
        textAnchor="middle"
        className="metric"
        fill={COLORS.inkFaint}
      >
        you
      </text>

      {/* orchestrator node */}
      <circle cx={orch.x} cy={orch.y} r={26} fill="url(#orch-glow)" />
      <circle
        cx={orch.x}
        cy={orch.y}
        r={13}
        fill={COLORS.base}
        stroke={netHue}
        strokeWidth={1.6}
      />
      <motion.circle
        cx={orch.x}
        cy={orch.y}
        r={13}
        fill="none"
        stroke={netHue}
        strokeWidth={1.2}
        animate={{ r: [13, 22], opacity: [0.5, 0] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: "easeOut" }}
      />
      <text
        x={orch.x}
        y={orch.y + 1}
        fontSize={9}
        textAnchor="middle"
        dominantBaseline="middle"
        className="metric"
        fill={netHue}
        fontWeight={600}
      >
        ORCH
      </text>
      <text
        x={orch.x}
        y={orch.y + 40}
        fontSize={10}
        textAnchor="middle"
        className="metric"
        fill={COLORS.inkFaint}
      >
        orchestrator
      </text>
    </svg>
  );
}

/** A quadratic spoke from the orchestrator out to a specialist. */
function spoke(x1: number, y1: number, x2: number, y2: number): string {
  const cx = (x1 + x2) / 2 + 18;
  return `M ${x1} ${y1} Q ${cx} ${y1} ${x2} ${y2}`;
}

/** A traveling packet of light along a (optionally curved) edge. */
function Packet({
  x1,
  y1,
  x2,
  y2,
  color,
  delay,
  curved = false,
}: {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  color: string;
  delay: number;
  curved?: boolean;
}) {
  const path = curved ? spoke(x1, y1, x2, y2) : `M ${x1} ${y1} L ${x2} ${y2}`;
  return (
    <circle r={2.4} fill={color} style={{ filter: `drop-shadow(0 0 3px ${color})` }}>
      <animateMotion
        dur="2.2s"
        begin={`${delay}s`}
        repeatCount="indefinite"
        path={path}
        keyPoints="0;1"
        keyTimes="0;1"
      />
      <animate
        attributeName="opacity"
        values="0;1;1;0"
        keyTimes="0;0.15;0.85;1"
        dur="2.2s"
        begin={`${delay}s`}
        repeatCount="indefinite"
      />
    </circle>
  );
}
