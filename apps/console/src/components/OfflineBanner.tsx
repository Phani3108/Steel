import { API_BASE } from "../lib/api";

/** Shown when the control-plane API is unreachable; pages keep rendering beneath it. */
export function OfflineBanner({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <div
      role="status"
      className="mb-5 rounded-md border border-amber-700/60 bg-amber-950/40 px-4 py-2.5 text-sm text-amber-300"
    >
      <span className="font-semibold">control plane offline</span>
      <span className="text-amber-400/80">
        {" "}
        — cannot reach the JAI API at {API_BASE}; showing last known state.
      </span>
    </div>
  );
}
