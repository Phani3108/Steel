"use client";

import { useEffect, useState } from "react";

export interface PollState<T> {
  data: T | null;
  /** True when the latest poll failed (control plane unreachable). */
  offline: boolean;
  /** True once at least one poll has completed (ok or not). */
  loaded: boolean;
}

const INITIAL: PollState<never> = { data: null, offline: false, loaded: false };

/**
 * Poll an async fetcher on an interval (default 2s), keeping the last good
 * data when a poll fails. `fn` must be referentially stable (a module-level
 * function or `useCallback`) — a new identity restarts the polling loop.
 * Pass a `key` to reset state when the target changes (e.g. selected run id).
 */
export function usePoll<T>(
  fn: () => Promise<T>,
  intervalMs = 2000,
  key = "",
): PollState<T> {
  const [state, setState] = useState<PollState<T>>(INITIAL);
  const [prevKey, setPrevKey] = useState(key);

  // Reset stale data the moment the target changes (render-time state reset).
  if (prevKey !== key) {
    setPrevKey(key);
    setState(INITIAL);
  }

  useEffect(() => {
    let alive = true;

    const tick = async () => {
      try {
        const data = await fn();
        if (alive) setState({ data, offline: false, loaded: true });
      } catch {
        if (alive) setState((s) => ({ ...s, offline: true, loaded: true }));
      }
    };

    void tick();
    const id = setInterval(() => void tick(), intervalMs);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [fn, intervalMs]);

  return state;
}
