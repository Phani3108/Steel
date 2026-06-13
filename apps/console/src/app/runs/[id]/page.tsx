import { RunDetailView } from "./_components/RunDetailView";

/**
 * /runs/[id] — RUN DETAIL.
 *
 * The deep-linkable single-run view: the whole story of one procurement, from a
 * run_id you can now actually click. This is the minimal valid scaffold — summary
 * + journey + a timeline placeholder — wired to GET /runs/{id}/detail. Phase 2
 * enriches the timeline, cost ledger, and gate trail.
 *
 * Next 16: `params` is a Promise; we await it and hand the id to the client view.
 */
export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <RunDetailView runId={decodeURIComponent(id)} />;
}
