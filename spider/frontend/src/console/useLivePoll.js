import { useEffect, useRef, useState } from "react";
import {
  attachTimeout,
  classifyLiveFailure,
  isExpectedAbort,
  nextLiveBackoff,
  shouldResumeOnVisible,
} from "./monitorLiveQuery";

/**
 * Ciclo ao vivo com um voo, backoff limitado, retomada por visibilidade
 * e sem tratar Abort esperado como falha de negócio.
 */
export function useLivePoll({
  enabled = true,
  paused = false,
  intervalMs = 4000,
  maxBackoffMs = 15000,
  timeoutMs = 12000,
  resetKey = "",
  forceKey = 0,
  run,
  isTerminal = () => false,
} = {}) {
  const [value, setValue] = useState(null);
  const [error, setError] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [status, setStatus] = useState("idle");
  const [stale, setStale] = useState(false);
  const [auth, setAuth] = useState(null);

  const runRef = useRef(run);
  const terminalCheckRef = useRef(isTerminal);
  const enabledRef = useRef(enabled);
  const pausedRef = useRef(paused);
  const failCount = useRef(0);
  const inFlight = useRef(false);
  const generation = useRef(0);
  const timerRef = useRef(null);
  const controllerRef = useRef(null);
  const cancelledRef = useRef(false);
  const authStop = useRef(null);
  const terminalRef = useRef(false);
  const forceOnce = useRef(false);

  runRef.current = run;
  terminalCheckRef.current = isTerminal;
  enabledRef.current = enabled;
  pausedRef.current = paused;

  useEffect(() => {
    setValue(null);
    setError(null);
    setUpdatedAt(null);
    setStale(false);
    setAuth(null);
    setStatus("idle");
    failCount.current = 0;
    authStop.current = null;
    terminalRef.current = false;
  }, [resetKey]);

  useEffect(() => {
    if (forceKey) forceOnce.current = true;
  }, [forceKey]);

  useEffect(() => {
    cancelledRef.current = false;

    function clearTimer() {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    }

    function schedule(delay) {
      clearTimer();
      if (cancelledRef.current || pausedRef.current || !enabledRef.current) return;
      if (authStop.current) return;
      timerRef.current = setTimeout(() => {
        timerRef.current = null;
        execute();
      }, delay);
    }

    async function execute() {
      if (cancelledRef.current || !enabledRef.current || pausedRef.current) return;
      if (authStop.current) return;
      if (inFlight.current) return;
      if (terminalRef.current && !forceOnce.current) return;
      forceOnce.current = false;
      inFlight.current = true;
      const gen = ++generation.current;
      const parent = new AbortController();
      controllerRef.current = parent;
      const timed = attachTimeout(parent.signal, timeoutMs);
      setStatus((current) => (current === "ok" || current === "terminal" ? current : "loading"));
      try {
        const next = await runRef.current(timed.signal);
        timed.dispose();
        if (cancelledRef.current || gen !== generation.current) return;
        setValue(next);
        setError(null);
        setUpdatedAt(new Date());
        setStale(false);
        setAuth(null);
        failCount.current = 0;
        if (terminalCheckRef.current(next)) {
          terminalRef.current = true;
          setStatus("terminal");
          return;
        }
        terminalRef.current = false;
        setStatus("ok");
        schedule(intervalMs);
      } catch (caught) {
        timed.dispose();
        if (cancelledRef.current || gen !== generation.current) return;
        if (isExpectedAbort(caught, parent.signal) || isExpectedAbort(caught, timed.signal)) {
          return;
        }
        const kind = classifyLiveFailure(caught);
        if (kind === "abort") return;
        if (kind === "expired") {
          setError(caught);
          setStale(true);
          setAuth("expired");
          setStatus("expired");
          authStop.current = "expired";
          return;
        }
        if (kind === "denied") {
          setValue(null);
          setError(caught);
          setAuth("denied");
          setStale(false);
          setStatus("denied");
          authStop.current = "denied";
          return;
        }
        failCount.current += 1;
        setError(caught);
        setStale(true);
        setStatus("error");
        schedule(nextLiveBackoff(failCount.current, intervalMs, maxBackoffMs));
      } finally {
        if (gen === generation.current) inFlight.current = false;
      }
    }

    function resumeIfAllowed() {
      if (
        !shouldResumeOnVisible({
          paused: pausedRef.current,
          auth: authStop.current,
          terminal: terminalRef.current,
        })
      ) {
        return;
      }
      if (!enabledRef.current || cancelledRef.current) return;
      clearTimer();
      execute();
    }

    function onVisibility() {
      if (typeof document !== "undefined" && document.visibilityState === "visible") {
        resumeIfAllowed();
      }
    }

    if (enabled && !paused) {
      execute();
    } else {
      clearTimer();
      if (!enabled) setStatus("idle");
    }

    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", onVisibility);
    }
    if (typeof window !== "undefined") {
      window.addEventListener("pageshow", onVisibility);
    }

    return () => {
      cancelledRef.current = true;
      inFlight.current = false;
      controllerRef.current?.abort();
      clearTimer();
      if (typeof document !== "undefined") {
        document.removeEventListener("visibilitychange", onVisibility);
      }
      if (typeof window !== "undefined") {
        window.removeEventListener("pageshow", onVisibility);
      }
    };
  }, [enabled, paused, intervalMs, maxBackoffMs, timeoutMs, resetKey, forceKey]);

  return { value, error, updatedAt, status, stale, auth };
}
