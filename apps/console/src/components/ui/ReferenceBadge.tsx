import { COLORS, withAlpha } from "@/lib/theme";
import { LiveDot } from "./LiveDot";

/**
 * ReferenceBadge — a small data-honesty chip. Every instrument labels where its
 * numbers come from so nobody mistakes a fallback or a model for live truth:
 *   • live      — green pulsing dot, the control plane is answering
 *   • reference — violet, "reference data, control plane offline" (graceful fallback)
 *   • modeled   — amber, "modeled cost · no API spend" (real rates × real tokens)
 */

export type ReferenceMode = "live" | "reference" | "modeled";

interface ReferenceBadgeProps {
  mode: ReferenceMode;
  /** Override the default label for this mode. */
  label?: string;
  className?: string;
}

const COPY: Record<ReferenceMode, { label: string; color: string; title: string }> = {
  live: {
    label: "live",
    color: COLORS.ok,
    title: "Live data — the control plane is answering.",
  },
  reference: {
    label: "reference data · control plane offline",
    color: COLORS.autonomy,
    title:
      "The control plane is unreachable; showing the built-in reference fleet so the screen stays meaningful.",
  },
  modeled: {
    label: "modeled cost · no API spend",
    color: COLORS.warn,
    title:
      "Cost is modeled from real per-model rates × real token counts. No live API spend occurred.",
  },
};

export function ReferenceBadge({ mode, label, className = "" }: ReferenceBadgeProps) {
  const { label: defaultLabel, color, title } = COPY[mode];
  const text = label ?? defaultLabel;

  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-1 font-mono text-[10px] leading-none tracking-wide ${className}`}
      style={{
        color,
        borderColor: withAlpha(color, 0.4),
        background: withAlpha(color, 0.1),
      }}
    >
      {mode === "live" ? (
        <LiveDot live size={7} />
      ) : (
        <span
          aria-hidden
          className="inline-block h-1.5 w-1.5 rounded-full"
          style={{ background: color }}
        />
      )}
      {text}
    </span>
  );
}
