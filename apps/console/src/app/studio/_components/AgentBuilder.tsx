"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";

import { Panel, Pill, Spinner } from "@/components/ui";
import { postManifestValidate, type ManifestCheck } from "@/lib/api";
import {
  AUTONOMY_COLORS,
  AUTONOMY_LABELS,
  COLORS,
  withAlpha,
} from "@/lib/theme";
import {
  DEFAULT_DRAFT,
  draftToYaml,
  localValidate,
  MODEL_GROUPS,
  MODEL_HINTS,
  PIPELINE_HINTS,
  PIPELINES,
  type AgentDraft,
  type ModelGroup,
  type Pipeline,
} from "./manifest";
import { YamlPreview } from "./YamlPreview";

const VALIDATE_DEBOUNCE_MS = 450;

/** The latest validation outcome, tagged with the YAML it judged. */
interface CheckResult {
  check: ManifestCheck;
  offline: boolean;
  /** The exact YAML this result validated — drives the "checking" state. */
  forYaml: string;
}

/**
 * SECTION 1 — "Build an agent".
 *
 * A form whose every keystroke re-derives a real, schema-valid jai/v1
 * AgentManifest in the live preview pane, debounce-validated against
 * POST /manifest/validate. The point: the studio is a design-time author for
 * the SAME manifest the platform compiles — not a toy no-code runtime.
 */
