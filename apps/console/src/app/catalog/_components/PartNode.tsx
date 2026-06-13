"use client";

import { motion } from "motion/react";

import {
  autonomyColor,
  COLORS,
  statusColor,
  systemHue,
  withAlpha,
} from "@/lib/theme";
import { NODE, type CatalogPart } from "./data";

interface PartNodeProps {
  part: CatalogPart;
  x: number;
  y: number;
  selected: boolean;
  hovered: boolean;
  /** Stagger index for entrance animation. */
  index: number;
  onSelect: (name: string) => void;
  onHover: (name: string | null) => void;
}

/**
 * One part rendered as an SVG instrument node inside the exploded-vehicle
 * diagram. Agents carry a status-tinted left rail + autonomy pips + a tiny
 * pass-rate arc; infrastructure parts are quieter. Pure SVG, theme-driven.
 */
export function PartNode({
  part,
  x,
  y,
  selected,
  hovered,
  index,
  onSelect,
  onHover,
}: PartNodeProps) {
  const { w, h } = NODE;
  const hue = systemHue(part.system);
  const sColor = statusColor(part.status);
  const active = selected || hovered;

  // Short label — drop the redundant prefix for readability.
  const label = part.name;

  const fill = selected
    ? withAlpha(hue, 0.16)
    : hovered
      ? withAlpha(hue, 0.1)
      : COLORS.panel;
  const stroke = active ? withAlpha(hue, 0.75) : COLORS.line;

  const pass = part.scorecard?.pass_rate ?? null;

  return (
    <motion.g
      role="button"
      tabIndex={0}
      aria-label={`${part.name} — ${part.status}`}
      style={{ cursor: "pointer", outline: "none" }}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.18 + index * 0.012, ease: [0.22, 1, 0.36, 1] }}
      onClick={() => onSelect(part.name)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect(part.name);
        }
      }}
      onMouseEnter={() => onHover(part.name)}
      onMouseLeave={() => onHover(null)}
      onFocus={() => onHover(part.name)}
      onBlur={() => onHover(null)}
    >
      {/* selection glow */}
      {selected && (
        <rect
          x={x - 2}
          y={y - 2}
          width={w + 4}
          height={h + 4}
          rx={9}
          fill="none"
          stroke={withAlpha(hue, 0.4)}
          strokeWidth={1.5}
        />
      )}
      <motion.rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={7}
        fill={fill}
        stroke={stroke}
        strokeWidth={1}
        animate={{
          filter: active
            ? `drop-shadow(0 4px 14px ${withAlpha(hue, 0.28)})`
            : "drop-shadow(0 1px 2px rgba(0,0,0,0.4))",
        }}
        transition={{ duration: 0.2 }}
      />

      {/* status rail on the left edge */}
      <rect
        x={x}
        y={y}
        width={3}
        height={h}
        rx={1.5}
        fill={part.isAgent ? sColor : withAlpha(hue, 0.55)}
      />
      {part.status === "active" && part.isAgent && (
        <circle cx={x + 1.5} cy={y + h - 6} r={2} fill={sColor}>
          <animate
            attributeName="opacity"
            values="1;0.3;1"
            dur="1.8s"
            repeatCount="indefinite"
          />
        </circle>
      )}

      {/* name */}
      <text
        x={x + 11}
        y={y + (part.isAgent ? 14 : 21)}
        style={{
          fill: active ? COLORS.ink : COLORS.inkMuted,
          fontSize: 11,
          fontFamily: "var(--font-mono)",
          fontWeight: 500,
          letterSpacing: "-0.01em",
        }}
      >
        {label}
      </text>

      {/* agent sub-row: autonomy pips + status dot */}
      {part.isAgent && (
        <g transform={`translate(${x + 11}, ${y + 23})`}>
          {[1, 2, 3, 4, 5].map((lvl) => {
            const on = lvl <= (part.autonomy_level ?? 0);
            return (
              <rect
                key={lvl}
                x={(lvl - 1) * 7}
                y={0}
                width={5}
                height={4}
                rx={1}
                fill={on ? autonomyColor(part.autonomy_level) : COLORS.lineStrong}
              />
            );
          })}
          <text
            x={42}
            y={4}
            style={{
              fill: COLORS.inkFaint,
              fontSize: 8.5,
              fontFamily: "var(--font-mono)",
              letterSpacing: "0.04em",
            }}
          >
            {(part.pipeline ?? "").toUpperCase()}
          </text>
        </g>
      )}

      {/* pass-rate mini arc for scored agents */}
      {part.isAgent && pass !== null && (
        <g transform={`translate(${x + w - 18}, ${y + h / 2})`}>
          <circle
            r={8}
            fill="none"
            stroke={withAlpha(COLORS.ok, 0.14)}
            strokeWidth={2.5}
          />
          <circle
            r={8}
            fill="none"
            stroke={
              pass >= 0.85 ? COLORS.ok : pass >= 0.6 ? COLORS.warn : COLORS.danger
            }
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeDasharray={`${2 * Math.PI * 8 * pass} ${2 * Math.PI * 8}`}
            transform="rotate(-90)"
          />
          <text
            y={2.5}
            textAnchor="middle"
            style={{
              fill: COLORS.inkMuted,
              fontSize: 7,
              fontFamily: "var(--font-mono)",
            }}
          >
            {Math.round(pass * 100)}
          </text>
        </g>
      )}

      {/* non-agent: tiny status glyph at right */}
      {!part.isAgent && (
        <circle
          cx={x + w - 12}
          cy={y + h / 2}
          r={3}
          fill={withAlpha(sColor, 0.9)}
        />
      )}
    </motion.g>
  );
}
