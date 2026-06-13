"use client";

import { useCallback, useState } from "react";

import { Panel, SectionHeader } from "@/components/ui";
import { JourneyBar } from "@/components/JourneyBar";
import {
  fetchRunEvents,
  fetchRuns,
  type AuditEvent,
  type RunSummary,
} from "@/lib/api";
import { usePoll } from "@/lib/usePoll";

import { ChainShield } from "./_components/ChainShield";
import { EventTimeline } from "./_components/EventTimeline";
import { RunList } from "./_components/RunList";
import { fetchAuditVerify, type AuditVerifyResult } from "./_components/auditApi";

export default function RunsPage() {
  // `picked` is the user's explicit selection; until they choose one we default
  // to the most recent run at render time (no setState-in-effect cascade).
  const [picked, setPicked] = useState<string | null>(null);

  // ---- runs index (left rail) ----
  const {
    data: runs,
    offline: runsOffline,
    loaded: runsLoaded,
  } = usePoll<RunSummary[]>(fetchRuns, 3000);

  const selected = picked ?? runs?.[0]?.run_id ?? null;

  // ---- selected run's events (right pane) — reset on run change via key ----
  const eventsFetcher = useCallback(
    () =>
      selected
        ? fetchRunEvents(selected)
        : Promise.resolve([] as AuditEvent[]),
    [selected],
  );
  const {
    data: events,
    offline: eventsOffline,
    loaded: eventsLoaded,
  } = usePoll<AuditEvent[]>(eventsFetcher, 3000, selected ?? "");

  // ---- chain verification (top-right shield) ----
  const {
    data: verify,
    offline: verifyOffline,
    loaded: verifyLoaded,
  } = usePoll<AuditVerifyResult>(fetchAuditVerify, 8000);

  const offline = runsOffline || eventsOffline;
  const runCount = runs?.length ?? 0;

  return (
    <div className="animate-fade-in-up">
      <SectionHeader
        kicker="safety · black box"
        title="Flight Recorder"
        subtitle="Every agent run and its tamper-evident audit trail. Each event is hash-chained to the one before it — the recorder is replayed and re-verified live."
        action={
          <ChainShield
            ok={verify ? verify.ok : null}
            checked={verify?.checked ?? 0}
            offline={verifyOffline}
            loaded={verifyLoaded}
          />
        }
      />

      {offline && (
        <p className="metric mt-4 inline-flex items-center gap-2 rounded-md border border-line bg-panel-2 px-3 py-1.5 text-[11px] text-ink-faint">
          <span
            className="h-1.5 w-1.5 rounded-full bg-warn"
            aria-hidden
          />
          live telemetry offline — showing last known recorder state
        </p>
      )}

      <div className="mt-6">
        <Panel accent="accent" title="procurement journey · you are here">
          <JourneyBar current="audit" size="sm" linked />
        </Panel>
      </div>

      <div className="mt-6 grid items-start gap-5 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        {/* runs index */}
        <Panel
          title="runs"
          accent="SAFETY"
          flush
          action={
            <span className="metric text-[10px] text-ink-faint">
              {runCount} logged
            </span>
          }
        >
          <div className="max-h-[calc(100vh-15rem)] overflow-y-auto">
            <RunList
              runs={runs ?? []}
              selected={selected}
              onSelect={setPicked}
              loaded={runsLoaded}
            />
          </div>
        </Panel>

        {/* audit trail */}
        <Panel
          title={
            selected ? (
              <span className="inline-flex items-baseline gap-2">
                <span className="label-cap">audit trail</span>
                <span className="metric text-[11px] text-ink-muted">
                  {selected}
                </span>
              </span>
            ) : (
              "audit trail"
            )
          }
          accent="accent"
          flush
        >
          {!selected ? (
            <div className="px-4 py-12 text-center text-sm text-ink-faint">
              select a run to replay its audit trail
            </div>
          ) : (
            <EventTimeline events={events ?? []} loaded={eventsLoaded} />
          )}
        </Panel>
      </div>
    </div>
  );
}
