"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";

import { Panel, SectionHeader } from "@/components/ui";
import { COLORS } from "@/lib/theme";

import { BargainingTheatre } from "./_components/BargainingTheatre";
import { NegotiationForm } from "./_components/NegotiationForm";
import { NegotiationIdle } from "./_components/NegotiationIdle";
import { NegotiationVerdict } from "./_components/NegotiationVerdict";
import { TranscriptLog } from "./_components/TranscriptLog";
import {
  SEED_SELLERS,
  deriveBand,
  type SellerPersona,
} from "./_components/demo";
import { useNegotiation } from "./_components/useNegotiation";

/**
 * /negotiate — THE BARGAINING THEATRE (P4 hero).
 *
 * Pick a seller persona and a list price, then open a negotiation → POST
 * /negotiate → the transcript rolls in round by round as a bespoke SVG: buyer
 * offers step up, seller counters step down, converging to a green deal under
 * the mandate cap — or, when the list price is high enough that the only
 * attainable prices sit above the cap, the negotiator refuses to cross the rose
 * cap line and WALKS. The cap holds; constraint violations stay at zero.
 *
 * Offline, a scripted reference negotiation plays over staged delays, clearly
 * labeled, so the theatre is always a compelling demo.
 */
export default function NegotiatePage() {
  const { state, busy, negotiate, reset } = useNegotiation();

  const [sellerIdx, setSellerIdx] = useState(0);
  const [listPrice, setListPrice] = useState(120_000);

  // Personas: seed three until a live response names its sellers, then adopt
  // those (keeping the seed blurbs/profiles by position).
  const sellers: SellerPersona[] = useMemo(() => {
    const live = state?.result.sellers;
    if (live && live.length) {
      return live.map((s, i) => ({
        ...(SEED_SELLERS[i] ?? SEED_SELLERS[0]),
        skill_id: s.skill_id,
        name: s.name,
      }));
    }
    return SEED_SELLERS;
  }, [state?.result.sellers]);

  // Predictive safety hint: would *this* price breach the cap we last observed?
  // Before any run we estimate the cap from the offline geometry so the slider
  // turns rose as you approach the danger zone.
  const willWalk = useMemo(() => {
    const lastCap = state?.result.mandate_cap ?? null;
    const band = deriveBand(listPrice, lastCap);
    const persona = sellers[sellerIdx] ?? SEED_SELLERS[0];
    // Mirror the builder's floor exactly (it rounds) so the slider's rose
    // warning flips on precisely the stop where the negotiation starts to walk.
    const floor = Math.round((persona.floorOfList ?? 0.9) * listPrice);
    return floor > band.cap;
  }, [listPrice, sellerIdx, sellers, state?.result.mandate_cap]);

  const referenceMode = state?.source === "reference";

  return (
    <div className="space-y-6">
      <SectionHeader
        kicker="cockpit · agent negotiator"
        title="Negotiate"
        subtitle="Set a seller across the table and a list price, then watch the JAI-Negotiator bargain it down — round by round, offer against counter — and refuse, every time, to cross its mandate cap."
        action={
          referenceMode ? (
            <span
              className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px]"
              style={{
                borderColor: "color-mix(in srgb, var(--autonomy) 35%, transparent)",
                color: COLORS.autonomy,
                background: "color-mix(in srgb, var(--autonomy) 10%, transparent)",
              }}
              title="POST /negotiate is unreachable — replaying a scripted reference negotiation."
            >
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{ background: COLORS.autonomy }}
              />
              live negotiator offline — reference negotiation
            </span>
          ) : null
        }
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)] lg:items-start">
        {/* the table — sticky on wide screens so controls stay in reach */}
        <div className="lg:sticky lg:top-6">
          <NegotiationForm
            sellers={sellers}
            sellerIdx={sellerIdx}
            onSellerIdx={setSellerIdx}
            listPrice={listPrice}
            onListPrice={setListPrice}
            willWalk={willWalk}
            onNegotiate={() => negotiate(listPrice, sellerIdx)}
            busy={busy}
            hasRun={state !== null}
            onReset={reset}
          />
        </div>

        {/* the theatre */}
        <div className="min-w-0 space-y-6">
          <Panel
            accent={state?.result.status === "walked" ? "SAFETY" : "COCKPIT"}
            grid
            flush
            title="bargaining theatre"
            action={
              <span className="metric text-[10px] tracking-wider text-ink-faint">
                {state
                  ? `vs ${state.persona.name.toLowerCase()}`
                  : "zopa · mandate-bounded"}
              </span>
            }
          >
            <div className="p-3">
              <AnimatePresence mode="wait">
                {state ? (
                  <motion.div
                    key="theatre"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <BargainingTheatre state={state} />
                  </motion.div>
                ) : (
                  <motion.div
                    key="idle"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <NegotiationIdle />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </Panel>

          {/* transcript + verdict appear once a negotiation is on the table */}
          <AnimatePresence>
            {state && (
              <motion.div
                key="detail"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,300px)] lg:items-start"
              >
                <div className="order-2 lg:order-1">
                  <AnimatePresence>
                    {state.verdictReady && <NegotiationVerdict state={state} />}
                  </AnimatePresence>
                  {!state.verdictReady && (
                    <Panel title="negotiating" accent="accent">
                      <div className="flex items-center gap-3 py-1">
                        <span className="metric text-sm text-ink-muted">
                          rounds {state.revealed} / {state.result.transcript.length}
                        </span>
                        <span className="metric ml-auto text-[11px] text-ink-faint">
                          holding the mandate cap…
                        </span>
                      </div>
                    </Panel>
                  )}
                </div>
                <Panel
                  title="transcript"
                  className="order-1 lg:order-2"
                  action={
                    <span className="metric text-[10px] text-ink-faint">
                      {state.revealed}/{state.result.transcript.length}
                    </span>
                  }
                >
                  <TranscriptLog state={state} />
                </Panel>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
