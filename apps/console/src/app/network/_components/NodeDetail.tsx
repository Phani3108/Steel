"use client";

import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";

import {
  AutonomyMeter,
  Chip,
  EmptyState,
  GaugeRing,
  Pill,
} from "@/components/ui";
import type { AgentRecord, RunSummary } from "@/lib/api";
import { fmtTs } from "@/lib/api";
import { AUTONOMY_LABELS, systemHue, withAlpha } from "@/lib/theme";

import type { NodeView } from "./resolve";

interface NodeDetailProps {
  node: NodeView | null;
  /** True when the registry call failed and this is fleet-fallback data. */
  offline: boolean;
}

/**
 * The inspector — the right-hand instrument that reads out the selected node.
 * For agents it shows the full AgentRecord (status, autonomy, pipeline, skills,
 * mandate, scorecard gauge). For services/human it shows the lighter profile.
 */
export function NodeDetail({ node }: NodeDetailProps) {
  return (
    <div className="relative min-h-[420px]">
      <AnimatePresence mode="wait">
        {node ? (
          <motion.div
            key={node.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
          >
            <Detail node={node} />
          </motion.div>
        ) : (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <EmptyState
              title="select a node"
              hint="Click any node in the fleet graph to inspect its mandate, autonomy, skills, and latest eval scorecard."
              icon={<InspectGlyph />}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Detail({ node }: { node: NodeView }) {
  const hue = systemHue(node.system);
  const record = node.record;

  return (
    <div className="flex flex-col gap-5 p-4">
      {/* identity header */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ background: hue, boxShadow: `0 0 8px -1px ${hue}` }}
              aria-hidden
            />
            <span
              className="metric truncate text-[11px] font-medium tracking-wider"
              style={{ color: hue }}
            >
              {node.system}
            </span>
            <span className="text-[10px] text-ink-ghost">
              {node.role === "human"
                ? "operator"
                : node.role === "service"
                  ? "service · mcp"
                  : "agent"}
            </span>
          </div>
          <h3 className="mt-1.5 truncate text-base font-semibold text-ink">
            {node.label}
          </h3>
          <p className="metric mt-0.5 truncate text-[11px] text-ink-faint">
            {node.id}
          </p>
        </div>
        {record ? (
          <Pill status={record.status} solid={record.status === "active"}>
            {record.status}
          </Pill>
        ) : (
          <Pill tone="info">{node.role}</Pill>
        )}
      </div>

      <p className="text-[13px] leading-relaxed text-ink-muted">
        {node.description}
      </p>

      {record ? (
        <AgentBody record={record} hue={hue} />
      ) : (
        <div className="hairline pt-4">
          <p className="text-xs leading-relaxed text-ink-faint">
            Infrastructure node — no autonomy mandate of its own. It is invoked
            by agents over the mesh as part of their pipelines.
          </p>
        </div>
      )}

      {/* recent runs this node took part in — deep-links into /runs/{id} */}
      <RecentRuns runs={node.runs} hue={hue} />
    </div>
  );
}

/**
 * The runs this node appears in, newest first, each a deep-link to the single-
 * run detail view — closing the audit's "you get a run_id you can't click" gap.
 * Renders nothing if the live runs feed couldn't be joined onto this agent.
 */
function RecentRuns({ runs, hue }: { runs: RunSummary[]; hue: string }) {
  if (runs.length === 0) return null;
  const shown = runs.slice(0, 6);

  return (
    <div className="hairline pt-4">
      <span className="label-cap">recent runs</span>
      <ul className="mt-2 flex flex-col gap-1">
        {shown.map((r) => (
          <li key={r.run_id}>
            <Link
              href={`/runs/${encodeURIComponent(r.run_id)}`}
              className="focus-ring group flex items-center justify-between gap-2 rounded-md border border-line bg-panel-2 px-2.5 py-1.5 transition-colors hover:border-line-strong"
              style={{ borderColor: withAlpha(hue, 0.14) }}
            >
              <span className="metric min-w-0 flex-1 truncate text-[11px] text-ink-muted group-hover:text-ink">
                {r.run_id}
              </span>
              <span className="metric shrink-0 text-[10px] text-ink-faint">
                {fmtTs(r.last_ts ?? r.started_at)}
              </span>
              <span
                aria-hidden
                className="shrink-0 text-[11px] text-ink-ghost transition-colors group-hover:text-accent"
              >
                open →
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

function AgentBody({ record, hue }: { record: AgentRecord; hue: string }) {
  const scorecard = record.scorecard;

  return (
    <>
      {/* autonomy + pipeline strip */}
      <div className="hairline grid grid-cols-2 gap-4 pt-4">
        <Field label="autonomy">
          <AutonomyMeter level={record.autonomy_level} showLabel={false} size="sm" />
          <span className="mt-1 block text-[11px] text-ink-faint">
            L{record.autonomy_level} · {AUTONOMY_LABELS[record.autonomy_level]}
          </span>
        </Field>
        <Field label="pipeline">
          <span className="metric text-[13px] text-ink">{record.pipeline}</span>
          {record.mandate_usd != null && (
            <span className="mt-1 block text-[11px] text-ink-faint">
              mandate{" "}
              <span className="metric text-ink-muted">
                ${record.mandate_usd.toLocaleString()}
              </span>
            </span>
          )}
        </Field>
      </div>

      {/* skills */}
      {record.skills.length > 0 && (
        <div className="hairline pt-4">
          <span className="label-cap">skills</span>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {record.skills.map((s) => (
              <Chip key={s} color={hue}>
                {s}
              </Chip>
            ))}
          </div>
        </div>
      )}

      {/* scorecard */}
      <div className="hairline pt-4">
        <span className="label-cap">latest scorecard</span>
        {scorecard ? (
          <div
            className="mt-2 flex items-center gap-4 rounded-md border p-3"
            style={{
              borderColor: withAlpha(hue, 0.18),
              background: withAlpha(hue, 0.04),
            }}
          >
            <GaugeRing value={scorecard.pass_rate} size={72} thickness={6} />
            <div className="min-w-0">
              <p className="metric truncate text-[12px] text-ink">
                {scorecard.suite}
              </p>
              <p className="mt-1 text-[11px] text-ink-faint">
                <span className="metric text-ok">{scorecard.n_passed}</span>
                <span className="text-ink-ghost"> / </span>
                <span className="metric text-ink-muted">{scorecard.n_cases}</span>{" "}
                cases passed
              </p>
            </div>
          </div>
        ) : (
          <p className="mt-2 text-[11px] text-ink-faint">
            No scorecard yet —{" "}
            <span className="text-warn">no scorecard, no ship.</span>
          </p>
        )}
      </div>
    </>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <span className="label-cap">{label}</span>
      <div className="mt-1.5">{children}</div>
    </div>
  );
}

function InspectGlyph() {
  return (
    <svg width={40} height={40} viewBox="0 0 40 40" fill="none" aria-hidden>
      <circle cx={17} cy={17} r={10} stroke="currentColor" strokeWidth={1.5} />
      <line
        x1={24.5}
        y1={24.5}
        x2={33}
        y2={33}
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinecap="round"
      />
      <circle cx={17} cy={17} r={3.5} fill="currentColor" opacity={0.4} />
    </svg>
  );
}
