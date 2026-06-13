"use client";

import { useState } from "react";

import { fetchTransparency, type Transparency } from "@/lib/api";
import { usePoll } from "@/lib/usePoll";

/**
 * The footer's EU AI Act Article 50 transparency line.
 *
 * Fetches GET /transparency once the control plane is up and renders a single
 * quiet disclosure ("⬡ AI system · EU AI Act Art. 50 — …"). Hovering or focusing
 * expands the full notice (regulation, data basis, human oversight). When the
 * endpoint is offline it falls back to static, on-brand disclosure text so the
 * footer is always compliant and never crashes.
 */

const FALLBACK: Transparency = {
  ai_system: true,
  notice:
    "Autonomous agents, audited, human-gated. You are interacting with an AI system.",
  regulation: "EU AI Act, Article 50 — transparency obligations",
  data: "Synthetic research data only — no real supplier or buyer records.",
  human_oversight:
    "Every consequential action is mandate-capped and routed through a human approval gate.",
};

export function GovernanceNotice() {
  const { data, offline, loaded } = usePoll<Transparency>(
    fetchTransparency,
    60_000,
  );
  const [open, setOpen] = useState(false);

  // Use live data when present; otherwise the static fallback keeps the line
  // meaningful while the control plane is unreachable.
  const t = !offline && data ? data : FALLBACK;
  const live = loaded && !offline && Boolean(data);

  return (
    <div
      className="relative"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        className="focus-ring group inline-flex items-center gap-1.5 rounded-sm font-mono text-[10px] tracking-wider text-ink-ghost transition-colors hover:text-ink-faint"
        title="EU AI Act Article 50 — AI transparency disclosure"
      >
        <span
          aria-hidden
          className="text-[11px] leading-none"
          style={{ color: "var(--autonomy)" }}
        >
          ⬡
        </span>
        <span>
          AI system · EU AI Act Art. 50 — autonomous agents, audited, human-gated
        </span>
        {live ? (
          <span
            aria-hidden
            className="h-1 w-1 rounded-full"
            style={{ background: "var(--ok)" }}
            title="transparency disclosure served live"
          />
        ) : null}
      </button>

      {open ? (
        <div
          role="note"
          className="panel-2 absolute bottom-full right-0 z-30 mb-2 w-[min(22rem,80vw)] rounded-md border border-line p-3 text-left shadow-xl"
        >
          <p className="text-[11px] leading-relaxed text-ink-muted">
            {t.notice}
          </p>
          <dl className="mt-2.5 space-y-1.5 border-t border-line/70 pt-2.5">
            <Row term="regulation" value={t.regulation} />
            <Row term="data" value={t.data} />
            <Row term="oversight" value={t.human_oversight} />
          </dl>
          {!live ? (
            <p className="mt-2.5 font-mono text-[9px] tracking-wider text-ink-ghost">
              static disclosure — control plane offline
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function Row({ term, value }: { term: string; value: string }) {
  return (
    <div className="grid grid-cols-[5.5rem_minmax(0,1fr)] gap-2">
      <dt className="label-cap pt-px">{term}</dt>
      <dd className="text-[10px] leading-relaxed text-ink-faint">{value}</dd>
    </div>
  );
}
