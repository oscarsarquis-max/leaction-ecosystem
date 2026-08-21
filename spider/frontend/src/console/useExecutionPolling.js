import { useEffect, useRef, useState } from "react";
import { getExecutionDetail, isTerminalState } from "./api";

/**
 * Polling real com AbortController — para em terminal, unmount ou erro repetido.
 */
export function useExecutionPolling(executionId, { enabled, minIntervalMs = 1000, paused } = {}) {
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [status, setStatus] = useState("idle");
  const failCount = useRef(0);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!executionId || !enabled || paused) {
      return undefined;
    }

    let cancelled = false;
    let controller = null;

    async function tick(delay) {
      if (cancelled) return;
      timerRef.current = setTimeout(run, delay);
    }

    async function run() {
      if (cancelled) return;
      controller?.abort();
      controller = new AbortController();
      setStatus("loading");
      try {
        const data = await getExecutionDetail(executionId, { signal: controller.signal });
        if (cancelled) return;
        setDetail(data);
        setError(null);
        setUpdatedAt(new Date());
        setStatus("ok");
        failCount.current = 0;
        const state = data?.summary?.state;
        if (isTerminalState(state)) {
          setStatus("terminal");
          return;
        }
        await tick(minIntervalMs);
      } catch (e) {
        if (cancelled || e.name === "AbortError") return;
        failCount.current += 1;
        setError(e);
        setStatus("error");
        if (failCount.current >= 5) {
          return;
        }
        const backoff = Math.min(minIntervalMs * 2 ** failCount.current, 15000);
        await tick(backoff);
      }
    }

    run();

    return () => {
      cancelled = true;
      controller?.abort();
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [executionId, enabled, paused, minIntervalMs]);

  return { detail, error, updatedAt, status, setDetail };
}
