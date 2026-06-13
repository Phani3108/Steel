"use client";

import { useMemo, useState } from "react";

import { Pill } from "@/components/ui";
import { fmtTs, type AuditEvent, type Outcome } from "@/lib/api";
import { COLORS, OUTCOME_COLORS, outcomeColor, systemHue, withAlpha } from "@/lib/theme";

import { resolveAgent } from "./agents";

/**
 * RunTimeline — the run's audit trail as a vertical, hash-chained flight
 * recorder. Each event is a chain-link node connected to its predecessor; the
 * link colors green when prev_hash matches the prior event's hash, red on a
 * break — the tamper-evidence made legible. Mirrors the runs-index timeline
 * craft, scoped to the single-run view and tinted by each event's agent system.
 */

const OUTCOME_ORDER: Outcome[] = [
  "ok",
  "escalated",
  "pending_approval",
  "denied",
  "error",
];

/** A short, monospace fingerprint of a long hash (first 7 / last 4). */
function shortHash(h: string | null | undefined): string | null {
  if (!h) return null;
  const clean = h.replace(/^0x/, "");
  if (clean.length <= 14) return clean;
  return `${clean.slice(0, 7)}…${clean.slice(-4)}`;
}

/** Pull a few human-meaningful fields out of an event's detail blob for the row. */
function keyDetails(detail: AuditEvent["detail"]): [string, string][] {
  if (!detail || typeof detail !== "object") return [];
  const PREFERRED = [
    "title",
    "gate",
    "skill_id",
    "supplier_id",
    "est_value_usd",
    "total_usd",
    "best_bid",
    "savings_pct",
    "reason",
    "note",
  ];
  const out: [string, string][] = [];
  for (const k of PREFERRED) {
    const v = (detail as Record<string, unknown>)[k];
    if (v !== undefined && v !== null && typeof v !== "object") {
      out.push([k, String(v)]);
    }
    if (out.length >= 4) break;
  }
  return out;
}

interface EventNodeProps {
  event: AuditEvent;
  prev: AuditEvent | null;
  isFirst: boolean;
  isLast: boolean;
  index: number;
}

function EventNode({ event, prev, isFirst, isLast, index }: EventNodeProps) {
  const [open, setOpen] = useState(false);
  const color = outcomeColor(event.outcome);
  const details = keyDetails(event.detail);
  const sha = shortHash(event.input_sha256);
  const hash = shortHash(event.hash);
  const prevHash = shortHash(event.prev_hash);
  const hasRawDetail = event.detail && Object.keys(event.detail).length > 0;
  const sysHue = event.agent ? systemHueOf(event.agent) : null;

  // Does this event's prev_hash link back to the prior event's hash?
  const linked =
    !isFirst &&
    prev != null &&
    event.prev_hash != null &&
    prev.hash != null &&
    event.prev_hash === prev.hash;

  return (
    <li
      className="relative grid grid-cols-[28px_minmax(0,1fr)] gap-x-3 pb-5 last:pb-0"
      style={{ animation: `fade-in-up 0.4s ${Math.min(index, 12) * 28}ms both` }}
    >
      {/* ---- chain rail (left gutter) ---- */}
      <div className="relative flex justify-center">
        {!isFirst && (
          <span
            aria-hidden
            className="absolute top-[-20px] h-[28px] w-px"
            style={{
              background: linked
                ? `linear-gradient(to bottom, ${withAlpha(
                    outcomeColor(prev?.outcome),
                    0.5,
                  )}, ${withAlpha(color, 0.5)})`
                : withAlpha(COLORS.danger, 0.6),
              left: "50%",
            }}
          />
        )}
        {!isLast && (
          <span
            aria-hidden
            className="absolute top-3 h-full w-px"
            style={{ background: withAlpha(color, 0.32), left: "50%" }}
          />
        )}
        <span
          aria-hidden
          className="relative z-10 mt-1.5 flex h-3 w-3 items-center justify-center rounded-full"
          style={{
            background: COLORS.base,
            border: `1.5px solid ${color}`,
            boxShadow: `0 0 7px -1px ${withAlpha(color, 0.8)}`,
          }}
        >
          <span
            className="block h-1 w-1 rounded-full"
            style={{ background: color }}
          />
        </span>
      </div>

      {/* ---- event card ---- */}
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="metric text-[10px] text-ink-ghost">
            {String(event.seq ?? index + 1).padStart(2, "0")}
          </span>
          <span className="text-[13px] font-medium text-ink">{event.action}</span>
          <Pill outcome={event.outcome}>{event.outcome}</Pill>
          <span className="metric ml-auto text-[10px] text-ink-faint">
            {fmtTs(event.ts)}
          </span>
        </div>

        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-ink-faint">
          {event.agent && (
            <span className="metric inline-flex items-center gap-1 text-ink-muted">
              {sysHue && (
                <span
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ background: sysHue }}
                  aria-hidden
                />
              )}
              {resolveAgent(event.agent).label}
            </span>
          )}
          {event.actor_id && (
            <span>
              {event.actor_id}
              {event.actor_role && (
                <span className="text-ink-ghost"> · {event.actor_role}</span>
              )}
            </span>
          )}
          {event.policy_version && (
            <span className="metric text-ink-ghost">pol {event.policy_version}</span>
          )}
        </div>

        {details.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {details.map(([k, v]) => (
              <span
                key={k}
                className="inline-flex items-center gap-1 rounded-md border border-line bg-panel-2 px-1.5 py-0.5"
              >
                <span className="metric text-[10px] text-ink-faint">{k}</span>
                <span className="metric max-w-[16rem] truncate text-[10px] text-ink-muted">
                  {v}
                </span>
              </span>
            ))}
          </div>
        )}

        {/* hash-chain fingerprints — the tamper-evident link, made legible */}
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
          {sha && (
            <span
              className="metric text-[10px] text-ink-ghost"
              title={event.input_sha256 ?? undefined}
            >
              sha256 {sha}
            </span>
          )}
          {(hash || prevHash) && (
            <span className="inline-flex items-center gap-1 text-[10px]">
              {prevHash && (
                <span
                  className="metric text-ink-ghost"
                  title={`prev_hash ${event.prev_hash}`}
                >
                  {prevHash}
                </span>
              )}
              {prevHash && hash && (
                <span
                  aria-hidden
                  style={{ color: linked ? COLORS.ok : COLORS.danger }}
                  title={
                    linked
                      ? "links to previous event"
                      : isFirst
                        ? "genesis event"
                        : "chain link mismatch"
                  }
                >
                  ⛓
                </span>
              )}
              {hash && (
                <span
                  className="metric"
                  style={{ color: withAlpha(color, 0.85) }}
                  title={`hash ${event.hash}`}
                >
                  {hash}
                </span>
              )}
            </span>
          )}
        </div>

        {hasRawDetail && (
          <div className="mt-2">
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              className="focus-ring metric rounded text-[10px] text-ink-faint transition-colors hover:text-accent"
            >
              {open ? "▾ hide payload" : "▸ payload"}
            </button>
            {open && (
              <pre className="mt-1.5 max-h-72 overflow-auto rounded-md border border-line bg-base-2 p-2.5 text-[10.5px] leading-relaxed text-ink-muted">
                {JSON.stringify(event.detail, null, 2)}
              </pre>
            )}
          </div>
        )}
      </div>
    </li>
  );
}

