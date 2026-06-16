/**
 * Live AgentManifest authoring for the Studio.
 *
 * The studio is a DESIGN-TIME concept, not a no-code runtime: the form below
 * emits a real, schema-valid `steel/v1` AgentManifest (mirrors
 * schemas/agent-manifest.schema.json) that the platform's steel-engine could
 * compile. We hand-serialize a small, predictable YAML so the preview reads
 * cleanly and stays diff-friendly — no YAML lib, no surprises.
 */

export type Pipeline =
  | "direct"
  | "rag"
  | "sourcing"
  | "orchestrate"
  | "negotiate";

export type ModelGroup = "reasoning" | "reasoning-max" | "fast";

/** The editable studio draft — the minimal surface a builder touches. */
export interface AgentDraft {
  name: string;
  description: string;
  autonomyLevel: number; // 1..5
  pipeline: Pipeline;
  modelGroup: ModelGroup;
  /** Raw comma-separated skill ids as typed. */
  skills: string;
  /** Optional spend mandate; empty string = no mandate. */
  maxSpendUsd: string;
}

export const PIPELINES: readonly Pipeline[] = [
  "direct",
  "rag",
  "sourcing",
  "orchestrate",
  "negotiate",
] as const;

export const MODEL_GROUPS: readonly ModelGroup[] = [
  "reasoning",
  "reasoning-max",
  "fast",
] as const;

/** One-line purpose per pipeline — helps a builder pick. */
export const PIPELINE_HINTS: Record<Pipeline, string> = {
  direct: "single-shot LLM call, no retrieval",
  rag: "cited retrieval over the knowledge base",
  sourcing: "draft RFx · collect bids · rank · recommend",
  orchestrate: "route an intake across specialists (A2A)",
  negotiate: "bounded, multi-round price negotiation",
};

export const MODEL_HINTS: Record<ModelGroup, string> = {
  reasoning: "balanced — the default",
  "reasoning-max": "deepest reasoning, highest cost",
  fast: "cheap & quick, for simple tasks",
};

/** Default per-task budget the studio writes per model group. */
const MODEL_BUDGET: Record<ModelGroup, number> = {
  reasoning: 0.5,
  "reasoning-max": 2,
  fast: 0.1,
};

/** A sensible starting draft — a cited supplier-risk analyst. */
export const DEFAULT_DRAFT: AgentDraft = {
  name: "agent-contract-analyst",
  description:
    "Reviews contracts for expiring terms and obligations, with cited findings.",
  autonomyLevel: 2,
  pipeline: "rag",
  modelGroup: "reasoning",
  skills: "contract.review, obligation.extract, expiry.flag",
  maxSpendUsd: "",
};

/** Turn a free-typed name into a slug the registry would accept. */
export function slugifyName(raw: string): string {
  const s = raw
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return s || "agent-unnamed";
}

/** Parse the raw comma list into clean, de-duplicated skill ids. */
export function parseSkills(raw: string): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const part of raw.split(/[,\n]/)) {
    const s = part.trim();
    if (s && !seen.has(s)) {
      seen.add(s);
      out.push(s);
    }
  }
  return out;
}

/** YAML-quote a scalar only when it needs it (keeps the preview airy). */
function yamlStr(value: string): string {
  if (value === "") return '""';
  // Quote if it could be mis-parsed (leading symbol, colon, hash, etc.).
  if (/^[\s"'#&*!|>%@`-]|[:#]\s|[:]$|^\d/.test(value) || /[:]/.test(value)) {
    return JSON.stringify(value);
  }
  return value;
}

/**
 * Serialize a draft to a `steel/v1` AgentManifest YAML string.
 * Field order mirrors how the manifests are authored on disk so the preview
 * looks like something a human checked in.
 */
export function draftToYaml(draft: AgentDraft): string {
  const name = slugifyName(draft.name);
  const skills = parseSkills(draft.skills);
  const lvl = Math.max(1, Math.min(5, Math.round(draft.autonomyLevel || 1)));
  const spend = Number(draft.maxSpendUsd);
  const hasMandate =
    draft.maxSpendUsd.trim() !== "" && Number.isFinite(spend) && spend > 0;

  const lines: string[] = [];
  lines.push("api_version: steel/v1");
  lines.push(`name: ${yamlStr(name)}`);
  lines.push(`description: ${yamlStr(draft.description.trim())}`);
  lines.push(`autonomy_level: ${lvl}`);
  lines.push(`pipeline: ${draft.pipeline}`);

  // prompt is a required, versioned file reference (ADR-001: never inline).
  lines.push("prompt:");
  lines.push(`  path: prompts/${name}.md`);
  lines.push("  version: \"1\"");

  lines.push("model:");
  lines.push(`  group: ${draft.modelGroup}`);
  lines.push(`  budget_usd_per_task: ${MODEL_BUDGET[draft.modelGroup]}`);
  lines.push("  max_tokens: 4096");

  if (skills.length > 0) {
    lines.push("skills:");
    for (const s of skills) lines.push(`  - ${yamlStr(s)}`);
  } else {
    lines.push("skills: []");
  }

  if (hasMandate) {
    lines.push("mandate:");
    lines.push(`  max_spend_usd: ${spend}`);
  }

  return lines.join("\n") + "\n";
}

/**
 * Offline echo of POST /manifest/validate — used when the control plane is
 * unreachable so the "valid ✓" affordance still tells the truth about the draft
 * the studio just built. Mirrors the server's ManifestCheck shape.
 */
export function localValidate(draft: AgentDraft): {
  valid: boolean;
  name?: string;
  autonomy_level?: number;
  pipeline?: string;
  skills?: string[];
  error?: string;
} {
  const name = slugifyName(draft.name);
  if (!draft.description.trim()) {
    return { valid: false, error: "description is required" };
  }
  return {
    valid: true,
    name,
    autonomy_level: Math.max(1, Math.min(5, Math.round(draft.autonomyLevel))),
    pipeline: draft.pipeline,
    skills: parseSkills(draft.skills),
  };
}
