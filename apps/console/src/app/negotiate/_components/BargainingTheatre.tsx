"use client";

import { motion } from "motion/react";

import { COLORS, withAlpha } from "@/lib/theme";
import { deriveBand, fmtK, type NegotiationState } from "./demo";

/**
 * THE BARGAINING THEATRE — the P4 hero.
 *
 * A bespoke SVG with a vertical price axis (list price at the crown, descending).
 * The agent's mandate is drawn as a ZOPA band: a TARGET line (accent), a
 * WALK-AWAY line (warn), and the HARD CAP (rose) — the line the negotiator may
 * never cross. The transcript rolls in: buyer offers rise from the floor on the
 * left, seller counters fall from list on the right, each round drawn as a
 * stepped pair converging toward the center.
 *
 * On a deal they meet at a green seal under the cap. On a WALK-AWAY the cap line
 * holds, the buyer's last offer is pinned just beneath it, the seller's counter
 * floats above it out of reach, and the agent walks — "constraint violations: 0".
 */
interface BargainingTheatreProps {
  state: NegotiationState;
}

const W = 720;
const H = 460;
const PAD_TOP = 54;
const PAD_BOTTOM = 56;
const AXIS_X = 86; // the price axis rail
const LANE_BUYER = 250; // buyer-offer lane (left of center)
const LANE_SELLER = W - 150; // seller-counter lane (right)
const CENTER_X = (LANE_BUYER + LANE_SELLER) / 2;