/** Resolve an agent name to its system hue (offline-safe, via the resolver). */
function systemHueOf(agent: string): string {
  return systemHue(resolveAgent(agent).system);
}

interface RunTimelineProps {
  events: AuditEvent[];
}

export function RunTimeline({ events }: RunTimelineProps) {
  const [filter, setFilter] = useState<Outcome | "all">("all");

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const e of events) c[e.outcome] = (c[e.outcome] ?? 0) + 1;
    return c;
  }, [events]);

  const visible = useMemo(
    () => (filter === "all" ? events : events.filter((e) => e.outcome === filter)),
    [events, filter],
  );

  if (events.length === 0) {
    return (
      <div className="px-4 py-12 text-center text-sm text-ink-faint">
        no events recorded for this run yet — as it progresses, each hash-chained
        event appears here
      </div>
    );
  }

  const presentOutcomes = OUTCOME_ORDER.filter((o) => counts[o]);

  return (
    <div>
      {/* outcome filter rail */}
      <div className="flex flex-wrap items-center gap-1.5 border-b border-line px-4 py-2.5">
        <FilterChip
          active={filter === "all"}
          color={COLORS.accent}
          label="all"
          count={events.length}
          onClick={() => setFilter("all")}
        />
        {presentOutcomes.map((o) => (
          <FilterChip
            key={o}
            active={filter === o}
            color={OUTCOME_COLORS[o]}
            label={o}
            count={counts[o]}
            onClick={() => setFilter(o)}
          />
        ))}
      </div>

      {visible.length === 0 ? (
        <div className="px-4 py-10 text-center text-xs text-ink-faint">
          no {filter} events in this run
        </div>
      ) : (
        <ol className="px-4 pt-4 pb-2">
          {visible.map((event, i) => (
            <EventNode
              key={event.event_id ?? i}
              event={event}
              prev={i > 0 ? visible[i - 1] : null}
              isFirst={i === 0}
              isLast={i === visible.length - 1}
              index={i}
            />
          ))}
        </ol>
      )}
    </div>
  );
}

interface FilterChipProps {
  active: boolean;
  color: string;
  label: string;
  count: number;
  onClick: () => void;
}

function FilterChip({ active, color, label, count, onClick }: FilterChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="focus-ring inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[10px] tracking-wide transition-colors"
      style={{
        borderColor: active ? withAlpha(color, 0.5) : "var(--line)",
        background: active ? withAlpha(color, 0.14) : "transparent",
        color: active ? color : COLORS.inkFaint,
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ background: color, opacity: active ? 1 : 0.5 }}
        aria-hidden
      />
      {label}
      <span style={{ color: active ? color : COLORS.inkGhost }}>{count}</span>
    </button>
  );
}
