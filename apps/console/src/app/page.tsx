type PartStatus = "built" | "in progress" | "planned";

interface Part {
  name: string;
  purpose: string;
  status: PartStatus;
}

interface System {
  name: string;
  tagline: string;
  parts: Part[];
}

// Static this phase — mirrors docs/VISION.md. The registry will feed this live later.
const SYSTEMS: System[] = [
  {
    name: "POWERTRAIN",
    tagline: "intelligence supply",
    parts: [
      { name: "jai-gateway", purpose: "one fuel line — LiteLLM model access with budgets, tags, mock mode", status: "built" },
      { name: "jai-manifest", purpose: "the part drawings — agent specs, RunContext, audit event contract", status: "built" },
      { name: "jai-engine", purpose: "compiles manifests into runnable agents", status: "in progress" },
    ],
  },
  {
    name: "CHASSIS",
    tagline: "knowledge",
    parts: [
      { name: "jai-cortex", purpose: "retrieval memory over the procurement world", status: "planned" },
      { name: "jai-foundry", purpose: "seeded synthetic world — suppliers, POs, invoices, RFx", status: "built" },
    ],
  },
  {
    name: "DRIVETRAIN",
    tagline: "domain capability",
    parts: [
      { name: "mcp-suppliers", purpose: "supplier master MCP server", status: "planned" },
      { name: "mcp-sourcing", purpose: "sourcing / RFx MCP server", status: "planned" },
      { name: "mcp-contracts", purpose: "contracts MCP server", status: "planned" },
      { name: "mcp-orders", purpose: "purchase orders MCP server", status: "planned" },
      { name: "mcp-invoices", purpose: "invoices MCP server", status: "planned" },
    ],
  },
  {
    name: "SAFETY",
    tagline: "trust",
    parts: [
      { name: "jai-blackbox", purpose: "tamper-evident hash-chained audit trail", status: "built" },
      { name: "jai-governor", purpose: "policy enforcement before actions", status: "planned" },
      { name: "jai-dyno", purpose: "eval harness and scorecards", status: "in progress" },
      { name: "jai-brakes", purpose: "human-in-the-loop approval gates", status: "planned" },
      { name: "jai-meter", purpose: "cost ledger — who spent what, on which run", status: "built" },
    ],
  },
  {
    name: "NETWORK",
    tagline: "the fleet",
    parts: [
      { name: "jai-registry", purpose: "catalog of agents and their autonomy levels", status: "planned" },
      { name: "jai-mesh", purpose: "A2A — agents talking over the open protocol", status: "planned" },
      { name: "the agents", purpose: "the fleet itself, compiled from manifests", status: "planned" },
    ],
  },
  {
    name: "COCKPIT",
    tagline: "human interface",
    parts: [
      { name: "jai-console", purpose: "this app — platform state, costs, audit trails", status: "built" },
    ],
  },
];

const PILL_STYLES: Record<PartStatus, string> = {
  built: "border-emerald-700/60 bg-emerald-950/50 text-emerald-400",
  "in progress": "border-amber-700/60 bg-amber-950/40 text-amber-400",
  planned: "border-zinc-700/60 bg-zinc-900 text-zinc-500",
};

function StatusPill({ status }: { status: PartStatus }) {
  return (
    <span
      className={`shrink-0 rounded-full border px-2 py-0.5 font-mono text-[10px] tracking-wide ${PILL_STYLES[status]}`}
    >
      {status}
    </span>
  );
}

export default function CatalogPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-zinc-50">The vehicle</h1>
      <p className="mt-1 max-w-2xl text-sm text-zinc-400">
        JAI is built the way an automotive engineer builds a car: six systems, each part named,
        standalone, and rippable. This is the parts catalog.
      </p>

      <div className="mt-8 grid gap-5 md:grid-cols-2">
        {SYSTEMS.map((system) => (
          <section
            key={system.name}
            className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-5"
          >
            <div className="flex items-baseline gap-3">
              <h2 className="font-mono text-sm font-semibold tracking-widest text-zinc-100">
                {system.name}
              </h2>
              <span className="text-xs text-zinc-500">{system.tagline}</span>
            </div>
            <ul className="mt-4 space-y-3 border-l border-zinc-800 pl-4">
              {system.parts.map((part) => (
                <li key={part.name} className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-mono text-sm text-zinc-200">{part.name}</div>
                    <div className="mt-0.5 text-xs leading-relaxed text-zinc-500">
                      {part.purpose}
                    </div>
                  </div>
                  <StatusPill status={part.status} />
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