export function BargainingTheatre({ state }: BargainingTheatreProps) {
  const { result, revealed } = state;
  const list = result.list_price;
  const band = deriveBand(list, result.mandate_cap);

  // Price → Y. Top of plot = list; bottom = a touch below the lowest interesting
  // price (target / cap / any offer), so everything stays comfortably in frame.
  const allPrices = [
    list,
    band.target,
    band.walkaway,
    band.cap,
    ...result.transcript.flatMap((t) => [t.offer, t.counter]),
    result.final_price ?? list,
  ].filter((n): n is number => typeof n === "number" && !Number.isNaN(n));
  const pHi = Math.max(...allPrices, list);
  const pLo = Math.min(...allPrices) * 0.985;
  const span = Math.max(pHi - pLo, 1);

  const yTop = PAD_TOP;
  const yBot = H - PAD_BOTTOM;
  const yOf = (price: number) =>
    yTop + ((pHi - price) / span) * (yBot - yTop);

  const visible = result.transcript.slice(0, revealed);
  const walked = result.status === "walked";
  const settled = state.verdictReady;
  const dealY = result.final_price != null ? yOf(result.final_price) : null;

  // axis ticks: a handful of round prices across the visible range
  const ticks = buildTicks(pLo, pHi);

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="h-auto w-full"
      role="img"
      aria-label="Negotiation bargaining theatre — price axis with mandate band and round-by-round offers"
    >
      <defs>
        <linearGradient id="neg-zopa" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={withAlpha(COLORS.accent, 0.16)} />
          <stop offset="100%" stopColor={withAlpha(COLORS.accent, 0.02)} />
        </linearGradient>
        <linearGradient id="neg-breach" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={withAlpha(COLORS.danger, 0.18)} />
          <stop offset="100%" stopColor={withAlpha(COLORS.danger, 0.04)} />
        </linearGradient>
        <radialGradient id="neg-deal" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor={withAlpha(COLORS.ok, 0.55)} />
          <stop offset="100%" stopColor={withAlpha(COLORS.ok, 0)} />
        </radialGradient>
      </defs>

      {/* ===================== the FORBIDDEN ZONE (above the cap) ===================== */}
      {/* Everything above the cap line is off-limits to the agent. Tint it rose. */}
      <rect
        x={AXIS_X}
        y={yTop - 8}
        width={W - AXIS_X - 16}
        height={yOf(band.cap) - (yTop - 8)}
        fill="url(#neg-breach)"
        opacity={0.6}
      />
      {/* the negotiable corridor (cap down to the floor) */}
      <rect
        x={AXIS_X}
        y={yOf(band.cap)}
        width={W - AXIS_X - 16}
        height={yBot - yOf(band.cap)}
        fill="url(#neg-zopa)"
        opacity={0.5}
      />

      {/* ===================== price axis ===================== */}
      <line
        x1={AXIS_X}
        y1={yTop - 8}
        x2={AXIS_X}
        y2={yBot + 6}
        stroke={COLORS.lineStrong}
        strokeWidth={1}
      />
      {ticks.map((p) => (
        <g key={p}>
          <line
            x1={AXIS_X - 4}
            y1={yOf(p)}
            x2={AXIS_X}
            y2={yOf(p)}
            stroke={COLORS.inkFaint}
            strokeWidth={1}
          />
          <text
            x={AXIS_X - 9}
            y={yOf(p) + 3.5}
            fontSize={10}
            textAnchor="end"
            className="metric"
            fill={COLORS.inkFaint}
          >
            {fmtK(p)}
          </text>
        </g>
      ))}
      <text
        x={AXIS_X - 9}
        y={yTop - 22}
        fontSize={9}
        textAnchor="end"
        className="metric"
        fill={COLORS.inkGhost}
        style={{ letterSpacing: "0.12em" }}
      >
        PRICE
      </text>

      {/* ===================== mandate markers ===================== */}
      <MandateLine
        y={yOf(list)}
        label="list"
        sub={fmtK(list)}
        color={COLORS.inkMuted}
        dashed
      />
      <MandateLine
        y={yOf(band.target)}
        label="target"
        sub={fmtK(band.target)}
        color={COLORS.accent}
      />
      <MandateLine
        y={yOf(band.walkaway)}
        label="walk-away"
        sub={fmtK(band.walkaway)}
        color={COLORS.warn}
        dashed
      />
      {/* THE HARD CAP — the dramatic line. Bold, rose, with a guard glyph. */}
      <CapLine y={yOf(band.cap)} value={band.cap} pulse={!settled} walked={walked} />

      {/* ===================== lane headers ===================== */}
      <text
        x={LANE_BUYER}
        y={yTop - 22}
        fontSize={10}
        textAnchor="middle"
        className="metric"
        fill={COLORS.accent}
        style={{ letterSpacing: "0.1em" }}
      >
        ◤ BUYER
      </text>
      <text
        x={LANE_SELLER}
        y={yTop - 22}
        fontSize={10}
        textAnchor="middle"
        className="metric"
        fill={COLORS.danger}
        style={{ letterSpacing: "0.1em" }}
      >
        SELLER ◢
      </text>

      {/* ===================== the rounds ===================== */}
      {visible.map((turn, i) => {
        const rowFrac = visible.length > 1 ? i / (visible.length - 1) : 0;
        // Each round nudges slightly inward toward center as it progresses,
        // visually telegraphing convergence even before prices meet.
        const inward = rowFrac * 36;
        const bx = LANE_BUYER + inward;
        const sx = LANE_SELLER - inward;
        const by = yOf(turn.offer);
        const sy = yOf(turn.counter);
        const isLast = i === visible.length - 1;
        const accepts = turn.action === "seller_accepts";

        return (
          <g key={turn.round}>
            {/* connecting tie between this round's offer and counter (the gap) */}
            <motion.line
              x1={bx}
              y1={by}
              x2={sx}
              y2={sy}
              stroke={withAlpha(
                accepts ? COLORS.ok : COLORS.inkFaint,
                accepts ? 0.55 : 0.28,
              )}
              strokeWidth={accepts ? 1.6 : 1}
              strokeDasharray={accepts ? undefined : "3 4"}
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 0.45, delay: 0.08 }}
            />

            {/* buyer offer node (steps UP toward the seller across rounds) */}
            <OfferNode
              x={bx}
              y={by}
              round={turn.round}
              price={turn.offer}
              color={COLORS.accent}
              side="left"
              emphasize={isLast}
            />
            {/* seller counter node (steps DOWN toward the buyer) — hidden when they accept */}
            {!accepts && (
              <OfferNode
                x={sx}
                y={sy}
                round={turn.round}
                price={turn.counter}
                color={COLORS.danger}
                side="right"
                emphasize={isLast}
              />
            )}
          </g>
        );
      })}

      {/* ===================== verdict ===================== */}
      {settled && !walked && dealY != null && (
        <DealSeal
          x={CENTER_X}
          y={dealY}
          price={result.final_price as number}
          savings={result.savings_pct}
        />
      )}
      {settled && walked && (
        <WalkAway capY={yOf(band.cap)} />
      )}
    </svg>
  );
}

