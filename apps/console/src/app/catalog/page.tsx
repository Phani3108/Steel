import { CatalogView } from "./_components/CatalogView";

/**
 * /catalog — PLATFORM ARCHITECTURE.
 *
 * The parts catalog reimagined as an interactive exploded-vehicle blueprint: six
 * systems, ~22 parts, the fleet of agents with live status + scorecards. This is
 * the secondary "how it's built" view — Home (/) is now the orientation screen.
 *
 * Thin server entry; all interactivity lives in the client CatalogView.
 */
export default function CatalogPage() {
  return <CatalogView />;
}
