"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";

import { SectionHeader, Term } from "@/components/ui";
import { COLORS } from "@/lib/theme";
import { fetchMeta, postChat, type Meta } from "@/lib/api";

import { Composer } from "./_components/Composer";
import { ExamplePrompts } from "./_components/ExamplePrompts";
import { MessageBubble, type Turn } from "./_components/MessageBubble";
import { PersonaBar } from "./_components/PersonaBar";
import { roleLabel } from "./_components/personas";

const DEFAULT_ROLE = "requester";
const DEFAULT_TENANT = "TEN-0001";

/** The agent's "thinking" placeholder while a /chat round-trip is in flight. */
function ThinkingBubble() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="flex justify-start pr-10"
    >
      <div className="panel-2 flex items-center gap-2.5 px-3.5 py-3">
        <span className="flex items-center gap-1" aria-hidden>
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              className="inline-block h-1.5 w-1.5 rounded-full"
              style={{ background: COLORS.accent }}
              animate={{ opacity: [0.25, 1, 0.25] }}
              transition={{
                duration: 1.2,
                repeat: Infinity,
                delay: i * 0.18,
                ease: "easeInOut",
              }}
            />
          ))}
        </span>
        <span className="metric text-[11px] tracking-wide text-ink-faint">
          retrieving · reasoning · citing
        </span>
      </div>
    </motion.div>
  );
}

export default function ChatPage() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [role, setRole] = useState(DEFAULT_ROLE);
  const [tenant, setTenant] = useState(DEFAULT_TENANT);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [offline, setOffline] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchMeta()
      .then((m) => {
        setMeta(m);
        setOffline(false);
        if (m.roles.length > 0 && !m.roles.includes(role)) setRole(m.roles[0]);
        if (m.tenants.length > 0) setTenant(m.tenants[0].id);
      })
      .catch(() => setOffline(true));
    // run once on mount; role/tenant defaults are seeded above
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [turns, busy]);

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    setDraft("");
    setTurns((t) => [...t, { who: "user", text: message }]);
    setBusy(true);
    try {
      const reply = await postChat(message, role, tenant);
      setOffline(false);
      setTurns((t) => [...t, { who: "agent", text: reply.text, reply }]);
    } catch {
      setOffline(true);
      setTurns((t) => [
        ...t,
        {
          who: "agent",
          text: "Control plane unreachable — is the JAI API running on :8400?",
          transportError: true,
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  const empty = turns.length === 0;

  return (
    <div className="flex flex-col gap-5">
      <SectionHeader
        kicker="cockpit · ask"
        title="Ask the fleet"
        subtitle="A cited supplier-intelligence agent over the knowledge base. Every answer is permission-scoped to the persona below and traced to the audit log."
        action={
          <span className="metric hidden text-[10px] tracking-wider text-ink-faint sm:inline">
            pipeline <span className="text-accent">RAG</span> · autonomy{" "}
            <span className="text-autonomy">L2 · advise</span>
          </span>
        }
      />

      <PersonaBar
        meta={meta}
        role={role}
        tenant={tenant}
        offline={offline}
        onRole={setRole}
        onTenant={setTenant}
      />

      {/* permission-scope note — answers obey the persona's mandate, below the model */}
      <p className="flex flex-wrap items-center gap-1.5 px-1 text-[11.5px] leading-relaxed text-ink-faint">
        <ShieldGlyph />
        Answers are{" "}
        <span className="text-ink-muted">permission-scoped</span> to this
        persona&rsquo;s <Term k="mandate" /> — the{" "}
        <Term k="autonomy">governor</Term> enforces row- and field-level access
        below the model, and every answer is traced to the audit log.
      </p>

      {/* conversation surface */}
      <div className="panel relative flex min-h-[clamp(22rem,52vh,40rem)] flex-col overflow-hidden">
        <div
          ref={scrollRef}
          className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-5"
        >
          {empty ? (
            <div className="flex h-full flex-col justify-center gap-6 py-4">
              <div className="text-center">
                <p className="text-sm text-ink-muted">
                  Ask about suppliers, items, contracts, policies, or news.
                </p>
                <p className="mt-1 text-[12px] text-ink-faint">
                  Answering as{" "}
                  <span className="metric text-autonomy">
                    {roleLabel(role)}
                  </span>
                  . Pick a starter or type below.
                </p>
              </div>
              <ExamplePrompts role={role} onPick={(t) => void send(t)} />
            </div>
          ) : (
            <>
              {turns.map((turn, i) => (
                <MessageBubble key={i} turn={turn} />
              ))}
              {busy && <ThinkingBubble />}
            </>
          )}
        </div>

        {!empty && (
          <div className="border-t border-line/70 bg-base-2/30 px-4 py-2.5">
            <ExamplePromptsRow role={role} onPick={(t) => void send(t)} />
          </div>
        )}
      </div>

      <Composer
        value={draft}
        busy={busy}
        onChange={setDraft}
        onSend={() => void send(draft)}
      />
    </div>
  );
}

/**
 * A condensed single-row variant of the starters shown beneath an active
 * conversation, so the persona-aware prompts stay reachable without crowding.
 */
function ExamplePromptsRow({
  role,
  onPick,
}: {
  role: string;
  onPick: (text: string) => void;
}) {
  return (
    <div className="flex items-center gap-2 overflow-x-auto">
      <span className="label-cap shrink-0">more as {roleLabel(role)}</span>
      <ExamplePrompts role={role} onPick={onPick} compact />
    </div>
  );
}

/**
 * A small shield — the visual anchor for the permission-scope note, signalling
 * that the governor enforces access below the model. Tinted with the autonomy hue
 * to tie it to the governor / mandate vocabulary used in the line.
 */
function ShieldGlyph() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 16 16"
      className="h-3.5 w-3.5 shrink-0"
      fill="none"
      style={{ color: COLORS.autonomy }}
    >
      <path
        d="M8 1.5 13 3.4v4.1c0 3.2-2.1 5.6-5 6.9-2.9-1.3-5-3.7-5-6.9V3.4L8 1.5Z"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      <path
        d="M5.8 8 7.3 9.5 10.3 6"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
