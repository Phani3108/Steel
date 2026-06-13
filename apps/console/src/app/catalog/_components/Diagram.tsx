"use client";

import { motion } from "motion/react";
import { useMemo } from "react";

import { COLORS, SYSTEM_META, systemHue, withAlpha } from "@/lib/theme";
import {
  placeBays,
  SPINE,
  VIEW_H,
  VIEW_W,
  type CatalogSystem,
} from "./data";
import { PartNode } from "./PartNode";

interface DiagramProps {
  systems: CatalogSystem[];
  selected: string | null;
  hovered: string | null;
  onSelect: (name: string) => void;
  onHover: (name: string | null) => void;
}

/**
 * The exploded-vehicle blueprint. A central platform spine with six system bays
 * branching off it (three per side), each bay a labeled cluster of part nodes.
 * Bays connect to the spine with an L-shaped telemetry trace that energizes on
 * hover. Bespoke SVG — no chart library.
 */
export function Diagram({
  systems,
  selected,
  hovered,
  onSelect,
  onHover,
}: DiagramProps) {
  const bays = useMemo(() => placeBays(systems), [systems]);

  // Which bay (if any) is currently lit — by hovered/selected part.
  const litSystem = useMemo(() => {
    const name = hovered ?? selected;
    if (!name) return null;
    return systems.find((s) => s.parts.some((p) => p.name === name))?.system ?? null;
  }, [hovered, selected, systems]);

  return (
    <svg
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      className="w-full"
      style={{ display: "block" }}
      role="group"
      aria-label="JAI platform — exploded vehicle diagram"
    >
      <defs>
        <linearGradient id="spineGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={withAlpha(COLORS.accent, 0)} />
          <stop offset="12%" stopColor={withAlpha(COLORS.accent, 0.55)} />
          <stop offset="88%" stopColor={withAlpha(COLORS.accent, 0.55)} />
          <stop offset="100%" stopColor={withAlpha(COLORS.accent, 0)} />
        </linearGradient>
        <radialGradient id="hubGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor={withAlpha(COLORS.accent, 0.5)} />
          <stop offset="100%" stopColor={withAlpha(COLORS.accent, 0)} />
        </radialGradient>
      </defs>

      {/* ---- the platform spine ---- */}
      <motion.line
        x1={SPINE.x}
        y1={SPINE.top}
        x2={SPINE.x}
        y2={SPINE.bottom}
        stroke="url(#spineGrad)"
        strokeWidth={2}
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      />
      {/* spine end-caps + label */}
      <motion.g
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5, duration: 0.4 }}
      >
        <circle cx={SPINE.x} cy={SPINE.top} r={4} fill={COLORS.accent} />
        <circle cx={SPINE.x} cy={SPINE.bottom} r={4} fill={COLORS.accent} />
        <text
          x={SPINE.x}
          y={SPINE.top - 16}
          textAnchor="middle"
          style={{
            fill: COLORS.inkFaint,
            fontSize: 10,
            fontFamily: "var(--font-mono)",
            letterSpacing: "0.22em",
          }}
        >
          THE PLATFORM
        </text>
      </motion.g>

      {/* ---- bays ---- */}
      {bays.map((b, bi) => {
        const hue = systemHue(b.bay.system);
        const lit = litSystem === b.bay.system;
        const tagline = SYSTEM_META[b.bay.system].tagline;
        // L-trace: spine -> horizontal to inner edge -> small stub up to header
        const traceD = `M ${b.spineX} ${b.spineY} L ${b.innerEdgeX} ${b.spineY}`;

        return (
          <g key={b.bay.system}>
            {/* connector trace from spine to bay */}
            <motion.path
              d={traceD}
              fill="none"
              stroke={lit ? hue : withAlpha(hue, 0.35)}
              strokeWidth={lit ? 2 : 1.25}
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ delay: 0.4 + bi * 0.07, duration: 0.5 }}
              style={{ transition: "stroke 0.25s, stroke-width 0.25s" }}
            />
            {/* node where the trace meets the spine */}
            <circle
              cx={b.spineX}
              cy={b.spineY}
              r={lit ? 4.5 : 3}
              fill={lit ? hue : withAlpha(hue, 0.6)}
              style={{ transition: "r 0.2s, fill 0.2s" }}
            />
            {/* energy pulse along the trace when lit */}
            {lit && (
              <circle r={3} fill={hue}>
                <animateMotion dur="1.1s" repeatCount="indefinite" path={traceD} />
                <animate
                  attributeName="opacity"
                  values="0;1;0"
                  dur="1.1s"
                  repeatCount="indefinite"
                />
              </circle>
            )}

            {/* bay header */}
            <motion.g
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 + bi * 0.06, duration: 0.4 }}
            >
              <rect
                x={b.headerX}
                y={b.headerY}
                width={4}
                height={22}
                rx={2}
                fill={hue}
                style={{ filter: lit ? `drop-shadow(0 0 6px ${hue})` : "none" }}
              />
              <text
                x={b.headerX + 12}
                y={b.headerY + 11}
                style={{
                  fill: lit ? hue : withAlpha(hue, 0.85),
                  fontSize: 13,
                  fontFamily: "var(--font-mono)",
                  fontWeight: 600,
                  letterSpacing: "0.12em",
                }}
              >
                {b.bay.system}
              </text>
              <text
                x={b.headerX + 12}
                y={b.headerY + 24}
                style={{
                  fill: COLORS.inkFaint,
                  fontSize: 9.5,
                  fontFamily: "var(--font-mono)",
                  letterSpacing: "0.06em",
                }}
              >
                {tagline} · {b.parts.length}
              </text>
            </motion.g>

            {/* part nodes */}
            {b.parts.map((pp, pi) => (
              <PartNode
                key={pp.part.name}
                part={pp.part}
                x={pp.x}
                y={pp.y}
                selected={selected === pp.part.name}
                hovered={hovered === pp.part.name}
                index={bi * 5 + pi}
                onSelect={onSelect}
                onHover={onHover}
              />
            ))}
          </g>
        );
      })}
    </svg>
  );
}
