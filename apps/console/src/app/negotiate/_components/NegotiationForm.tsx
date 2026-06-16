"use client";

import { Panel, Spinner } from "@/components/ui";
import { COLORS, withAlpha } from "@/lib/theme";
import {
  PRICE_MAX,
  PRICE_MIN,
  SEED_SELLERS,
  fmtK,
  type SellerPersona,
} from "./demo";

interface NegotiationFormProps {
  /** Personas to choose from — the live `sellers` list once known, else the seeds. */
  sellers: SellerPersona[];
  sellerIdx: number;
  onSellerIdx: (i: number) => void;
  listPrice: number;
  onListPrice: (p: number) => void;
  /** True once we know (from the last result) that this price would breach the cap. */
  willWalk: boolean;
  onNegotiate: () => void;
  busy: boolean;
  /** True while a negotiation is on the table — exposes a "New" reset. */
  hasRun: boolean;
  onReset: () => void;
}

const STEP = 2_500;

export function NegotiationForm({
  sellers,
  sellerIdx,
  onSellerIdx,
  listPrice,
  onListPrice,
  willWalk,
  onNegotiate,
  busy,
  hasRun,
  onReset,
}: NegotiationFormProps) {
  const list = sellers.length ? sellers : SEED_SELLERS;
  const sliderPct = ((listPrice - PRICE_MIN) / (PRICE_MAX - PRICE_MIN)) * 100;
  const fill = willWalk ? COLORS.danger : COLORS.accent;

  return (
    <Panel
      accent="COCKPIT"
      title="the table"
      action={
        <span
          className="metric text-[10px] tracking-wide"
          style={{ color: willWalk ? COLORS.danger : COLORS.inkFaint }}
        >
          {willWalk ? "▲ would breach mandate" : "within mandate"}
        </span>
      }
    >
      <div className="space-y-5">
        {/* seller persona picker */}
        <div>
          <span className="label-cap mb-2 block">opponent</span>
          <div className="space-y-2">
            {list.map((s, i) => {
              const active = i === sellerIdx;
              return (
                <button
                  key={s.skill_id ?? i}
                  type="button"
                  onClick={() => onSellerIdx(i)}
                  disabled={busy}
                  aria-pressed={active}
                  className="focus-ring group block w-full rounded-md border px-3 py-2.5 text-left transition-all disabled:opacity-50"
                  style={{
                    borderColor: active
                      ? withAlpha(COLORS.accent, 0.5)
                      : "var(--line)",
                    background: active
                      ? withAlpha(COLORS.accent, 0.08)
                      : "var(--base-2)",
                  }}
                >
                  <div className="flex items-center gap-2">
                    <SellerGlyph active={active} index={i} />
                    <span
                      className="text-sm font-semibold"
                      style={{ color: active ? COLORS.accent : COLORS.ink }}
                    >
                      {s.name}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] leading-relaxed text-ink-faint">
                    {s.blurb ??
                      "A seller persona routed through the negotiator skill."}
                  </p>
                </button>
              );
            })}
          </div>
        </div>

        {/* list price */}
        <div>
          <div className="mb-1.5 flex items-baseline justify-between">
            <span className="label-cap">list price</span>
            <span
              className="metric text-sm font-semibold"
              style={{ color: fill }}
            >
              {fmtK(listPrice)}
            </span>
          </div>
          <input
            type="range"
            min={PRICE_MIN}
            max={PRICE_MAX}
            step={STEP}
            value={listPrice}
            onChange={(e) => onListPrice(Number(e.target.value))}
            disabled={busy}
            aria-label="list price"
            className="steel-range w-full"
            style={
              {
                "--pct": `${sliderPct}%`,
                "--fill": fill,
              } as React.CSSProperties
            }
          />
          <div className="mt-1 flex justify-between">
            <span className="text-[10px] text-ink-ghost">{fmtK(PRICE_MIN)}</span>
            <span className="text-[10px] text-ink-ghost">{fmtK(PRICE_MAX)}</span>
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-ink-faint">
            The negotiator holds a hard{" "}
            <span style={{ color: COLORS.danger }}>mandate cap</span>. Push the
            price high enough and the only attainable deals sit above the cap —
            watch it refuse to cross the line.
          </p>
        </div>

        {/* engage */}
        <div className="flex items-center gap-2 pt-0.5">
          <button
            type="button"
            onClick={onNegotiate}
            disabled={busy}
            className="focus-ring group relative inline-flex flex-1 items-center justify-center gap-2 overflow-hidden rounded-md px-4 py-2.5 text-sm font-semibold transition-all disabled:opacity-60"
            style={{
              background: busy
                ? withAlpha(COLORS.accent, 0.15)
                : `linear-gradient(180deg, ${withAlpha(COLORS.accent, 0.95)}, ${COLORS.accentDim})`,
              color: busy ? COLORS.accent : COLORS.accentInk,
              boxShadow: busy ? "none" : `0 0 22px -6px ${COLORS.accent}`,
            }}
          >
            {busy ? (
              <Spinner size={15} label="at the table…" />
            ) : (
              <>
                <GavelGlyph />
                {hasRun ? "Re-open negotiation" : "Open negotiation"}
              </>
            )}
          </button>
          {hasRun && (
            <button
              type="button"
              onClick={onReset}
              disabled={busy}
              className="focus-ring rounded-md border border-line px-3 py-2.5 text-sm text-ink-muted transition-colors hover:border-line-strong hover:text-ink disabled:opacity-40"
            >
              New
            </button>
          )}
        </div>
      </div>

      <RangeStyles />
    </Panel>
  );
}

