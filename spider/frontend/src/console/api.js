/**
 * Cliente tipado do console operacional — sem localStorage de tokens.
 */

function parseProblem(body) {
  if (!body || typeof body !== "object") {
    return { title: "Erro desconhecido", status: 0 };
  }
  return {
    title: body.title || body.reasonCode || "Erro",
    status: body.status || 0,
    detail: body.detail,
  };
}

async function request(path, { method = "GET", body, signal, headers = {} } = {}) {
  const res = await fetch(path, {
    method,
    signal,
    headers: {
      Accept: "application/json, application/problem+json",
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }
  if (!res.ok) {
    const problem = parseProblem(data);
    const err = new Error(problem.title || `HTTP ${res.status}`);
    err.status = res.status;
    err.problem = problem;
    err.consoleUnavailable = res.status === 404 || res.status === 500;
    throw err;
  }
  return data;
}

export function listExecutions(filters = {}, cursor = {}, { signal } = {}) {
  const q = new URLSearchParams();
  if (filters.states?.length) q.set("states", filters.states.join(","));
  if (filters.routeCode) q.set("routeCode", filters.routeCode);
  if (filters.onlyWaiting) q.set("onlyWaiting", "true");
  if (filters.startedFrom) q.set("startedFrom", filters.startedFrom);
  if (filters.startedTo) q.set("startedTo", filters.startedTo);
  if (filters.limit) q.set("limit", String(filters.limit));
  if (cursor.cursorStartedAt) q.set("cursorStartedAt", cursor.cursorStartedAt);
  if (cursor.cursorExecutionId) q.set("cursorExecutionId", cursor.cursorExecutionId);
  const qs = q.toString();
  return request(`/v1/console/executions${qs ? `?${qs}` : ""}`, { signal });
}

export function getExecutionDetail(executionId, { signal } = {}) {
  return request(`/v1/console/executions/${encodeURIComponent(executionId)}`, { signal });
}

export function getExecutionOperationalEvents(executionId, { signal } = {}) {
  return request(`/v1/console/executions/${encodeURIComponent(executionId)}/events`, { signal });
}

export function submitMockScenario(httpBody, { idempotencyKey, traceparent, signal } = {}) {
  return request("/v1/canonical/executions", {
    method: "POST",
    body: httpBody,
    signal,
    headers: {
      "Idempotency-Key": idempotencyKey,
      traceparent,
      "X-Spider-Credential-Ref": "local-demo-console",
    },
  });
}

export function submitMockSignal(body, { signal } = {}) {
  return request("/v1/canonical/signals", {
    method: "POST",
    body,
    signal,
    headers: { "X-Spider-Credential-Ref": "local-demo-console" },
  });
}

export function getImplementationStatus({ signal } = {}) {
  return request("/v1/console/implementation", { signal });
}

export function getPresentationReadiness({ signal } = {}) {
  return request("/v1/console/presentation/readiness", { signal });
}

export function getOperationalHealth(window = "PT24H", { signal } = {}) {
  const query = new URLSearchParams({ window });
  return request(`/v1/console/operational-health?${query}`, { signal });
}

export function listFailureLabScenarios({ signal } = {}) {
  return request("/v1/console/failure-lab/scenarios", { signal });
}

export function startFailureLabRun(body, { signal } = {}) {
  return request("/v1/console/failure-lab/runs", {
    method: "POST",
    body,
    signal,
    headers: { "X-Spider-Credential-Ref": "local-demo-console" },
  });
}

export function getFailureLabRun(labRunId, { signal } = {}) {
  return request(`/v1/console/failure-lab/runs/${encodeURIComponent(labRunId)}`, { signal });
}

export function getFailureLabEvidence(labRunId, { signal } = {}) {
  return request(`/v1/console/failure-lab/runs/${encodeURIComponent(labRunId)}/evidence`, {
    signal,
  });
}

export const TERMINAL_STATES = new Set([
  "SUCCEEDED",
  "PARTIALLY_SUCCEEDED",
  "COMPENSATED",
  "FAILED",
  "TIMED_OUT",
  "REJECTED",
  "CANCELLED",
]);

export function isTerminalState(state) {
  return TERMINAL_STATES.has(state);
}
