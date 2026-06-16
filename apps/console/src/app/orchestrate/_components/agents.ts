/**
 * Resolve an agent/service *name* (as it appears in orchestrate hops) into a
 * display label and the car-system it belongs to, using the reference fleet as
 * the canonical map. Anything unknown degrades gracefully.
 */

import { REFERENCE_NETWORK, REFERENCE_PARTS } from "@/lib/fleet";
import type { System } from "@/lib/theme";

export interface AgentMeta {
  name: string;
  label: string;
  system: System;
  role: "human" | "agent" | "service";
}

const BY_NAME: Record<string, AgentMeta> = {};

// Seed from the network topology (has friendly labels + roles)…
for (const node of REFERENCE_NETWORK.nodes) {
  BY_NAME[node.id] = {
    name: node.id,
    label: node.label,
    system: node.system,
    role: node.role,
  };
}
// …then fill any parts not present in the topology (e.g. other MCP servers).
for (const part of REFERENCE_PARTS) {
  if (!BY_NAME[part.name]) {
    BY_NAME[part.name] = {
      name: part.name,
      label: prettify(part.name),
      system: part.system,
      role: part.isAgent ? "agent" : "service",
    };
  }
}

/** Turn "mcp-sourcing-events" → "Sourcing Events", "agent-foo" → "Foo". */
function prettify(name: string): string {
  return name
    .replace(/^agent-/, "")
    .replace(/^mcp-/, "")
    .replace(/^steel-/, "")
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function agentMeta(name: string): AgentMeta {
  return (
    BY_NAME[name] ?? {
      name,
      label: prettify(name),
      // Unknown names: treat as NETWORK (the fleet) by default.
      system: "NETWORK",
      role: name === "human" ? "human" : "agent",
    }
  );
}
