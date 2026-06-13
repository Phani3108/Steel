/**
 * Negotiate — shared types, seller personas, and the offline scripted demo.
 *
 * When POST /negotiate is reachable we replay the *real* transcript returned by
 * the control plane, staged round-by-round so the bargaining reads as live.
 * When it's offline we synthesize a believable reference negotiation (clearly
 * labeled in the UI) whose shape exactly matches a real /negotiate response, so
 * the theatre code is identical for live and reference runs.
 *
 * Nothing here imports React — pure data/logic, safe anywhere in the tree.
 *
 * The emotional core is SAFETY: when the list price is high enough that even the
 * best attainable deal would breach the agent's mandate cap, the negotiator
 * refuses to cross the cap line and WALKS — constraint violations stay at zero.
 */

import type { NegotiationResult, NegotiationSeller } from "@/lib/api";

/** Price-slider bounds (USD). */
export const PRICE_MIN = 40_000;
export const PRICE_MAX = 250_000;

/**
 * Seed personas used before the first live response names its sellers. Index
 * order is the contract — POST /negotiate {seller} is an index into this list.
 * Each persona also carries a *script profile* the offline demo uses to shape a
 * distinct negotiation character.
 */
export interface SellerPersona extends NegotiationSeller {
  /** One-line characterization shown under the persona name. */
  blurb: string;
  /** How hard they hold (0..1) — higher = smaller concessions. */
  toughness: number;
  /** Where their best attainable price sits, as a fraction of list. */
  floorOfList: number;
}

export const SEED_SELLERS: SellerPersona[] = [
  {
    skill_id: "seller.stonewaller",
    name: "The Stonewaller",
    blurb: "Anchors at list, concedes in slivers. Tests your walk-away nerve.",
    toughness: 0.82,
    floorOfList: 0.93,
  },
  {
    skill_id: "seller.margin_hawk",
    name: "The Margin Hawk",
    blurb: "Guards gross margin to the last point. Trades terms for price.",
    toughness: 0.62,
    floorOfList: 0.88,
  },
  {
    skill_id: "seller.volume_hunter",
    name: "The Volume Hunter",
    blurb: "Wants the logo and the volume. Moves fast if the deal closes today.",
    toughness: 0.4,
    floorOfList: 0.83,
  },
];

/** Per-round reveal phase, driven by the staged scheduler. */
export type RoundPhase = "buyer" | "seller" | "resolved";

/** Where the whole negotiation sits in its lifecycle. */
export type TheatrePhase =
  | "idle"
  | "opening" // request in flight / mandate framed, table set
  | "bargaining" // rounds streaming in
  | "settled"; // deal / walk resolved

/** The live, staged view the theatre renders. */
export interface NegotiationState {
  source: "live" | "reference";
  phase: TheatrePhase;
  result: NegotiationResult;
  /** Persona engaged (resolved name + blurb), for the masthead. */
  persona: SellerPersona;
  /** Count of transcript rounds revealed so far; grows as it "streams". */
  revealed: number;
  /** True once the verdict (deal/walk) is shown. */
  verdictReady: boolean;
}

// ----------------------------------------------------- mandate geometry ----

/**
 * The mandate band the agent operates within, expressed in absolute USD against
 * a given list price. These mirror the negotiate pipeline's policy posture:
 *  - target ≈ where a good deal lands (~86% of list)
 *  - walkaway ≈ the soft ceiling beyond which it's a bad deal (~95% of list)
 *  - cap = the HARD mandate ceiling the agent may never cross.
 *
 * The cap is the dramatic line. When `mandate_cap` comes back from the API we
 * honor it exactly; offline we derive a cap that sits *below* a high list price
 * so the walk-away story is reachable.
 */
export interface MandateBand {
  list: number;
  target: number;
  walkaway: number;
  cap: number;
}

/**
 * The agent's HARD mandate ceiling, in absolute USD. This is the dramatic line.
 *
 * It is a *fixed dollar amount*, NOT a fraction of list — that's the whole
 * point. Below the cap, deals are reachable and the agent closes. Push the list
 * price above the cap and the only attainable prices sit out of reach, so the
 * negotiator refuses to cross the line and walks. The slider is the control that
 * drives the outcome. Sits at $135k — between the $40k–$250k slider range, so
 * both stories are one drag apart. Live responses override via `mandate_cap`.
 */
export const OFFLINE_MANDATE_CAP = 135_000;

export function deriveBand(
  list: number,
  capOverride: number | null,
): MandateBand {
  const target = Math.round(list * 0.86);
  const walkaway = Math.round(list * 0.95);
  const cap = capOverride ?? OFFLINE_MANDATE_CAP;
  return { list, target, walkaway, cap };
}

// --------------------------------------------------------- reference run ----

/**
 * Build a believable scripted negotiation against the chosen persona. Shape is
 * identical to a real POST /negotiate response so the theatre is agnostic.
 *
 * Two outcomes emerge from the geometry, exactly like the live pipeline:
 *  - DEAL: the seller's floor sits at or below the mandate cap → buyer steps up,
 *    seller steps down, they converge under the cap and close.
 *  - WALK: the seller's floor sits *above* the cap → the negotiator refuses to
 *    cross the rose cap line and walks. Breach is averted; violations = 0.
 */
