/**
 * Catalog data layer — merges the live registry (when /registry answers) onto
 * the canonical reference fleet, and lays the six systems out on a fixed SVG
 * "blueprint" grid so the exploded-vehicle diagram is deterministic.
 *
 * Route-local (per phase-2 rules): nothing here is exported to other routes.
 */

import type { AgentRecord, Scorecard } from "@/lib/api";
import {
  REFERENCE_FLEET,
  type FleetPart,
  type FleetSystem,
  type Pipeline,
} from "@/lib/fleet";
import { SYSTEMS, type Status, type System } from "@/lib/theme";

/** A part resolved for the diagram — reference shape, optionally enriched live. */
export interface CatalogPart {
  name: string;
  system: System;
  purpose: string;
  status: Status;
  isAgent: boolean;
  autonomy_level?: number;
  pipeline?: Pipeline;
  skills?: string[];
  mandate_usd?: number | null;
  scorecard?: Scorecard | null;
  /** True when this part's status/scorecard came from a live /registry record. */
  live: boolean;
}

export interface CatalogSystem {
  system: System;
  tagline: string;
  parts: CatalogPart[];
}

function fromReference(part: FleetPart): CatalogPart {
  return {
    name: part.name,
    system: part.system,
    purpose: part.purpose,
    status: part.status,
    isAgent: Boolean(part.isAgent),
    autonomy_level: part.autonomy_level,
    pipeline: part.pipeline,
    skills: part.skills,
    mandate_usd: part.mandate_usd,
    scorecard: null,
    live: false,
  };
}

/**
 * Merge: start from the human-authored reference fleet (canonical structure),
 * then overlay any matching live registry record (status, scorecard, autonomy,
 * mandate, skills). Registry parts not present in the reference are appended to
 * their system so a freshly-registered agent still appears.
 */
export function buildCatalog(
  registry: AgentRecord[] | null,
): { systems: CatalogSystem[]; live: boolean } {
  const live = Array.isArray(registry) && registry.length > 0;
  const byName = new Map<string, AgentRecord>();
  if (live) for (const r of registry!) byName.set(r.name, r);

  const seen = new Set<string>();

  const systems: CatalogSystem[] = REFERENCE_FLEET.map((sys: FleetSystem) => {
    const parts = sys.parts.map((p) => {
      const base = fromReference(p);
      const rec = byName.get(p.name);
      if (!rec) return base;
      seen.add(p.name);
      return {
        ...base,
        status: rec.status,
        purpose: rec.description || base.purpose,
        autonomy_level: rec.autonomy_level ?? base.autonomy_level,
        pipeline: rec.pipeline ?? base.pipeline,
        skills: rec.skills?.length ? rec.skills : base.skills,
        mandate_usd: rec.mandate_usd ?? base.mandate_usd,
        scorecard: rec.scorecard ?? null,
        live: true,
      };
    });
    return { system: sys.system, tagline: sys.tagline, parts };
  });

  // Append any live agents the reference fleet doesn't know about.
  if (live) {
    for (const rec of registry!) {
      if (seen.has(rec.name)) continue;
      const target = systems.find((s) => s.system === rec.system);
      if (!target) continue;
      target.parts.push({
        name: rec.name,
        system: rec.system,
        purpose: rec.description,
        status: rec.status,
        isAgent: rec.pipeline === "orchestrate" || rec.skills.length > 0,
        autonomy_level: rec.autonomy_level,
        pipeline: rec.pipeline,
        skills: rec.skills,
        mandate_usd: rec.mandate_usd,
        scorecard: rec.scorecard,
        live: true,
      });
    }
  }

  return { systems, live };
}

// --------------------------------------------------------------- headline ----

export interface HeadlineStats {
  partsTotal: number;
  partsActive: number;
  agentsTotal: number;
  agentsActive: number;
  systemsOnline: number;
  systemsTotal: number;
  /** Mean pass-rate across agents that have a scorecard (0..1), or null. */
  avgPassRate: number | null;
  scoredAgents: number;
}

export function headlineStats(systems: CatalogSystem[]): HeadlineStats {
  const parts = systems.flatMap((s) => s.parts);
  const agents = parts.filter((p) => p.isAgent);
  const scored = agents.filter((a) => a.scorecard);
  const avg =
    scored.length > 0
      ? scored.reduce((sum, a) => sum + (a.scorecard?.pass_rate ?? 0), 0) /
        scored.length
      : null;

  const systemsOnline = systems.filter((s) =>
    s.parts.some((p) => p.status === "active"),
  ).length;

  return {
    partsTotal: parts.length,
    partsActive: parts.filter((p) => p.status === "active").length,
    agentsTotal: agents.length,
    agentsActive: agents.filter((a) => a.status === "active").length,
    systemsOnline,
    systemsTotal: SYSTEMS.length,
    avgPassRate: avg,
    scoredAgents: scored.length,
  };
}

