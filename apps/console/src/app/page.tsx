"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { useCallback, useMemo, useState } from "react";

import { JourneyBar } from "@/components/JourneyBar";
import {
  LiveDot,
  Panel,
  Pill,
  ReferenceBadge,
  Spinner,
  Term,
} from "@/components/ui";
import {
  fetchNetwork,
  fetchRegistry,
  fetchRuns,
  startSampleProcurement,
  type AgentRecord,
  type NetworkTopology,
  type RunSummary,
} from "@/lib/api";
import { API_BASE } from "@/lib/api";
import { REFERENCE_AGENTS } from "@/lib/fleet";
import { COLORS, SYSTEMS, withAlpha } from "@/lib/theme";
import { usePoll } from "@/lib/usePoll";

/** Minimal approvals shape — Home only needs the count. */
async function fetchApprovalsCount(): Promise<number> {
  const res = await fetch(`${API_BASE}/approvals`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET /approvals -> ${res.status}`);
  const data = (await res.json()) as unknown;
  return Array.isArray(data) ? data.length : 0;
}

/**
 * HOME — the orientation screen. The one place a first-timer lands and instantly
 * gets it: what the platform does, the journey a procurement takes, and where to
 * start. Live counts flow through the journey; one button runs a whole sample
 * procurement end-to-end and drops you on its run-detail view.
 */
export default function HomePage() {
  const router = useRouter();

  const runs = usePoll<RunSummary[]>(fetchRuns, 4000);
  const approvals = usePoll<number>(fetchApprovalsCount, 4000);
  const registry = usePoll<AgentRecord[]>(fetchRegistry, 8000);
  const network = usePoll<NetworkTopology>(fetchNetwork, 8000);

  const [launching, setLaunching] = useState(false);
  const [launchErr, setLaunchErr] = useState<string | null>(null);

  const runList = runs.data ?? [];
  const runCount = runList.length;
  const pendingApprovals = approvals.data ?? 0;

  // Recent awards: runs whose outcome reads as an award/ok (best-effort).
  const recentAwards = useMemo(
    () =>
      runList.filter((r) => {
        const o = String(r.outcome ?? r.status ?? "").toLowerCase();
        return o.includes("award") || o === "ok";
      }).length,
    [runList],
  );

  // Fleet counts — live registry, else reference fallback.
  const agentsActive =
    registry.data && registry.data.length > 0
      ? registry.data.filter((a) => a.status === "active").length
      : REFERENCE_AGENTS.length;
  const agentsLive = Boolean(registry.data && registry.data.length > 0);

  const systemsOnline = SYSTEMS.length;
  const totalHops = network.data?.total_hops ?? 0;
  const meshLive = Boolean(network.data?.live);

  const controlPlaneOffline =
    runs.offline && approvals.offline && registry.offline && network.offline;

  const journeyCounts = {
    intake: runCount,
    orchestrate: runCount,
    approve: pendingApprovals,
    award: recentAwards,
    audit: runCount,
  };

  const runSample = useCallback(async () => {
    setLaunching(true);
    setLaunchErr(null);
    try {
      const res = await startSampleProcurement();
      if (res?.run_id) {
        router.push(`/runs/${encodeURIComponent(res.run_id)}`);
        return;
      }
      throw new Error("no run_id returned");
    } catch {
      setLaunchErr(
        "Couldn't reach the control plane — start the API (localhost:8400) and try again.",
      );
      setLaunching(false);
    }
  }, [router]);

  return (
    <div className="space-y-10">
      {/* ───────────────────────── hero ───────────────────────── */}
      <section className="relative">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="flex flex-wrap items-center gap-3"
        >
          <span className="label-cap text-accent">steel · cockpit</span>
          {controlPlaneOffline ? (
            <ReferenceBadge mode="reference" />
          ) : (
            <ReferenceBadge mode="live" />
          )}
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.05, ease: [0.22, 1, 0.36, 1] }}
          className="mt-3 max-w-3xl text-4xl font-semibold leading-[1.1] tracking-tight text-ink sm:text-5xl"
        >
          Autonomous procurement,{" "}
          <span className="text-accent">governed.</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.18 }}
          className="mt-4 max-w-2xl text-base leading-relaxed text-ink-muted"
        >
          Agents source, negotiate, and award under human-approved, fully audited
          control — every{" "}
          <Term k="mandate" />, every{" "}
          <Term k="gate" />, every{" "}
          <Term k="a2a" /> hop on the record.
        </motion.p>

        {/* run-a-sample CTA */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.28 }}
          className="mt-6 flex flex-wrap items-center gap-4"
        >
          <button
            type="button"
            onClick={runSample}
            disabled={launching}
            className="focus-ring group relative inline-flex items-center gap-2.5 overflow-hidden rounded-lg border border-accent/50 bg-accent/10 px-5 py-3 text-sm font-medium text-ink transition-colors hover:bg-accent/20 disabled:cursor-wait disabled:opacity-80"
          >
            <span
              aria-hidden
              className="absolute inset-0 opacity-0 transition-opacity group-hover:opacity-100"
              style={{ boxShadow: "var(--glow-accent)" }}
            />
            {launching ? (
              <Spinner size={16} />
            ) : (
              <span className="relative text-accent" aria-hidden>
                ▶
              </span>
            )}
            <span className="relative">
              {launching ? "Running sample procurement…" : "Run a sample procurement"}
            </span>
          </button>
          <span className="max-w-xs text-[12px] leading-relaxed text-ink-faint">
            Launches one full run — intake → source → award → audit — and opens its
            detail view. Synthetic data, no real spend.
          </span>
        </motion.div>

        {launchErr && (
          <p className="mt-3 inline-flex items-center gap-2 rounded-md border border-danger/40 bg-danger/10 px-3 py-1.5 text-[12px] text-danger">
            {launchErr}
          </p>
        )}
      </section>

      {/* ──────────────── the procurement journey (big) ──────────────── */}
      <section>
        <Panel accent="accent" grid title="the procurement journey">
          <div className="px-1 pb-2 pt-3 sm:px-3">
            <JourneyBar size="lg" counts={journeyCounts} linked current="orchestrate" />
          </div>
          <p className="mt-4 border-t border-line px-1 pt-3 text-center text-[11.5px] text-ink-faint sm:px-3">
            live counts flow through each stage — click a stage to jump to its
            screen, or follow one procurement end to end
          </p>
        </Panel>
      </section>

      {/* ──────────────── quick-start cards ──────────────── */}
      <section>
        <div className="label-cap mb-3">start here</div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <QuickCard
            href="/orchestrate"
            title="Run a procurement"
            desc="Launch an intake and watch the fleet source it live."
            color={COLORS.accent}
            icon={
              <path
                d="M5 4l14 8-14 8V4z"
                fill="currentColor"
                stroke="currentColor"
                strokeWidth="1.4"
                strokeLinejoin="round"
              />
            }
          />
          <QuickCard
            href="/approvals"
            title="Review gates"
            badge={pendingApprovals > 0 ? pendingApprovals : undefined}
            desc="Approve or reject runs paused at a human gate."
            color={COLORS.info}
            icon={
              <>
                <path
                  d="M5 13l4 4L19 7"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill="none"
                />
              </>
            }
          />
          <QuickCard
            href="/runs"
            title="Audit trail"
            desc="Replay any run's tamper-evident, hash-chained record."
            color={COLORS.danger}
            icon={
              <>
                <rect
                  x="4"
                  y="4"
                  width="16"
                  height="16"
                  rx="3"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  fill="none"
                />
                <path
                  d="M8 9h8M8 13h8M8 17h5"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </>
            }
          />
          <QuickCard
            href="/chat"
            title="Ask the data"
            desc="Query the procurement world with cited retrieval."
            color={COLORS.autonomy}
            icon={
              <path
                d="M4 5h16v10H9l-5 4V5z"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinejoin="round"
                fill="none"
              />
            }
          />
        </div>
      </section>

      {/* ──────────────── fleet at a glance ──────────────── */}
      <section>
        <Panel
          flush
          title={
            <span className="inline-flex items-center gap-2">
              <span className="label-cap">fleet at a glance</span>
              {meshLive ? (
                <LiveDot live size={7} />
              ) : (
                <LiveDot live={false} color="var(--ink-faint)" size={7} />
              )}
            </span>
          }
          action={
            <div className="flex items-center gap-2">
              <Link
                href="/network"
                className="focus-ring rounded px-2 py-0.5 font-mono text-[10px] text-ink-faint transition-colors hover:text-ink"
              >
                mesh →
              </Link>
              <Link
                href="/catalog"
                className="focus-ring rounded px-2 py-0.5 font-mono text-[10px] text-ink-faint transition-colors hover:text-ink"
              >
                architecture →
              </Link>
            </div>
          }
        >
          <div className="grid grid-cols-2 divide-x divide-line sm:grid-cols-4">
            <GlanceStat
              label="agents active"
              value={agentsActive}
              hint={agentsLive ? "live registry" : "reference fleet"}
              color={COLORS.autonomy}
            />
            <GlanceStat
              label="systems online"
              value={systemsOnline}
              hint="powertrain → cockpit"
              color={COLORS.accent}
            />
            <GlanceStat
              label="a2a hops"
              value={totalHops}
              hint="agent handoffs"
              color={COLORS.ok}
            />
            <GlanceStat
              label="runs logged"
              value={runCount}
              hint="in the recorder"
              color={COLORS.danger}
            />
          </div>
        </Panel>
      </section>
    </div>
  );
}

/* ─────────────────────────── sub-components ─────────────────────────── */

function QuickCard({
  href,
  title,
  desc,
  color,
  icon,
  badge,
}: {
  href: string;
  title: string;
  desc: string;
  color: string;
  icon: React.ReactNode;
  badge?: number;
}) {
  return (
    <Link
      href={href}
      className="focus-ring group panel relative flex flex-col gap-3 overflow-hidden p-4 transition-transform hover:-translate-y-0.5"
    >
      <span
        aria-hidden
        className="absolute inset-x-0 top-0 h-px opacity-0 transition-opacity group-hover:opacity-100"
        style={{ background: `linear-gradient(to right, ${color}, transparent 70%)` }}
      />
      <div className="flex items-start justify-between">
        <span
          className="flex h-9 w-9 items-center justify-center rounded-md border"
          style={{
            color,
            borderColor: withAlpha(color, 0.35),
            background: withAlpha(color, 0.1),
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden>
            {icon}
          </svg>
        </span>
        {badge !== undefined && (
          <Pill tone="info" solid className="!text-[10px]">
            {badge}
          </Pill>
        )}
      </div>
      <div>
        <div className="flex items-center gap-1.5 text-sm font-medium text-ink">
          {title}
          <span
            aria-hidden
            className="text-ink-faint transition-transform group-hover:translate-x-0.5"
          >
            →
          </span>
        </div>
        <p className="mt-1 text-[12px] leading-relaxed text-ink-faint">{desc}</p>
      </div>
    </Link>
  );
}

function GlanceStat({
  label,
  value,
  hint,
  color,
}: {
  label: string;
  value: number;
  hint: string;
  color: string;
}) {
  return (
    <div className="flex flex-col gap-1 px-4 py-4 sm:px-5">
      <span className="label-cap">{label}</span>
      <span className="metric text-2xl font-semibold" style={{ color }}>
        {value}
      </span>
      <span className="text-[10px] text-ink-faint">{hint}</span>
    </div>
  );
}