// ----------------------------------------------------------- sub-parts ----

function MandateLine({
  y,
  label,
  sub,
  color,
  dashed = false,
}: {
  y: number;
  label: string;
  sub: string;
  color: string;
  dashed?: boolean;
}) {
  return (
    <g>
      <line
        x1={AXIS_X}
        y1={y}
        x2={W - 16}
        y2={y}
        stroke={withAlpha(color, 0.5)}
        strokeWidth={1}
        strokeDasharray={dashed ? "4 5" : undefined}
      />
      <text
        x={W - 16}
        y={y - 5}
        fontSize={9.5}
        textAnchor="end"
        className="metric"
        fill={color}
        style={{ letterSpacing: "0.08em" }}
      >
        {label.toUpperCase()} · {sub}
      </text>
    </g>
  );
}

/** The hard mandate cap — a bold rose rail with a lock, pulsing while live. */
function CapLine({
  y,
  value,
  pulse,
  walked,
}: {
  y: number;
  value: number;
  pulse: boolean;
  walked: boolean;
}) {
  const c = COLORS.danger;
  return (
    <g>
      {/* glow underlay so the line reads as a force-field */}
      <line
        x1={AXIS_X}
        y1={y}
        x2={W - 16}
        y2={y}
        stroke={c}
        strokeWidth={walked ? 6 : 4}
        opacity={0.18}
        style={{ filter: `blur(2px)` }}
      />
      <line
        x1={AXIS_X}
        y1={y}
        x2={W - 16}
        y2={y}
        stroke={c}
        strokeWidth={1.8}
      />
      {pulse && (
        <motion.line
          x1={AXIS_X}
          y1={y}
          x2={W - 16}
          y2={y}
          stroke={c}
          strokeWidth={1.8}
          animate={{ opacity: [0.15, 0.7, 0.15] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
        />
      )}
      {/* lock glyph + label at the rail head */}
      <g transform={`translate(${AXIS_X + 6}, ${y - 16})`}>
        <rect x={0} y={5} width={9} height={7} rx={1.4} stroke={c} strokeWidth={1.2} fill={COLORS.base} />
        <path d="M2 5V3.6a2.5 2.5 0 0 1 5 0V5" stroke={c} strokeWidth={1.2} fill="none" />
      </g>
      <text
        x={AXIS_X + 20}
        y={y - 6}
        fontSize={10.5}
        className="metric"
        fill={c}
        fontWeight={700}
        style={{ letterSpacing: "0.08em" }}
      >
        MANDATE CAP · {fmtK(value)}
      </text>
    </g>
  );
}

/** A single offer/counter node — a labeled price chip dropping into place. */
function OfferNode({
  x,
  y,
  round,
  price,
  color,
  side,
  emphasize,
}: {
  x: number;
  y: number;
  round: number;
  price: number;
  color: string;
  side: "left" | "right";
  emphasize: boolean;
}) {
  const labelDx = side === "left" ? -12 : 12;
  const anchor = side === "left" ? "end" : "start";
  return (
    <motion.g
      initial={{ opacity: 0, y: side === "left" ? 14 : -14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      {emphasize && (
        <motion.circle
          cx={x}
          cy={y}
          r={5}
          fill="none"
          stroke={color}
          strokeWidth={1.2}
          animate={{ r: [5, 13], opacity: [0.6, 0] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeOut" }}
        />
      )}
      <circle
        cx={x}
        cy={y}
        r={emphasize ? 4.5 : 3.5}
        fill={COLORS.base}
        stroke={color}
        strokeWidth={1.6}
      />
      <circle cx={x} cy={y} r={1.6} fill={color} />
      {/* round badge */}
      <text
        x={x + labelDx}
        y={y - 5}
        fontSize={8.5}
        textAnchor={anchor}
        className="metric"
        fill={COLORS.inkGhost}
        style={{ letterSpacing: "0.06em" }}
      >
        R{round}
      </text>
      {/* price */}
      <text
        x={x + labelDx}
        y={y + 5}
        fontSize={11}
        textAnchor={anchor}
        className="metric"
        fill={color}
        fontWeight={emphasize ? 700 : 500}
      >
        {fmtK(price)}
      </text>
    </motion.g>
  );
}

/** Green converged seal — the deal point, under the cap. */
function DealSeal({
  x,
  y,
  price,
  savings,
}: {
  x: number;
  y: number;
  price: number;
  savings: number;
}) {
  return (
    <motion.g
      initial={{ opacity: 0, scale: 0.6 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      <circle cx={x} cy={y} r={34} fill="url(#neg-deal)" />
      <motion.circle
        cx={x}
        cy={y}
        r={13}
        fill="none"
        stroke={COLORS.ok}
        strokeWidth={1.3}
        animate={{ r: [13, 26], opacity: [0.55, 0] }}
        transition={{ duration: 2.2, repeat: Infinity, ease: "easeOut" }}
      />
      <circle cx={x} cy={y} r={13} fill={COLORS.base} stroke={COLORS.ok} strokeWidth={1.8} />
      <path
        d={`M ${x - 5} ${y + 0.5} l 3.4 3.4 l 6 -7`}
        fill="none"
        stroke={COLORS.ok}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <text
        x={x}
        y={y + 32}
        fontSize={13}
        textAnchor="middle"
        className="metric"
        fill={COLORS.ok}
        fontWeight={700}
      >
        {fmtK(price)} · −{savings.toFixed(1)}%
      </text>
      <text
        x={x}
        y={y + 47}
        fontSize={9.5}
        textAnchor="middle"
        className="metric"
        fill={COLORS.inkFaint}
        style={{ letterSpacing: "0.12em" }}
      >
        DEAL CLOSED
      </text>
    </motion.g>
  );
}

/** The walk-away — the cap holds, the agent steps back. The safety wow. */
function WalkAway({ capY }: { capY: number }) {
  return (
    <motion.g
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* a firm rose seal centered on the cap rail */}
      <motion.g
        initial={{ x: 0 }}
        animate={{ x: [0, -10, -6, -10] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
      >
        <circle cx={CENTER_X} cy={capY} r={15} fill={COLORS.base} stroke={COLORS.danger} strokeWidth={1.8} />
        {/* a "no-cross" bar */}
        <path
          d={`M ${CENTER_X - 6} ${capY - 6} L ${CENTER_X + 6} ${capY + 6}`}
          stroke={COLORS.danger}
          strokeWidth={2.2}
          strokeLinecap="round"
        />
        <circle cx={CENTER_X} cy={capY} r={15} fill="none" stroke={COLORS.danger} strokeWidth={1.8} />
      </motion.g>
      <text
        x={CENTER_X}
        y={capY + 34}
        fontSize={13}
        textAnchor="middle"
        className="metric"
        fill={COLORS.danger}
        fontWeight={700}
        style={{ letterSpacing: "0.04em" }}
      >
        WALKED AWAY
      </text>
      <text
        x={CENTER_X}
        y={capY + 50}
        fontSize={9.5}
        textAnchor="middle"
        className="metric"
        fill={COLORS.inkFaint}
        style={{ letterSpacing: "0.1em" }}
      >
        CAP HELD · NO BREACH
      </text>
    </motion.g>
  );
}

/** A few round axis ticks across the visible price range. */
function buildTicks(lo: number, hi: number): number[] {
  const range = hi - lo;
  // pick a "nice" step that yields ~5 ticks
  const raw = range / 5;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  const niceStep =
    (norm >= 5 ? 5 : norm >= 2 ? 2 : 1) * mag;
  const start = Math.ceil(lo / niceStep) * niceStep;
  const out: number[] = [];
  for (let p = start; p <= hi + 0.5; p += niceStep) out.push(Math.round(p));
  return out;
}