export function buildReferenceNegotiation(
  list: number,
  sellerIdx: number,
): NegotiationResult {
  const persona = SEED_SELLERS[sellerIdx] ?? SEED_SELLERS[0];
  const band = deriveBand(list, null);
  const cap = band.cap;

  // The lowest price this seller will ultimately accept.
  const sellerFloor = Math.round(list * persona.floorOfList);
  // The agent can only close at-or-below the cap.
  const canDeal = sellerFloor <= cap;

  // Buyer opens low (anchored near the target), seller counters high (near list).
  let buyerOffer = Math.round(band.target * 0.96);
  let sellerCounter = Math.round(list * 0.995);

  const transcript: NegotiationResult["transcript"] = [];
  const maxRounds = 5;
  let round = 0;
  let dealPrice: number | null = null;

  // How fast the seller closes the gap to its floor each round. Tougher sellers
  // concede less, so they take more rounds — but a *closable* deal always lands
  // within the budget because the seller commits to its floor on the last round.
  const concede = 0.55 + (1 - persona.toughness) * 0.4; // 0.55 (tough) … 0.79

  for (round = 1; round <= maxRounds; round++) {
    const lastRound = round === maxRounds;

    // Seller concedes toward their floor; on a closable deal's final round they
    // commit fully to the floor so convergence is guaranteed within the budget.
    sellerCounter =
      canDeal && lastRound
        ? sellerFloor
        : Math.round(
            Math.max(sellerFloor, sellerCounter - (sellerCounter - sellerFloor) * concede),
          );

    // Buyer steps up toward the seller's counter, but is HARD-CLAMPED at its
    // mandate ceiling — it will never table an offer above the cap. That clamp
    // is the safety; it is why the agent can refuse to breach.
    const buyerWants = Math.round(buyerOffer + (sellerCounter - buyerOffer) * 0.65);
    buyerOffer = Math.min(buyerWants, cap);

    if (canDeal) {
      // The buyer's standing offer meets or beats the seller's counter → close.
      // (sellerCounter ≤ sellerFloor ≤ cap, so the deal price is always ≤ cap.)
      if (buyerOffer >= sellerCounter || lastRound) {
        dealPrice = Math.min(sellerCounter, cap);
        transcript.push({
          round,
          offer: Math.max(buyerOffer, dealPrice),
          counter: dealPrice,
          action: "seller_accepts",
        });
        break;
      }
      transcript.push({
        round,
        offer: buyerOffer,
        counter: sellerCounter,
        action: "counter_up",
      });
    } else {
      // Not closable: the seller's floor sits ABOVE the cap. The buyer pins at
      // the cap and the seller floats above it — the agent holds the line. After
      // a couple of rounds it's clear the seller won't come under: it walks.
      // Never breaches — the buyer never tables above its mandate ceiling.
      transcript.push({
        round,
        offer: buyerOffer,
        counter: sellerCounter,
        action: "counter_up",
      });
      if (round >= 2) break;
    }
  }

  const closed = dealPrice != null;
  const finalPrice = dealPrice;
  const savingsPct = closed
    ? Math.round(((list - (finalPrice as number)) / list) * 1000) / 10
    : 0;

  return {
    status: closed ? "deal" : "walked",
    seller: persona.name,
    list_price: list,
    final_price: finalPrice,
    savings_pct: savingsPct,
    payment_terms_days: closed ? (persona.toughness > 0.6 ? 45 : 60) : null,
    rounds: transcript.length,
    mandate_cap: cap,
    breached: false, // the agent never crosses the cap — by construction
    closed,
    transcript,
    run_id: `run_${randId()}`,
    sellers: SEED_SELLERS.map(({ skill_id, name }) => ({ skill_id, name })),
  };
}

/**
 * Resolve the persona to display from a result + the index the operator picked.
 * Live responses may rename sellers; we match by name, then fall back to seed.
 */
export function resolvePersona(
  result: NegotiationResult,
  sellerIdx: number,
): SellerPersona {
  const byName = SEED_SELLERS.find((p) => p.name === result.seller);
  if (byName) return byName;
  const seed = SEED_SELLERS[sellerIdx] ?? SEED_SELLERS[0];
  // Adopt the live seller's name/blurb while keeping a sane script profile.
  return {
    ...seed,
    skill_id: result.sellers?.[sellerIdx]?.skill_id ?? seed.skill_id,
    name: result.seller || seed.name,
  };
}

function randId(): string {
  return Math.random().toString(36).slice(2, 10);
}

/** Compact USD (no cents) for axis ticks and chips. */
export function fmtK(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  if (Math.abs(n) >= 1_000_000)
    return `$${(n / 1_000_000).toFixed(n % 1_000_000 ? 1 : 0)}M`;
  if (Math.abs(n) >= 1_000) return `$${Math.round(n / 1_000)}k`;
  return `$${Math.round(n)}`;
}

/** Full USD for headline figures. */
export function fmtUsdFull(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}
