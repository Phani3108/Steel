"use client";

import { useCallback, useState } from "react";

import { OfflineBanner } from "../../components/OfflineBanner";
import {
  fetchRunEvents,
  fetchRuns,
  fmtTs,
  fmtUsd,
  type AuditEvent,
  type Outcome,
  type RunSummary,
} from "../../lib/api";
import { usePoll } from "../../lib/usePoll";

const OUTCOME_STYLES: Record<Outcome, string> = {
  ok: "border-emerald-700/60 bg-emerald-950/50 text-emerald-400",
  denied: "border-red-700/60 bg-red-950/40 text-red-400",
  error: "border-rose-700/60 bg-rose-950/40 text-rose-400",
  escalated: "border-amber-700/60 bg-amber-950/40 text-amber-400",
  pending_approval: "border-sky-700/60 bg-sky-950/40 text-sky-400",
};

function OutcomeChip({ outcome }: { outcome: Outcome }) {
  const style = OUTCOME_STYLES[outcome] ?? "border-zinc-700 bg-zinc-900 text-zinc-400";
  return (
    <span className={`rounded-full border px-2 py-0.5 font-mono text-[10px] ${style}`}>
      {outcome}
    </span>
  );
}

function ActionChip({ action }: { action: string }) {
  return (
    <span className="rounded border border-zinc-700/80 bg-zinc-900 px-2 py-0.5 font-mono text-[11px] text-zinc-300">
      {action}
    </span>
  );
}

function EventRow({ event }: { event: AuditEvent }) {
  const hasDetail = event.detail && Object.keys(event.detail).length > 0;
  return (
    <li className="relative pb-5 pl-6 last:pb-0">
      {/* timeline rail + dot */}
      <span className="absolute top-1.5 left-0 h-full w-px bg-zinc-800" aria-hidden />
      <span
        className="absolute top-1.5 left-[-3px] h-[7px] w-[7px] rounded-full bg-zinc-600"
        aria-hidden
      />
      <div className="flex flex-wrap items-center gap-2">
        <ActionChip action={event.action} />
        <OutcomeChip outcome={event.outcome} />
        <span className="font-mono text-[11px] text-zinc-500">{fmtTs(event.ts)}</span>
      </div>
      <div className="mt-1.5 text-xs text-zinc-500">
        <span className="font-mono text-zinc-400">{event.agent ?? "-"}</span>
        {" · actor "}
        <span className="font-mono">{event.actor_id}</span>
        {" ("}
        {event.actor_role}
        {")"}
        {event.policy_version && (
          <span className="ml-2 font-mono text-zinc-600">policy {event.policy_version}</span>
        )}
      </div>
      {hasDetail && (
        <details className="mt-1.5">
          <summary className="cursor-pointer font-mono text-[11px] text-zinc-600 hover:text-zinc-400">
            detail
          </summary>
          <pre className="mt-1 overflow-x-auto rounded border border-zinc-800 bg-zinc-900/60 p-2.5 font-mono text-[11px] leading-relaxed text-zinc-400">
            {JSON.stringify(event.detail, null, 2)}
          </pre>
        </details>
      )}
    </li>
  );
}

export default function RunsPage() {
  const [selected, setSelected] = useState<string | null>(null);

  const { data: runs, offline: runsOffline, loaded: runsLoaded } = usePoll<RunSummary[]>(
    fetchRuns,
    2000,
  );

  const eventsFetcher = useCallback(
    () => (selected ? fetchRunEvents(selected) : Promise.resolve([] as AuditEvent[])),
    [selected],
  );
  const { data: events, offline: eventsOffline, loaded: eventsLoaded } = usePoll<AuditEvent[]>(
    eventsFetcher,
    2000,
    selected ?? "",
  );

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-zinc-50">Runs</h1>
      <p className="mt-1 text-sm text-zinc-400">
        Every agent run and its tamper-evident audit timeline, refreshed every 2s.
      </p>

      <div className="mt-6">
        <OfflineBanner show={runsOffline || eventsOffline} />

        <div className="grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
          {/* runs list */}
          <div className="overflow-hidden rounded-lg border border-zinc-800">
            <div className="border-b border-zinc-800 bg-zinc-900/60 px-4 py-2.5 font-mono text-[11px] uppercase tracking-wider text-zinc-500">
              runs
            </div>
            <ul className="divide-y divide-zinc-800/70">
              {(runs ?? []).map((run) => {
                const active = run.run_id === selected;
                return (
                  <li key={run.run_id}>
                    <button
                      onClick={() => setSelected(run.run_id)}
                      className={`w-full px-4 py-3 text-left transition-colors ${
                        active ? "bg-zinc-800/70" : "hover:bg-zinc-900/50"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="truncate font-mono text-sm text-zinc-200">
                          {run.run_id}
                        </span>
                        {run.cost_usd !== undefined && (
                          <span className="shrink-0 font-mono text-xs text-emerald-400">
                            {fmtUsd(run.cost_usd)}
                          </span>
                        )}
                      </div>
                      <div className="mt-1 flex flex-wrap gap-x-3 text-[11px] text-zinc-500">
                        {run.agent != null && <span className="font-mono">{run.agent}</span>}
                        {run.tenant_id && <span>{run.tenant_id}</span>}
                        {run.event_count !== undefined && <span>{run.event_count} events</span>}
                        {(run.last_ts ?? run.started_at) && (
                          <span>{fmtTs(run.last_ts ?? run.started_at)}</span>
                        )}
                      </div>
                    </button>
                  </li>
                );
              })}
              {(runs ?? []).length === 0 && (
                <li className="px-4 py-10 text-center text-sm text-zinc-500">
                  {runsLoaded ? "no runs yet" : "loading…"}
                </li>
              )}
            </ul>
          </div>

          {/* audit timeline */}
          <div className="overflow-hidden rounded-lg border border-zinc-800">
            <div className="border-b border-zinc-800 bg-zinc-900/60 px-4 py-2.5 font-mono text-[11px] uppercase tracking-wider text-zinc-500">
              audit timeline{selected ? ` — ${selected}` : ""}
            </div>
            <div className="p-5">
              {!selected && (
                <p className="py-6 text-center text-sm text-zinc-500">
                  select a run to inspect its audit trail
                </p>
              )}
              {selected && !eventsLoaded && (
                <p className="py-6 text-center text-sm text-zinc-500">loading…</p>
              )}
              {selected && eventsLoaded && (events ?? []).length === 0 && (
                <p className="py-6 text-center text-sm text-zinc-500">
                  no events recorded for this run
                </p>
              )}
              {selected && (events ?? []).length > 0 && (
                <ol>
                  {(events ?? []).map((event) => (
                    <EventRow key={event.event_id} event={event} />
                  ))}
                </ol>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
