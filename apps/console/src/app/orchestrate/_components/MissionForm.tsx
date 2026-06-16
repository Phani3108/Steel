"use client";

import { useEffect, useMemo, useState } from "react";

import { fetchMeta, type Meta } from "@/lib/api";
import { Panel, Spinner } from "@/components/ui";
import { COLORS, withAlpha } from "@/lib/theme";
import { CATEGORIES, type MissionIntake } from "./demo";

/** Default persona options if /meta is unreachable. */
const FALLBACK_ROLES = ["requester", "category_manager", "cpo"];
const FALLBACK_TENANTS = [
  { id: "TEN-0001", name: "Borealis North America" },
  { id: "TEN-0002", name: "Aurora EMEA" },
];

/** Snap points for the value slider (log-ish), in USD. */
const VALUE_STOPS = [
  10_000, 25_000, 50_000, 100_000, 175_000, 250_000, 400_000, 600_000, 850_000,
  1_200_000,
];

function fmtUsdShort(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(n % 1_000_000 ? 1 : 0)}M`;
  if (n >= 1_000) return `$${Math.round(n / 1_000)}k`;
  return `$${n}`;
}

interface MissionFormProps {
  onLaunch: (intake: MissionIntake) => void;
  busy: boolean;
  /** True while a mission is on the board — turns the button into "New mission". */
  hasMission: boolean;
  onReset: () => void;
}

export function MissionForm({
  onLaunch,
  busy,
  hasMission,
  onReset,
}: MissionFormProps) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [title, setTitle] = useState("Refresh fleet of 240 engineering laptops");
  const [category, setCategory] = useState<string>(CATEGORIES[0]);
  const [valueIdx, setValueIdx] = useState(5); // → $250k, trips the gate
  const [role, setRole] = useState("category_manager");
  const [tenant, setTenant] = useState(FALLBACK_TENANTS[0].id);

  useEffect(() => {
    fetchMeta()
      .then((m) => {
        setMeta(m);
        if (m.roles.length && !m.roles.includes(role)) setRole(m.roles[0]);
        if (m.tenants.length) setTenant(m.tenants[0].id);
      })
      .catch(() => {
        /* keep fallbacks */
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const roles = meta?.roles ?? FALLBACK_ROLES;
  const tenants = meta?.tenants ?? FALLBACK_TENANTS;
  const estValueUsd = VALUE_STOPS[valueIdx];

  const willGate = estValueUsd >= 250_000;
  const sliderPct = (valueIdx / (VALUE_STOPS.length - 1)) * 100;

  const tenantName = useMemo(
    () => tenants.find((t) => t.id === tenant)?.name ?? tenant,
    [tenants, tenant],
  );

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy || !title.trim()) return;
    onLaunch({
      title: title.trim(),
      category,
      estValueUsd,
      persona: { role, tenantId: tenant },
    });
  }

  const inputCls =
    "w-full rounded-md border border-line bg-base-2 px-3 py-2 text-sm text-ink outline-none transition-colors focus-ring placeholder:text-ink-ghost focus:border-line-strong";
  const labelCls = "label-cap mb-1.5 block";

  return (
    <Panel accent="COCKPIT" title="intake" action={<MandateHint willGate={willGate} />}>
      <form onSubmit={submit} className="space-y-4">
        {/* title */}
        <div>
          <label className={labelCls} htmlFor="m-title">
            mission
          </label>
          <input
            id="m-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="What do you need sourced?"
            className={inputCls}
            disabled={busy}
          />
        </div>

        {/* category + value */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className={labelCls} htmlFor="m-cat">
              category
            </label>
            <div className="relative">
              <select
                id="m-cat"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className={`${inputCls} appearance-none pr-8`}
                disabled={busy}
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              <Caret />
            </div>
          </div>

          <div>
            <div className="mb-1.5 flex items-baseline justify-between">
              <span className="label-cap">est. value</span>
              <span
                className="metric text-sm font-semibold"
                style={{ color: willGate ? COLORS.warn : COLORS.accent }}
              >
                {fmtUsdShort(estValueUsd)}
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={VALUE_STOPS.length - 1}
              step={1}
              value={valueIdx}
              onChange={(e) => setValueIdx(Number(e.target.value))}
              disabled={busy}
              aria-label="estimated value"
              className="steel-range w-full"
              style={
                {
                  "--pct": `${sliderPct}%`,
                  "--fill": willGate ? COLORS.warn : COLORS.accent,
                } as React.CSSProperties
              }
            />
            <div className="mt-1 flex justify-between">
              <span className="text-[10px] text-ink-ghost">$10k</span>
              <span className="text-[10px] text-ink-ghost">$1.2M</span>
            </div>
          </div>
        </div>

        {/* persona */}
        <div>
          <label className={labelCls}>persona</label>
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="relative">
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className={`${inputCls} appearance-none pr-8`}
                disabled={busy}
                aria-label="role"
              >
                {roles.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
              <Caret />
            </div>
            <div className="relative">
              <select
                value={tenant}
                onChange={(e) => setTenant(e.target.value)}
                className={`${inputCls} appearance-none pr-8`}
                disabled={busy}
                aria-label="tenant"
              >
                {tenants.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
              <Caret />
            </div>
          </div>
          <p className="mt-1.5 text-[11px] leading-relaxed text-ink-faint">
            Acting as{" "}
            <span className="text-ink-muted">{role}</span> in{" "}
            <span className="text-ink-muted">{tenantName}</span> — the governor
            enforces the mandate below the model.
          </p>
        </div>

        {/* launch */}
        <div className="flex items-center gap-2 pt-1">
          <button
            type="submit"
            disabled={busy || !title.trim()}
            className="focus-ring group relative inline-flex flex-1 items-center justify-center gap-2 overflow-hidden rounded-md px-4 py-2.5 text-sm font-semibold transition-all disabled:opacity-50"
            style={{
              background: busy
                ? withAlpha(COLORS.accent, 0.15)
                : `linear-gradient(180deg, ${withAlpha(COLORS.accent, 0.95)}, ${COLORS.accentDim})`,
              color: busy ? COLORS.accent : COLORS.accentInk,
              boxShadow: busy ? "none" : `0 0 22px -6px ${COLORS.accent}`,
            }}
          >
            {busy ? (
              <Spinner size={15} label="dispatching…" />
            ) : (
              <>
                <LaunchGlyph />
                Launch mission
              </>
            )}
          </button>
          {hasMission && (
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
      </form>

      <RangeStyles />
    </Panel>
  );
}

function MandateHint({ willGate }: { willGate: boolean }) {
  return (
    <span
      className="metric text-[10px] tracking-wide"
      style={{ color: willGate ? COLORS.warn : COLORS.inkFaint }}
    >
      {willGate ? "▲ exceeds $250k mandate" : "within mandate"}
    </span>
  );
}

function Caret() {
  return (
    <svg
      className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-faint"
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      aria-hidden
    >
      <path
        d="M3 4.5 6 7.5 9 4.5"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function LaunchGlyph() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
      <path
        d="M2 7h7M6 3.5 9.5 7 6 10.5M9.5 2.5v9"
        stroke="currentColor"
        strokeWidth="1.6"
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
