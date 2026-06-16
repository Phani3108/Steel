/**
 * STEEL cockpit design tokens for TypeScript / hand-rolled SVG.
 *
 * These are the SAME values defined as CSS variables in app/globals.css.
 * Markup should prefer the Tailwind utilities (`text-accent`, `bg-panel`, …);
 * this module exists for places that can't read CSS variables ergonomically —
 * principally SVG attributes (stroke/fill) in the bespoke data-viz primitives.
 *
 * Keep this file and globals.css :root in lockstep.
 */

/** The six car systems. The catalog/network/registry all key off these. */
export type System =
  | "POWERTRAIN"
  | "CHASSIS"
  | "DRIVETRAIN"
  | "SAFETY"
  | "NETWORK"
  | "COCKPIT";

export const SYSTEMS: readonly System[] = [
  "POWERTRAIN",
  "CHASSIS",
  "DRIVETRAIN",
  "SAFETY",
  "NETWORK",
  "COCKPIT",
] as const;

/** Agent / part lifecycle. */
export type Status = "active" | "paused" | "killed" | "planned";

/** Outcome of an audit event (mirrors the API contract). */
export type Outcome =
  | "ok"
  | "denied"
  | "error"
  | "escalated"
  | "pending_approval";

/** Semantic colors — surfaces, ink, and signal hues. */
export const COLORS = {
  base: "#0a0b0d",
  base2: "#0c0e11",
  panel: "#111418",
  panel2: "#161a20",
  line: "#20262e",
  lineStrong: "#2c343e",

  ink: "#e7ecf2",
  inkMuted: "#9aa6b4",
  inkFaint: "#5c6675",
  inkGhost: "#3a424d",

  accent: "#22d3ee",
  accentDim: "#0e7490",
  accentInk: "#062a30",
  ok: "#34d399",
  warn: "#f59e0b",
  danger: "#fb7185",
  autonomy: "#a78bfa",
  info: "#38bdf8",
} as const;

/** One signature hue per car system. */
export const SYSTEM_HUES: Record<System, string> = {
  POWERTRAIN: "#f59e0b", // amber — intelligence supply
  CHASSIS: "#38bdf8", // sky — knowledge
  DRIVETRAIN: "#34d399", // emerald — domain capability
  SAFETY: "#fb7185", // rose — trust
  NETWORK: "#a78bfa", // violet — the fleet
  COCKPIT: "#22d3ee", // aqua — human interface
};

/** Short human label + tagline per system (used in catalog/network legends). */
export const SYSTEM_META: Record<System, { tagline: string }> = {
  POWERTRAIN: { tagline: "intelligence supply" },
  CHASSIS: { tagline: "knowledge" },
  DRIVETRAIN: { tagline: "domain capability" },
  SAFETY: { tagline: "trust" },
  NETWORK: { tagline: "the fleet" },
  COCKPIT: { tagline: "human interface" },
};

/** Status → color. Used by Pill, SystemBadge, registry cards. */
export const STATUS_COLORS: Record<Status, string> = {
  active: COLORS.ok,
  paused: COLORS.warn,
  killed: COLORS.danger,
  planned: COLORS.inkFaint,
};

/** Audit outcome → color. */
export const OUTCOME_COLORS: Record<Outcome, string> = {
  ok: COLORS.ok,
  denied: COLORS.danger,
  error: COLORS.danger,
  escalated: COLORS.warn,
  pending_approval: COLORS.info,
};

/** Autonomy level (1..5) → violet ramp. Index 0 is unused (levels start at 1). */
export const AUTONOMY_COLORS: readonly string[] = [
  "#2c343e", // 0 — unused / rail
  "#4c3f8a", // L1 advise
  "#6d57b8", // L2 draft
  "#8b6fe0", // L3 act-with-approval
  "#a78bfa", // L4 act-and-notify
  "#c4b5fd", // L5 autonomous
];

export const AUTONOMY_LABELS: Record<number, string> = {
  1: "advise",
  2: "draft",
  3: "act · approval",
  4: "act · notify",
  5: "autonomous",
};

// ---------------------------------------------------------------- helpers ----

/** Color for a system, with a safe fallback. */
export function systemHue(system: string | null | undefined): string {
  if (system && system in SYSTEM_HUES) {
    return SYSTEM_HUES[system as System];
  }
  return COLORS.inkFaint;
}

/** Color for a status, with a safe fallback. */
export function statusColor(status: string | null | undefined): string {
  if (status && status in STATUS_COLORS) {
    return STATUS_COLORS[status as Status];
  }
  return COLORS.inkFaint;
}

/** Color for an audit outcome, with a safe fallback. */
export function outcomeColor(outcome: string | null | undefined): string {
  if (outcome && outcome in OUTCOME_COLORS) {
    return OUTCOME_COLORS[outcome as Outcome];
  }
  return COLORS.inkFaint;
}

/** Color for an autonomy level 1..5 (clamped). */
export function autonomyColor(level: number | null | undefined): string {
  const n = Math.max(1, Math.min(5, Math.round(level ?? 1)));
  return AUTONOMY_COLORS[n];
}

/** Convert a hex color + 0..1 alpha into an `rgba()` string (for SVG fills/glows). */
export function withAlpha(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const full =
    h.length === 3
      ? h
          .split("")
          .map((c) => c + c)
          .join("")
      : h;
  const r = parseInt(full.slice(0, 2), 16);
  const g = parseInt(full.slice(2, 4), 16);
  const b = parseInt(full.slice(4, 6), 16);
  const a = Math.max(0, Math.min(1, alpha));
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}