function SellerGlyph({ active, index }: { active: boolean; index: number }) {
  const c = active ? COLORS.accent : COLORS.inkFaint;
  // Three distinct silhouettes for the three archetypes.
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
      {index === 0 ? (
        // Stonewaller — a wall.
        <>
          <rect x="2.5" y="3" width="11" height="10" rx="1" stroke={c} strokeWidth="1.3" />
          <path d="M2.5 6.5h11M2.5 9.5h11M6 3v3.5M10 6.5V10M6 9.5V13" stroke={c} strokeWidth="1" />
        </>
      ) : index === 1 ? (
        // Margin Hawk — a sharp chevron / beak.
        <>
          <path d="M2.5 11 8 3l5.5 8" stroke={c} strokeWidth="1.4" strokeLinejoin="round" />
          <path d="M5.5 9 8 6l2.5 3" stroke={c} strokeWidth="1.2" strokeLinejoin="round" />
        </>
      ) : (
        // Volume Hunter — stacked layers.
        <>
          <path d="M8 2.5 14 5.5 8 8.5 2 5.5 8 2.5Z" stroke={c} strokeWidth="1.3" strokeLinejoin="round" />
          <path d="M2.5 8.5 8 11.2l5.5-2.7M2.5 11 8 13.7 13.5 11" stroke={c} strokeWidth="1.1" strokeLinejoin="round" />
        </>
      )}
    </svg>
  );
}

function GavelGlyph() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M3 13h6M9.5 2.5l4 4M11.5 4.5 6 10M5 5.5 8.5 9"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Scoped styling for the native range input (cockpit accent track + thumb). */
function RangeStyles() {
  return (
    <style>{`
      .steel-range {
        -webkit-appearance: none;
        appearance: none;
        height: 4px;
        border-radius: 999px;
        background: linear-gradient(
          to right,
          var(--fill) 0%,
          var(--fill) var(--pct),
          var(--line-strong) var(--pct),
          var(--line-strong) 100%
        );
        outline: none;
        cursor: pointer;
      }
      .steel-range:disabled { opacity: 0.5; cursor: not-allowed; }
      .steel-range::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: 15px;
        height: 15px;
        border-radius: 999px;
        background: var(--base);
        border: 2px solid var(--fill);
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--fill) 22%, transparent),
          0 0 10px -2px var(--fill);
        transition: transform 0.12s ease;
      }
      .steel-range::-webkit-slider-thumb:hover { transform: scale(1.12); }
      .steel-range::-moz-range-thumb {
        width: 15px;
        height: 15px;
        border-radius: 999px;
        background: var(--base);
        border: 2px solid var(--fill);
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--fill) 22%, transparent);
      }
    `}</style>
  );
}
