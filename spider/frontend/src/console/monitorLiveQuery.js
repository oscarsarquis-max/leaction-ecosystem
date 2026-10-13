/** Classificação e política do ciclo ao vivo do Monitor — sem tokens. */

export const TERMINAL_MONITOR_EVENTS = [
  "SATELLITE_RESPONSE_RETURNED",
  "EXECUTION_SUCCEEDED",
  "EXECUTION_FAILED",
  "EXECUTION_REJECTED",
];

export function isExpectedAbort(error, signal) {
  if (signal?.aborted) return true;
  const name = error?.name || "";
  return name === "AbortError" || name === "TimeoutError";
}

export function classifyLiveFailure(error) {
  if (!error) return "transient";
  if (error.status === 401) return "expired";
  if (error.status === 403) return "denied";
  if (error.status === 404) return "missing";
  if (isExpectedAbort(error, error.signal)) return "abort";
  if (error.name === "AbortError" || error.name === "TimeoutError") return "abort";
  return "transient";
}

export function nextLiveBackoff(failCount, intervalMs = 4000, maxMs = 15000) {
  const n = Math.max(1, Number(failCount) || 1);
  return Math.min(intervalMs * 2 ** n, maxMs);
}

export function isTerminalMonitorEventList(items) {
  return (items || []).some((event) => TERMINAL_MONITOR_EVENTS.includes(event.eventType));
}

export function liveStreamLabel({ paused, auth, stale, updatedAt, formatWhen }) {
  if (paused) return "Pausado";
  if (auth === "expired") return "Sessão expirada";
  if (auth === "denied") return "Acesso recusado";
  const when = updatedAt && formatWhen ? formatWhen(updatedAt) : null;
  if (stale) return when ? `Desatualizado · última atualização ${when}` : "Desatualizado";
  return when ? `Ao vivo · atualizado ${when}` : "Ao vivo";
}

export function liveStreamTone({ paused, auth, stale }) {
  if (paused) return "paused";
  if (auth === "expired") return "expired";
  if (auth === "denied") return "denied";
  if (stale) return "stale";
  return "live";
}

export function shouldResumeOnVisible({ paused, auth, terminal }) {
  if (paused) return false;
  if (auth === "expired" || auth === "denied") return false;
  if (terminal) return false;
  return true;
}

const SELECTION_ID = /^[A-Za-z0-9._:-]{1,128}$/;

export function monitorSelectionWanted(search) {
  const params = new URLSearchParams(String(search || "").replace(/^\?/, ""));
  const execution = params.get("execution") || "";
  if (SELECTION_ID.test(execution)) return execution;
  const query = params.get("q") || "";
  if (SELECTION_ID.test(query)) return query;
  return "";
}

export function replaceMonitorSelectionSearch(search, selectedId) {
  const params = new URLSearchParams(String(search || "").replace(/^\?/, ""));
  if (!SELECTION_ID.test(selectedId || "")) {
    const qs = params.toString();
    return qs ? `?${qs}` : "";
  }
  params.set("execution", selectedId);
  const query = params.get("q");
  if (query && query !== selectedId) params.delete("q");
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export function shouldHoldManualMonitorSelection(userPicked, wanted, selectedId) {
  return Boolean(userPicked && selectedId && wanted && selectedId !== wanted);
}

export function safeMonitorReturnTo(location) {
  const loc = location || (typeof window !== "undefined" ? window.location : null);
  if (!loc) return "/";
  const path = String(loc.pathname || "/");
  if (!path.startsWith("/") || path.startsWith("//") || path.includes("://")) return "/";
  const search = String(loc.search || "");
  if (search.includes("code=") || search.includes("id_token=")) return path;
  return `${path}${search}` || "/";
}

export function attachTimeout(parentSignal, timeoutMs) {
  const controller = new AbortController();
  const onParentAbort = () => controller.abort();
  parentSignal?.addEventListener("abort", onParentAbort);
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return {
    signal: controller.signal,
    dispose() {
      clearTimeout(timer);
      parentSignal?.removeEventListener("abort", onParentAbort);
    },
  };
}
