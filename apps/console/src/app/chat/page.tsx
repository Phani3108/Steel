"use client";

import { useEffect, useRef, useState } from "react";
import { OfflineBanner } from "../../components/OfflineBanner";
import {
  ChatReply,
  fetchMeta,
  fmtUsd,
  Meta,
  postChat,
} from "../../lib/api";

interface Turn {
  who: "user" | "agent";
  text: string;
  reply?: ChatReply;
}

export default function ChatPage() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [role, setRole] = useState("requester");
  const [tenant, setTenant] = useState("TEN-0001");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [offline, setOffline] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchMeta()
      .then((m) => {
        setMeta(m);
        setOffline(false);
        if (m.tenants.length > 0) setTenant(m.tenants[0].id);
      })
      .catch(() => setOffline(true));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  async function send() {
    const message = draft.trim();
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
        { who: "agent", text: "Control plane unreachable — is `make api` running?" },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex h-[calc(100vh-7rem)] max-w-3xl flex-col gap-3">
      <OfflineBanner show={offline} />

      <div className="flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm">
        <span className="text-zinc-500">Acting as</span>
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-zinc-200"
        >
          {(meta?.roles ?? ["requester", "category_manager", "cpo"]).map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <span className="text-zinc-500">in</span>
        <select
          value={tenant}
          onChange={(e) => setTenant(e.target.value)}
          className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-zinc-200"
        >
          {(meta?.tenants ?? [{ id: "TEN-0001", name: "Borealis North America" }]).map(
            (t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ),
          )}
        </select>
        <span className="ml-auto text-xs text-zinc-600">
          permissions are enforced below the model — switch roles to see refusals
        </span>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto rounded-lg border border-zinc-800 bg-zinc-950 p-4">
        {turns.length === 0 && (
          <p className="text-sm text-zinc-600">
            Ask about suppliers, items, contracts, policies, or news — e.g.{" "}
            <em>&ldquo;Tell me about supplier Rampart Engineering Inc.&rdquo;</em>
          </p>
        )}
        {turns.map((turn, i) =>
          turn.who === "user" ? (
            <div key={i} className="ml-12 rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-100">
              {turn.text}
            </div>
          ) : (
            <div
              key={i}
              className={`mr-12 rounded-lg border px-3 py-2 text-sm ${
                turn.reply?.refused
                  ? "border-amber-700/60 bg-amber-950/40 text-amber-200"
                  : "border-zinc-800 bg-zinc-900 text-zinc-200"
              }`}
            >
              <pre className="whitespace-pre-wrap font-sans">{turn.text}</pre>
              {turn.reply && turn.reply.citations.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {turn.reply.citations.slice(0, 8).map((c, j) => (
                    <span
                      key={j}
                      className="rounded-full border border-zinc-700 bg-zinc-950 px-2 py-0.5 text-[11px] text-zinc-400"
                      title={c.snippet}
                    >
                      {c.source_type}:{c.source_id}
                    </span>
                  ))}
                </div>
              )}
              {turn.reply && (
                <div className="mt-1 text-[11px] text-zinc-600">
                  {fmtUsd(turn.reply.cost_usd)} · {turn.reply.run_id}
                </div>
              )}
            </div>
          ),
        )}
        {busy && <div className="mr-12 text-sm text-zinc-500">thinking…</div>}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
        className="flex gap-2"
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask the supplier-intelligence agent…"
          className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-zinc-500"
        />
        <button
          type="submit"
          disabled={busy || draft.trim() === ""}
          className="rounded-lg bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-900 disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </main>
  );
}
