import { isTerminalState } from "./api";
import { getExecutionDetail } from "./api";
import { useLivePoll } from "./useLivePoll";

/**
 * Polling real com um voo, backoff limitado e retomada por visibilidade.
 * Não apaga a última observação ao pausar ou desabilitar.
 */
export function useExecutionPolling(executionId, { enabled, minIntervalMs = 1000, paused } = {}) {
  const poll = useLivePoll({
    enabled: Boolean(executionId) && enabled,
    paused,
    intervalMs: minIntervalMs,
    maxBackoffMs: 15000,
    timeoutMs: 12000,
    resetKey: executionId || "",
    run: (signal) => getExecutionDetail(executionId, { signal }),
    isTerminal: (data) => isTerminalState(data?.summary?.state),
  });

  return {
    detail: poll.value,
    error: poll.error,
    updatedAt: poll.updatedAt,
    status: poll.status === "ok" ? "ok" : poll.status,
    stale: poll.stale,
    auth: poll.auth,
    setDetail() {},
  };
}
