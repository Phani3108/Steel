/**
 * Deterministic layered layout for the fleet network graph.
 *
 * No physics engine — positions are computed from graph structure so the same
 * topology always renders identically. We assign each node a "rank" (its BFS
 * depth from the human/source roots), then space nodes evenly within each rank
 * column. The result is a clean left-to-right A2A flow:
 *
 *   human → orchestrator → { triage, risk, spend, sourcing } → mcp servers
 *   supplier-intel → cortex  (a parallel lane that has no inbound edge)
 *
 * Everything here is pure: given the same nodes/edges it returns the same map.
 */

import type { NetworkEdge, NetworkNode } from "@/lib/api";

export interface LaidOutNode extends NetworkNode {
  x: number;
  y: number;
  /** Layer index (column) — 0 is the leftmost source rank. */
  rank: number;
}

export interface LaidOutEdge extends NetworkEdge {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  /** Stable id for keys / packet animation. */
  id: string;
}

export interface GraphLayout {
  nodes: LaidOutNode[];
  edges: LaidOutEdge[];
  width: number;
  height: number;
}

export interface LayoutOptions {
  /** Horizontal gap between rank columns. */
  colGap?: number;
  /** Vertical gap between sibling nodes in a column. */
  rowGap?: number;
  /** Outer padding around the whole graph (room for node radius + labels). */
  padX?: number;
  padY?: number;
}

const DEFAULTS: Required<LayoutOptions> = {
  colGap: 188,
  rowGap: 96,
  padX: 96,
  padY: 64,
};

/**
 * Assign a rank (column) to every node via longest-path layering from the
 * source roots (nodes with no inbound edges). Longest-path keeps a node to the
 * right of *all* its parents, so edges always point forward — no back-arrows.
 */
function rankNodes(
  nodes: NetworkNode[],
  edges: NetworkEdge[],
): Map<string, number> {
  const ids = new Set(nodes.map((n) => n.id));
  const incoming = new Map<string, number>();
  const outAdj = new Map<string, string[]>();
  for (const n of nodes) {
    incoming.set(n.id, 0);
    outAdj.set(n.id, []);
  }
  for (const e of edges) {
    if (!ids.has(e.source) || !ids.has(e.target)) continue;
    incoming.set(e.target, (incoming.get(e.target) ?? 0) + 1);
    outAdj.get(e.source)!.push(e.target);
  }

  // Kahn's algorithm carrying the max rank forward (longest-path layering).
  const rank = new Map<string, number>();
  const indeg = new Map(incoming);
  const queue: string[] = [];
  for (const n of nodes) {
    if ((indeg.get(n.id) ?? 0) === 0) {
      rank.set(n.id, 0);
      queue.push(n.id);
    }
  }
  while (queue.length > 0) {
    const u = queue.shift()!;
    const ru = rank.get(u) ?? 0;
    for (const v of outAdj.get(u) ?? []) {
      rank.set(v, Math.max(rank.get(v) ?? 0, ru + 1));
      const d = (indeg.get(v) ?? 0) - 1;
      indeg.set(v, d);
      if (d === 0) queue.push(v);
    }
  }
  // Any node untouched (e.g. part of a cycle — shouldn't happen here) → rank 0.
  for (const n of nodes) if (!rank.has(n.id)) rank.set(n.id, 0);
  return rank;
}

/**
 * Compute deterministic x/y for every node and resolve edge endpoints.
 * Within a column, nodes keep their original topology order (stable) and are
 * vertically centered so the whole graph balances around the mid-line.
 */
export function computeLayout(
  nodes: NetworkNode[],
  edges: NetworkEdge[],
  opts: LayoutOptions = {},
): GraphLayout {
  const { colGap, rowGap, padX, padY } = { ...DEFAULTS, ...opts };
  const rank = rankNodes(nodes, edges);

  // Bucket nodes by rank, preserving input order for stability.
  const columns = new Map<number, NetworkNode[]>();
  let maxRank = 0;
  for (const n of nodes) {
    const r = rank.get(n.id) ?? 0;
    maxRank = Math.max(maxRank, r);
    if (!columns.has(r)) columns.set(r, []);
    columns.get(r)!.push(n);
  }

  // Tallest column drives the vertical span; others center within it.
  let maxRows = 1;
  for (const col of columns.values()) maxRows = Math.max(maxRows, col.length);
  const spanH = (maxRows - 1) * rowGap;

  const placed = new Map<string, LaidOutNode>();
  for (let r = 0; r <= maxRank; r++) {
    const col = columns.get(r) ?? [];
    const colSpan = (col.length - 1) * rowGap;
    const top = padY + (spanH - colSpan) / 2;
    col.forEach((n, i) => {
      placed.set(n.id, {
        ...n,
        rank: r,
        x: padX + r * colGap,
        y: top + i * rowGap,
      });
    });
  }

  const laidOutNodes = [...placed.values()];
  const width = padX * 2 + maxRank * colGap;
  const height = padY * 2 + spanH;

  const laidOutEdges: LaidOutEdge[] = [];
  for (const e of edges) {
    const a = placed.get(e.source);
    const b = placed.get(e.target);
    if (!a || !b) continue;
    laidOutEdges.push({
      ...e,
      id: `${e.source}->${e.target}`,
      x1: a.x,
      y1: a.y,
      x2: b.x,
      y2: b.y,
    });
  }

  return { nodes: laidOutNodes, edges: laidOutEdges, width, height };
}

/**
 * A smooth cubic-bezier path between two points, bowed horizontally so the
 * link reads as a flowing cable rather than a straight stick. Control points
 * sit at the horizontal midpoint, which keeps left→right edges graceful and
 * same-column / vertical edges gently curved.
 */
export function edgePath(e: { x1: number; y1: number; x2: number; y2: number }): string {
  const dx = e.x2 - e.x1;
  const cx = Math.abs(dx) * 0.5;
  const c1x = e.x1 + cx;
  const c2x = e.x2 - cx;
  return `M ${e.x1} ${e.y1} C ${c1x} ${e.y1}, ${c2x} ${e.y2}, ${e.x2} ${e.y2}`;
}