export function AgentBuilder() {
  const [draft, setDraft] = useState<AgentDraft>(DEFAULT_DRAFT);
  const [result, setResult] = useState<CheckResult | null>(null);
  const [copied, setCopied] = useState(false);

  const yaml = useMemo(() => draftToYaml(draft), [draft]);

  // We're validating whenever the latest result doesn't yet match the YAML on
  // screen. Deriving this at render-time (rather than a synchronous setState in
  // the effect) keeps the effect's only state writes inside the async callback.
  const checking = result === null || result.forYaml !== yaml;

  // Debounced validation. Validate the YAML we actually show; fall back to a
  // local check (mirrors the server's shape) when the endpoint is offline.
  const seq = useRef(0);
  useEffect(() => {
    const mine = ++seq.current;
    const t = setTimeout(async () => {
      try {
        const check = await postManifestValidate(yaml);
        if (seq.current === mine) {
          setResult({ check, offline: false, forYaml: yaml });
        }
      } catch {
        if (seq.current === mine) {
          setResult({ check: localValidate(draft), offline: true, forYaml: yaml });
        }
      }
    }, VALIDATE_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [yaml, draft]);

  function set<K extends keyof AgentDraft>(key: K, value: AgentDraft[K]) {
    setDraft((d) => ({ ...d, [key]: value }));
  }

  async function copyYaml() {
    try {
      await navigator.clipboard.writeText(yaml);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard blocked — no-op, button just doesn't confirm */
    }
  }

  const inputCls =
    "w-full rounded-md border border-line bg-base-2 px-3 py-2 text-sm text-ink outline-none transition-colors focus-ring placeholder:text-ink-ghost focus:border-line-strong";
  const labelCls = "label-cap mb-1.5 block";

  return (
    <Panel
      accent="NETWORK"
      title="build an agent"
      action={<ValidityBadge checking={checking} result={result} />}
    >
      <p className="mb-4 max-w-2xl text-[12px] leading-relaxed text-ink-faint">
        The studio is design-time, not a no-code runtime. Every field below
        composes a real{" "}
        <span className="metric text-ink-muted">jai/v1</span> AgentManifest —
        the exact schema jai-engine compiles into a runnable agent.
      </p>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:items-start">
        {/* ---- the form ---- */}
        <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
          <div>
            <label className={labelCls} htmlFor="a-name">
              name
            </label>
            <input
              id="a-name"
              value={draft.name}
              onChange={(e) => set("name", e.target.value)}
              placeholder="agent-contract-analyst"
              className={`${inputCls} metric`}
            />
          </div>

          <div>
            <label className={labelCls} htmlFor="a-desc">
              description
            </label>
            <textarea
              id="a-desc"
              value={draft.description}
              onChange={(e) => set("description", e.target.value)}
              placeholder="What does this agent do, in one line?"
              rows={2}
              className={`${inputCls} resize-none leading-relaxed`}
            />
          </div>

          {/* autonomy — segmented control on the violet ramp */}
          <div>
            <div className="mb-1.5 flex items-baseline justify-between">
              <span className="label-cap">autonomy level</span>
              <span
                className="metric text-[11px]"
                style={{ color: AUTONOMY_COLORS[draft.autonomyLevel] }}
              >
                L{draft.autonomyLevel} · {AUTONOMY_LABELS[draft.autonomyLevel]}
              </span>
            </div>
            <AutonomySegments
              value={draft.autonomyLevel}
              onChange={(n) => set("autonomyLevel", n)}
            />
            <p className="mt-1.5 text-[11px] leading-relaxed text-ink-faint">
              An agent ships at the level its scorecards prove — see the maturity
              ladder below. The studio sets a starting level; promotion is earned.
            </p>
          </div>

          {/* pipeline + model group */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelCls} htmlFor="a-pipe">
                pipeline
              </label>
              <SelectField
                id="a-pipe"
                value={draft.pipeline}
                onChange={(v) => set("pipeline", v as Pipeline)}
                options={PIPELINES}
              />
              <p className="mt-1.5 text-[11px] leading-relaxed text-ink-faint">
                {PIPELINE_HINTS[draft.pipeline]}
              </p>
            </div>
            <div>
              <label className={labelCls} htmlFor="a-model">
                model group
              </label>
              <SelectField
                id="a-model"
                value={draft.modelGroup}
                onChange={(v) => set("modelGroup", v as ModelGroup)}
                options={MODEL_GROUPS}
              />
              <p className="mt-1.5 text-[11px] leading-relaxed text-ink-faint">
                {MODEL_HINTS[draft.modelGroup]}
              </p>
            </div>
          </div>

          {/* skills */}
          <div>
            <label className={labelCls} htmlFor="a-skills">
              skills{" "}
              <span className="text-ink-ghost">· comma-separated</span>
            </label>
            <input
              id="a-skills"
              value={draft.skills}
              onChange={(e) => set("skills", e.target.value)}
              placeholder="supplier.lookup, supplier.risk, qa.cited"
              className={`${inputCls} metric`}
            />
          </div>

          {/* optional mandate */}
          <div>
            <label className={labelCls} htmlFor="a-mandate">
              spend mandate{" "}
              <span className="text-ink-ghost">· optional, usd</span>
            </label>
            <div className="relative">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-ink-faint">
                $
              </span>
              <input
                id="a-mandate"
                value={draft.maxSpendUsd}
                onChange={(e) =>
                  set("maxSpendUsd", e.target.value.replace(/[^0-9.]/g, ""))
                }
                inputMode="decimal"
                placeholder="none"
                className={`${inputCls} metric pl-7`}
              />
            </div>
            <p className="mt-1.5 text-[11px] leading-relaxed text-ink-faint">
              A hard ceiling the governor enforces below the model — the
              negotiator pattern of bounded delegation.
            </p>
          </div>
        </form>

        {/* ---- live YAML preview ---- */}
        <div className="lg:sticky lg:top-6">
          <div className="mb-1.5 flex items-center justify-between">
            <span className="label-cap">manifest · live</span>
            <CopyButton copied={copied} onCopy={copyYaml} />
          </div>
          <YamlPreview yaml={yaml} />
          <ValidityNote checking={checking} result={result} />
        </div>
      </div>
    </Panel>
  );
}

/* ------------------------------------------------------------------ pieces --- */

function AutonomySegments({
  value,
  onChange,
}: {
  value: number;
  onChange: (n: number) => void;
}) {
  return (
    <div className="grid grid-cols-5 gap-1.5">
      {[1, 2, 3, 4, 5].map((lvl) => {
        const on = lvl <= value;
        const isCurrent = lvl === value;
        const color = AUTONOMY_COLORS[value];
        return (
          <button
            key={lvl}
            type="button"
            onClick={() => onChange(lvl)}
            aria-pressed={isCurrent}
            className="focus-ring group flex flex-col items-center gap-1 rounded-md border px-1 py-1.5 transition-all"
            style={{
              borderColor: on
                ? withAlpha(color, isCurrent ? 0.7 : 0.4)
                : COLORS.line,
              background: on
                ? withAlpha(color, isCurrent ? 0.18 : 0.08)
                : "transparent",
              boxShadow: isCurrent ? `0 0 14px -6px ${color}` : "none",
            }}
          >
            <span
              className="metric text-[11px] font-semibold"
              style={{ color: on ? AUTONOMY_COLORS[lvl] : COLORS.inkFaint }}
            >
              L{lvl}
            </span>
            <span
              className="text-[9px] leading-tight"
              style={{ color: on ? COLORS.inkMuted : COLORS.inkGhost }}
            >
              {AUTONOMY_LABELS[lvl]}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function SelectField({
  id,
  value,
  onChange,
  options,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  options: readonly string[];
}) {
  return (
    <div className="relative">
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="metric w-full appearance-none rounded-md border border-line bg-base-2 px-3 py-2 pr-8 text-sm text-ink outline-none transition-colors focus-ring focus:border-line-strong"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
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
    </div>
  );
}

function ValidityBadge({
  checking,
  result,
}: {
  checking: boolean;
  result: CheckResult | null;
}) {
  if (checking) {
    return <Spinner size={13} label="validating…" />;
  }
  if (result) {
    return result.check.valid ? (
      <Pill tone="ok">valid ✓</Pill>
    ) : (
      <Pill tone="danger">invalid</Pill>
    );
  }
  return null;
}

function ValidityNote({
  checking,
  result,
}: {
  checking: boolean;
  result: CheckResult | null;
}) {
  if (checking || !result) return null;
  const { check, offline } = result;
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={check.valid ? "ok" : "err"}
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="mt-2"
      >
        {check.valid ? (
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-ink-faint">
            <span style={{ color: COLORS.ok }}>
              schema-valid manifest — would compile.
            </span>
            {check.name && (
              <span className="metric text-ink-muted">{check.name}</span>
            )}
            {offline && (
              <span
                className="metric"
                style={{ color: COLORS.autonomy }}
                title="POST /manifest/validate unreachable — validated locally against the same schema."
              >
                · checked offline
              </span>
            )}
          </div>
        ) : (
          <p
            className="text-[11px] leading-relaxed"
            style={{ color: COLORS.danger }}
          >
            {check.error ?? "manifest is not valid yet."}
          </p>
        )}
      </motion.div>
    </AnimatePresence>
  );
}

function CopyButton({
  copied,
  onCopy,
}: {
  copied: boolean;
  onCopy: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onCopy}
      className="focus-ring inline-flex items-center gap-1.5 rounded-md border border-line px-2 py-1 text-[11px] text-ink-muted transition-colors hover:border-line-strong hover:text-ink"
    >
      {copied ? (
        <>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
            <path
              d="M2.5 6.5 5 9l4.5-5.5"
              stroke={COLORS.ok}
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span style={{ color: COLORS.ok }}>copied</span>
        </>
      ) : (
        <>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
            <rect
              x="3.5"
              y="3.5"
              width="6"
              height="6"
              rx="1.2"
              stroke="currentColor"
              strokeWidth="1.2"
            />
            <path
              d="M2 8V2.5A.5.5 0 0 1 2.5 2H8"
              stroke="currentColor"
              strokeWidth="1.2"
              strokeLinecap="round"
            />
          </svg>
          copy YAML
        </>
      )}
    </button>
  );
}
