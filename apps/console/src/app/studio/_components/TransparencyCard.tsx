"use client";

import { Panel } from "@/components/ui";
import { fetchTransparency, type Transparency } from "@/lib/api";
import { COLORS, withAlpha } from "@/lib/theme";
import { usePoll } from "@/lib/usePoll";

const POLL_MS = 60_000;

/** Static on-brand disclosure shown when GET /transparency is unreachable. */
const REFERENCE_TRANSPARENCY: Transparency = {
  ai_system: true,
  notice:
    "You are interacting with an AI system. JAI agents draft, analyze, and act on procurement tasks; their actions are logged and bounded by policy.",
  regulation: "EU AI Act, Article 50 — transparency obligations",
  data:
    "Operates over your tenant's procurement records — suppliers, contracts, spend, and sourcing events — never shared across tenants.",
  human_oversight:
    "Every consequential action is gated, mandated, and reversible; a human approves spend above mandate, and the full trail is tamper-evident.",
};

/** One labeled facet of the disclosure. */
const FACETS: {
  key: keyof Pick<Transparency, "regulation" | "data" | "human_oversight">;
  label: string;
  glyph: string;
}[] = [
  { key: "regulation", label: "regulation", glyph: "§" },
  { key: "human_oversight", label: "human oversight", glyph: "◉" },
  { key: "data", label: "data scope", glyph: "▤" },
];

/**
 * SECTION 3 — "Transparency" (EU AI Act Art. 50).
 *
 * The compliance posture made visible: the headline AI-system notice, then the
 * regulation it answers to, the human-oversight guarantee, and the data scope —
 * a calm governance card, the quiet counterpart to the live instruments.
 */
export function TransparencyCard() {
  const { data, offline } = usePoll<Transparency>(fetchTransparency, POLL_MS);
  const t = data ?? REFERENCE_TRANSPARENCY;
  const live = Boolean(data) && !offline;

  return (
    <Panel
      accent="SAFETY"
      title="transparency"
      action={
        <span className="inline-flex items-center gap-1.5">
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{
              background: live ? COLORS.ok : COLORS.inkFaint,
              boxShadow: live ? `0 0 6px -1px ${COLORS.ok}` : "none",
            }}
          />
          <span
            className="metric text-[10px] tracking-wide"
            style={{ color: live ? COLORS.ok : COLORS.inkFaint }}
          >
            {live ? "live disclosure" : "static notice"}
          </span>
        </span>
      }
    >
      {/* headline notice */}
      <div
        className="rounded-md border p-4"
        style={{
          borderColor: withAlpha(COLORS.danger, 0.28),
          background: withAlpha(COLORS.danger, 0.05),
        }}
      >
        <div className="flex items-start gap-3">
          <span
            aria-hidden
            className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-[13px]"
            style={{
              color: COLORS.danger,
              background: withAlpha(COLORS.danger, 0.12),
              border: `1px solid ${withAlpha(COLORS.danger, 0.3)}`,
            }}
          >
            ⬡
          </span>
          <div>
            <div className="label-cap" style={{ color: COLORS.danger }}>
              {t.ai_system ? "AI system · disclosed" : "not an AI system"}
            </div>
            <p className="mt-1 text-sm leading-relaxed text-ink">{t.notice}</p>
          </div>
        </div>
      </div>

      {/* facets */}
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        {FACETS.map((f) => (
          <div
            key={f.key}
            className="rounded-md border border-line bg-base-2/50 p-3"
          >
            <div className="flex items-center gap-1.5">
              <span
                aria-hidden
                className="text-[12px]"
                style={{ color: COLORS.danger }}
              >
                {f.glyph}
              </span>
              <span className="label-cap">{f.label}</span>
            </div>
            <p className="mt-1.5 text-[12px] leading-relaxed text-ink-muted">
              {t[f.key]}
            </p>
          </div>
        ))}
      </div>

      <p className="mt-3 text-[11px] leading-relaxed text-ink-faint">
        This disclosure is served from the platform itself — the same notice the
        console footer surfaces on every screen. Compliance is a property of the
        system, not a page.
      </p>
    </Panel>
  );
}
