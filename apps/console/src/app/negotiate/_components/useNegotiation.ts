"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { postNegotiate, type NegotiationResult } from "@/lib/api";
import {
  buildReferenceNegotiation,
  resolvePersona,
  type NegotiationState,
} from "./demo";

/** Timing of the staged reveal (ms). Brisk enough to read as a live exchange. */
const OPEN_DELAY = 720; // table is set / request in flight before round 1
const ROUND_STEP_MS = 920; // cadence between successive rounds revealing
const VERDICT_DELAY = 760; // beat after the last round before the verdict lands

interface UseNegotiation {
  state: NegotiationState | null;
  busy: boolean;
  /** Engage a seller (index into the persona list) at a list price. */
  negotiate: (listPrice: number, sellerIdx: number) => void;
  reset: () => void;
}

/**
 * Drives a negotiation: POSTs {list_price, seller} (falling back to a scripted
 * reference negotiation when /negotiate is offline), then *rolls* the resulting
 * transcript onto the theatre — each round revealing in sequence so buyer offers
 * step up and seller counters step down in real time. Timers clean up on
 * reset / unmount.
 */
export function useNegotiation(): UseNegotiation {
  const [state, setState] = useState<NegotiationState | null>(null);
  const [busy, setBusy] = useState(false);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }, []);

  const after = useCallback((ms: number, fn: () => void) => {
    timers.current.push(setTimeout(fn, ms));
  }, []);

  const reset = useCallback(() => {
    clearTimers();
    setState(null);
    setBusy(false);
  }, [clearTimers]);

  /** Stage a resolved result onto the rolling theatre. */
  const stage = useCallback(
    (
      result: NegotiationResult,
      source: "live" | "reference",
      sellerIdx: number,
    ) => {
      const persona = resolvePersona(result, sellerIdx);
      const total = result.transcript.length;

      // Seed: table set, mandate framed, no rounds revealed yet.
      setState({
        source,
        phase: "opening",
        result,
        persona,
        revealed: 0,
        verdictReady: false,
      });

      after(OPEN_DELAY, () => {
        setState((s) => (s ? { ...s, phase: "bargaining" } : s));

        // Roll each round in sequence.
        result.transcript.forEach((_, i) => {
          after((i + 1) * ROUND_STEP_MS, () => {
            setState((s) => (s ? { ...s, revealed: i + 1 } : s));
          });
        });

        // After the last round, settle into the verdict.
        const settleAt = total * ROUND_STEP_MS + VERDICT_DELAY;
        after(settleAt, () => {
          setState((s) =>
            s ? { ...s, phase: "settled", verdictReady: true } : s,
          );
          setBusy(false);
        });
      });
    },
    [after],
  );

  const negotiate = useCallback(
    (listPrice: number, sellerIdx: number) => {
      clearTimers();
      setBusy(true);
      setState(null);

      postNegotiate({ list_price: listPrice, seller: sellerIdx })
        .then((result) => {
          // Guard against a degenerate live response — fall back so the theatre
          // is never empty.
          if (!result.transcript || result.transcript.length === 0) {
            stage(
              buildReferenceNegotiation(listPrice, sellerIdx),
              "reference",
              sellerIdx,
            );
          } else {
            stage(result, "live", sellerIdx);
          }
        })
        .catch(() => {
          stage(
            buildReferenceNegotiation(listPrice, sellerIdx),
            "reference",
            sellerIdx,
          );
        });
    },
    [clearTimers, stage],
  );

  useEffect(() => clearTimers, [clearTimers]);

  return { state, busy, negotiate, reset };
}
