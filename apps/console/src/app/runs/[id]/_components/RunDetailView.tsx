"use client";

import Link from "next/link";
import { useCallback, useMemo } from "react";

import { JourneyBar, type JourneyStep } from "@/components/JourneyBar";
import {
  EmptyState,
  Panel,
  Pill,
  ReferenceBadge,
  SectionHeader,
  Spinner,
  Stat,
} from "@/components/ui";
import { fetchRunDetail, fmtTs, fmtUsd, type RunDetail } from "@/lib/api";
import { COLORS, outcomeColor, systemHue, withAlpha } from "@/lib/theme";
import { usePoll } from "@/lib/usePoll";

import { resolveAgent } from "./agents";
import { RunCostBars } from "./RunCostBars";
import { RunGates } from "./RunGates";
import { RunReplay } from "./RunReplay";
import { RunTimeline } from "./RunTimeline";

/**
 * RunDetailView — THE unified run story. The deep-linkable single-run view every
 * other screen's run_id points to: one procurement, end to end.
 *
 *   • header — run_id, tenant, outcome, the agents it touched (system-hued), and
 *     its modeled total cost, with a JourneyBar marking how far it reached;
 *   • run replay — a live SVG that lays out those agents and replays the run's
 *     real hops as a travelling packet, so you watch it flow across the fleet;
 *   • audit trail — the hash-chained event timeline, tamper-evidence made legible;
 *   • cost by agent — modeled per-agent spend as a compact bar list;
 *   • gates — the human approvals it passed through, linking to /approvals if open.
 *
 * Polls GET /runs/{id}/detail every 3s. Graceful throughout: a not-found / offline
 * run shows a calm EmptyState with a link back to the recorder, never a crash.
 */
