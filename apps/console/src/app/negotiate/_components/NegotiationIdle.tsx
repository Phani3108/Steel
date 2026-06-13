"use client";

import { motion } from "motion/react";

import { COLORS, withAlpha } from "@/lib/theme";

/**
 * Idle hero — the empty-table state. A bespoke SVG of the two parties facing
 * across a price corridor with the mandate cap drawn as a held rose line, so the
 * page tells the negotiator's safety story even before a deal is opened.
 */
export function NegotiationIdle() {
  const W = 520;
  const H = 240;
  const buyer = { x: 92, y: 96 };
  const seller = { x: W - 92, y: 96 };
  const capY = 168;

  return (
    <div className="flex flex-col items-center justify-center gap-5 py-6">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full max-w-lg"
        role="img"
        aria-label="An agent negotiator facing a seller across a price corridor, with the mandate cap held"
      >
        <defs>
          <radialGradient id="neg-idle-buyer" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={withAlpha(COLORS.accent, 0.45)} />
            <stop offset="100%" stopColor={withAlpha(COLORS.accent, 0)} />
          </radialGradient>
          <radialGradient id="neg-idle-seller" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={withAlpha(COLORS.danger, 0.4)} />
            <stop offset="100%" stopColor={withAlpha(COLORS.danger, 0)} />
          </radialGradient>
        </defs>

        {/* the bargaining line between the parties */}
        <line
          x1={buyer.x}
          y1={buyer.y}
          x2={seller.x}
          y2={seller.y}
          stroke={withAlpha(COLORS.inkFaint, 0.4)}
          strokeWidth={1}
          strokeDasharray="4 5"
        />
        {/* a buyer→seller probe packet */}
        <Packet x1={buyer.x} y1={buyer.y} x2={seller.x} y2={seller.y} color={COLORS.accent} delay={0} />
        {/* a seller→buyer counter packet */}
        <Packet x1={seller.x} y1={seller.y} x2={buyer.x} y2={buyer.y} color={COLORS.danger} delay={1.1} />

        {/* the mandate cap — a held rose rail beneath the table */}
        <line
          x1={48}
          y1={capY}
          x2={W - 48}
          y2={capY}
          stroke={COLORS.danger}
          strokeWidth={4}
          opacity={0.16}
          style={{ filter: "blur(2px)" }}
        />
        <line x1={48} y1={capY} x2={W - 48} y2={capY} stroke={COLORS.danger} strokeWidth={1.6} />
        <motion.line
          x1={48}
          y1={capY}
          x2={W - 48}
          y2={capY}
          stroke={COLORS.danger}
          strokeWidth={1.6}
          animate={{ opacity: [0.15, 0.6, 0.15] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
        />
        <g transform={`translate(${W / 2 - 7}, ${capY - 19})`}>
          <rect x={0} y={6} width={11} height={8} rx={1.5} stroke={COLORS.danger} strokeWidth={1.3} fill={COLORS.base} />
          <path d="M2.4 6V4.4a3 3 0 0 1 6 0V6" stroke={COLORS.danger} strokeWidth={1.3} fill="none" />
        </g>
        <text
          x={W / 2}
          y={capY + 22}
          fontSize={9.5}
          textAnchor="middle"
          className="metric"
          fill={COLORS.danger}
          style={{ letterSpacing: "0.12em" }}
        >
          MANDATE CAP — HELD
        </text>

        {/* buyer node */}
        <circle cx={buyer.x} cy={buyer.y} r={26} fill="url(#neg-idle-buyer)" />
        <circle cx={buyer.x} cy={buyer.y} r={13} fill={COLORS.base} stroke={COLORS.accent} strokeWidth={1.6} />
        <motion.circle
          cx={buyer.x}
          cy={buyer.y}
          r={13}
          fill="none"
          stroke={COLORS.accent}
          strokeWidth={1.2}
          animate={{ r: [13, 22], opacity: [0.5, 0] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: "easeOut" }}
        />
        <text x={buyer.x} y={buyer.y + 1} fontSize={8.5} textAnchor="middle" dominantBaseline="middle" className="metric" fill={COLORS.accent} fontWeight={700}>
          AGENT
        </text>
        <text x={buyer.x} y={buyer.y + 40} fontSize={10} textAnchor="middle" className="metric" fill={COLORS.inkFaint}>
          negotiator
        </text>

        {/* seller node */}
        <circle cx={seller.x} cy={seller.y} r={26} fill="url(#neg-idle-seller)" />
        <circle cx={seller.x} cy={seller.y} r={13} fill={COLORS.base} stroke={COLORS.danger} strokeWidth={1.6} />
        <text x={seller.x} y={seller.y + 1} fontSize={8.5} textAnchor="middle" dominantBaseline="middle" className="metric" fill={COLORS.danger} fontWeight={700}>
          SELLER
        </text>
        <text x={seller.x} y={seller.y + 40} fontSize={10} textAnchor="middle" className="metric" fill={COLORS.inkFaint}>
          counterparty
        </text>
      </svg>

      <div className="max-w-md text-center">
        <p className="text-sm leading-relaxed text-ink-muted">
          Pick an opponent and a list price, then open the negotiation. Watch the
          agent bargain the price down round by round — and refuse, every time, to
          cross its mandate cap.
        </p>
      </div>
    </div>
  );
}

/** A traveling packet of light along an edge. */
function Packet({
  x1,
  y1,
  x2,
  y2,
  color,
  delay,
}: {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  color: string;
  delay: number;
}) {
  return (
    <circle r={2.6} fill={color} style={{ filter: `drop-shadow(0 0 3px ${color})` }}>
      <animateMotion
        dur="2.2s"
        begin={`${delay}s`}
        repeatCount="indefinite"
        path={`M ${x1} ${y1} L ${x2} ${y2}`}
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