// ----------------------------------------------------------- the blueprint ----
// A fixed schematic layout for the exploded-vehicle diagram. The platform is a
// central vertical spine; the six systems branch off it (three per side),
// ordered front→rear like a real drivetrain. Coordinates are in a 1000×780
// viewBox the diagram component scales into. Row heights leave room for the
// densest bay (NETWORK: 8 parts → 4 rows ≈ 214px) without overflowing.

export const VIEW_W = 1000;
export const VIEW_H = 780;

/** Where each system bay sits and which side of the spine it docks to. */
export interface SystemBay {
  system: System;
  /** Bay anchor (top-left of the bay's part column). */
  x: number;
  y: number;
  /** Which side the bay docks to the spine. */
  side: "left" | "right";
  /** Vertical position the connector meets the spine. */
  spineY: number;
}

const SPINE_X = VIEW_W / 2;
export const SPINE_TOP = 70;
export const SPINE_BOTTOM = VIEW_H - 40;

/**
 * Six bays in a 3×2 arrangement around the spine — laid out front (top) to rear
 * (bottom) to read like a vehicle blueprint:
 *   POWERTRAIN (L, front) · CHASSIS (R, front)
 *   DRIVETRAIN (L, mid)   · SAFETY  (R, mid)
 *   NETWORK    (L, rear)  · COCKPIT (R, rear)
 */
const ROW_Y = [SPINE_TOP + 30, 300, 520];
const BAY_W = 360;

export const SYSTEM_BAYS: SystemBay[] = [
  { system: "POWERTRAIN", side: "left", x: 40, y: ROW_Y[0], spineY: ROW_Y[0] + 40 },
  { system: "CHASSIS", side: "right", x: VIEW_W - 40 - BAY_W, y: ROW_Y[0], spineY: ROW_Y[0] + 40 },
  { system: "DRIVETRAIN", side: "left", x: 40, y: ROW_Y[1], spineY: ROW_Y[1] + 40 },
  { system: "SAFETY", side: "right", x: VIEW_W - 40 - BAY_W, y: ROW_Y[1], spineY: ROW_Y[1] + 40 },
  { system: "NETWORK", side: "left", x: 40, y: ROW_Y[2], spineY: ROW_Y[2] + 40 },
  { system: "COCKPIT", side: "right", x: VIEW_W - 40 - BAY_W, y: ROW_Y[2], spineY: ROW_Y[2] + 40 },
];

export const SPINE = { x: SPINE_X, top: SPINE_TOP, bottom: SPINE_BOTTOM, bayW: BAY_W };

/** A part placed at an absolute coordinate within the diagram. */
export interface PlacedPart {
  part: CatalogPart;
  x: number;
  y: number;
}

export interface PlacedBay {
  bay: SystemBay;
  parts: PlacedPart[];
  /** The bay header anchor. */
  headerX: number;
  headerY: number;
  /** Connector start (where it leaves the spine). */
  spineX: number;
  spineY: number;
  /** Connector target — the inner edge of the bay nearest the spine. */
  innerEdgeX: number;
}

const NODE_W = 168;
const NODE_H = 34;
const NODE_GAP_X = 12;
const NODE_GAP_Y = 11;
const COLS = 2;

/**
 * Place every part of every system on the blueprint grid. Parts flow in a
 * two-column grid inside each bay; left-docked bays grow rightward, right-docked
 * bays mirror. Returns absolute node centers ready to render + connect.
 */
export function placeBays(systems: CatalogSystem[]): PlacedBay[] {
  const bySystem = new Map<System, CatalogSystem>();
  for (const s of systems) bySystem.set(s.system, s);

  return SYSTEM_BAYS.map((bay) => {
    const sys = bySystem.get(bay.system);
    const parts = sys?.parts ?? [];

    const placed: PlacedPart[] = parts.map((part, i) => {
      const col = i % COLS;
      const row = Math.floor(i / COLS);
      const x = bay.x + col * (NODE_W + NODE_GAP_X);
      const y = bay.y + 34 + row * (NODE_H + NODE_GAP_Y);
      return { part, x, y };
    });

    // Connector docks from the spine to the inner edge of the bay.
    const innerEdgeX = bay.side === "left" ? bay.x + BAY_W : bay.x;
    return {
      bay,
      parts: placed,
      headerX: bay.x,
      headerY: bay.y,
      spineX: SPINE_X,
      spineY: bay.spineY,
      innerEdgeX,
    };
  });
}

export const NODE = { w: NODE_W, h: NODE_H, cols: COLS };