export function RunDetailView({ runId }: { runId: string }) {
  const fetcher = useCallback(() => fetchRunDetail(runId), [runId]);
  const { data, offline, loaded } = usePoll<RunDetail>(fetcher, 3000, runId);

  const booting = !loaded && data === null;
  const found = data?.found ?? false;

  // Infer where this run sits on the procurement journey from its state.
  const journeyStep: JourneyStep = useMemo(() => {
    if (!data) return "orchestrate";
    const pendingGate = data.approvals.some(
      (a) =>
        a.status === "pending" ||
        a.status === "requested" ||
        a.status === "open",
    );
    if (pendingGate) return "approve";
    const decidedGate = data.approvals.some(
      (a) => a.status === "approved" || a.status === "rejected",
    );
    const outcome = data.summary.outcome;
    if (outcome === "ok") return "audit";
    if (decidedGate) return "award";
    return "orchestrate";
  }, [data]);

  return (
    <div className="animate-fade-in-up space-y-6">
      <SectionHeader
        kicker="safety · run detail"
        title="Run story"
        subtitle="One procurement, end to end — the agents it touched, the path it took, what it cost, and the tamper-evident trail it left behind."
        action={
          <div className="flex items-center gap-2">
            <ReferenceBadge mode={offline ? "reference" : "live"} />
            <Link
              href="/runs"
              className="focus-ring rounded-md border border-line px-2.5 py-1 font-mono text-[11px] text-ink-muted transition-colors hover:text-ink"
            >
              ← all runs
            </Link>
          </div>
        }
      />

      {/* identity strip — the run_id you can finally land on, + outcome */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="label-cap">run_id</span>
        <span className="metric select-all text-[12px] text-ink">{runId}</span>
        {data?.summary.tenant_id && (
          <span className="metric text-[11px] text-ink-faint">
            tenant {data.summary.tenant_id}
          </span>
        )}
        {data?.summary.outcome && (
          <Pill outcome={data.summary.outcome}>{data.summary.outcome}</Pill>
        )}
      </div>

      {/* journey position */}
      <Panel accent="accent" title="procurement journey · you are here">
        <JourneyBar current={journeyStep} size="sm" linked />
      </Panel>

      {booting ? (
        <Panel>
          <div className="flex h-40 items-center justify-center">
            <Spinner label="loading run detail…" />
          </div>
        </Panel>
      ) : !found ? (
        <Panel>
          <EmptyState
            title={offline ? "control plane offline" : "run not found"}
            hint={
              offline
                ? "The recorder is unreachable right now. The link is valid — try again when the control plane is back."
                : `No run with id ${runId} is in the recorder. It may not have started yet, or the id is mistyped.`
            }
            action={
              <Link
                href="/runs"
                className="focus-ring rounded-md border border-line px-3 py-1.5 text-sm text-ink-muted transition-colors hover:text-ink"
              >
                back to the flight recorder
              </Link>
            }
          />
        </Panel>
      ) : (
        <>
          {/* ---- headline metrics ---- */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Panel>
              <Stat label="events" value={data!.summary.events} />
            </Panel>
            <Panel>
              <Stat
                label="agents touched"
                value={data!.summary.agents.length}
                color={COLORS.autonomy}
              />
            </Panel>
            <Panel>
              <Stat
                label="modeled cost"
                value={fmtUsd(data!.cost_total_usd)}
                color={COLORS.warn}
              />
              <div className="mt-2">
                <ReferenceBadge mode="modeled" />
              </div>
            </Panel>
            <Panel>
              <Stat
                label="outcome"
                value={
                  <span style={{ color: outcomeColor(data!.summary.outcome) }}>
                    {data!.summary.outcome ?? "—"}
                  </span>
                }
              />
            </Panel>
          </div>

          {/* ---- agents touched (system-hued chips → fleet) ---- */}
          {data!.summary.agents.length > 0 && (
            <Panel title="agents on this run">
              <div className="flex flex-wrap gap-2">
                {data!.summary.agents.map((a) => {
                  const meta = resolveAgent(a);
                  const hue = systemHue(meta.system);
                  return (
                    <Link
                      key={a}
                      href="/network"
                      title={`${a} · ${meta.system} — see it in the fleet`}
                      className="focus-ring inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 transition-transform hover:-translate-y-0.5"
                      style={{
                        background: withAlpha(hue, 0.1),
                        borderColor: withAlpha(hue, 0.3),
                      }}
                    >
                      <span
                        className="h-1.5 w-1.5 shrink-0 rounded-full"
                        style={{ background: hue, boxShadow: `0 0 6px -1px ${hue}` }}
                        aria-hidden
                      />
                      <span className="metric text-[11px] text-ink">{meta.label}</span>
                    </Link>
                  );
                })}
              </div>
            </Panel>
          )}

          {/* ---- THE run replay — watch the run flow across the fleet ---- */}
          <Panel
            accent="NETWORK"
            title="run replay"
            flush
            action={
              <span className="metric text-[10px] text-ink-faint">
                derived from the recorded event order
              </span>
            }
          >
            <div className="px-3 pt-3">
              <RunReplay events={data!.events} agents={data!.summary.agents} />
            </div>
          </Panel>

          {/* ---- main grid: audit trail | side rail ---- */}
          <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
            {/* audit trail — the hash-chained timeline */}
            <Panel
              accent="SAFETY"
              flush
              title={
                <span className="inline-flex items-baseline gap-2">
                  <span className="label-cap">audit trail</span>
                  <span className="metric text-[11px] text-ink-muted">
                    {data!.summary.events} event
                    {data!.summary.events === 1 ? "" : "s"}
                  </span>
                </span>
              }
            >
              <RunTimeline events={data!.events} />
            </Panel>

            {/* side rail: meta + gates + cost */}
            <div className="space-y-5">
              <Panel title="summary">
                <dl className="space-y-2 text-sm">
                  <Row label="tenant" value={data!.summary.tenant_id ?? "—"} />
                  <Row
                    label="started"
                    value={fmtTs(data!.summary.first_ts ?? undefined)}
                  />
                  <Row
                    label="last event"
                    value={fmtTs(data!.summary.last_ts ?? undefined)}
                  />
                  <Row label="hops replayed" value={hopLabel(data!)} />
                </dl>
              </Panel>

              <Panel accent="SAFETY" title="human gates">
                <RunGates approvals={data!.approvals} />
              </Panel>

              <Panel
                title="cost by agent"
                action={<ReferenceBadge mode="modeled" />}
              >
                <RunCostBars costs={data!.costs} total={data!.cost_total_usd} />
              </Panel>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/** Count distinct consecutive agent handoffs — the number of hops the replay shows. */
function hopLabel(data: RunDetail): string {
  let hops = 0;
  let prev: string | null = null;
  for (const e of data.events) {
    const cur = e.agent ?? null;
    if (cur && prev && cur !== prev) hops += 1;
    if (cur) prev = cur;
  }
  return `${hops} hop${hops === 1 ? "" : "s"}`;
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="label-cap shrink-0">{label}</dt>
      <dd className="metric min-w-0 truncate text-right text-[12px] text-ink">
        {value}
      </dd>
    </div>
  );
}
