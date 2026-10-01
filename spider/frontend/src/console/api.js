/**
 * Cliente tipado do console operacional — sem localStorage de tokens.
 * No sandbox publicado as consultas vão à mesma origem; a sessão OIDC fica
 * em cookie HttpOnly. A credencial local-demo continua só no desenvolvimento.
 */

export const LOCAL_DEMO_CREDENTIAL = "local-demo-console";
export const SANDBOX_CREDENTIAL = "sandbox-operator";

const API_BASE = (import.meta.env.VITE_SPIDER_API_BASE || "").replace(/\/$/, "");

function credentialRef() {
  if (import.meta.env.VITE_SPIDER_CREDENTIAL_REF) {
    return import.meta.env.VITE_SPIDER_CREDENTIAL_REF;
  }
  return import.meta.env.PROD ? SANDBOX_CREDENTIAL : LOCAL_DEMO_CREDENTIAL;
}

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

export function operationLabel(path) {
  const value = String(path || "");
  if (value.includes("/v1/context/executions/") && !value.endsWith("/executions")) {
    return "Consulta de contexto da execução";
  }
  if (value.includes("/v1/console/executions/") && value.endsWith("/events")) {
    return "Consulta de eventos relacionados";
  }
  if (value.includes("/v1/console/monitor/events")) {
    return "Consulta de eventos do Monitor";
  }
  if (value.includes("/v1/console/executions/")) {
    return "Consulta do detalhe da execução";
  }
  if (value.includes("/v1/console/executions")) {
    return "Consulta da lista de execuções";
  }
  if (value.includes("/v1/canonical/executions")) {
    return "Consulta de execuções canônicas";
  }
  return "Consulta operacional";
}

export function describeRequestFailure(path, status, problem = {}) {
  const operation = operationLabel(path);
  if (status === 404) {
    return `${operation} não está disponível neste ambiente.`;
  }
  const hint = problem.detail || problem.title || `HTTP ${status}`;
  return `${operation} falhou (${status}): ${hint}`;
}

async function request(path, { method = "GET", body, signal, headers = {} } = {}) {
  const headersOut = {
    Accept: "application/json, application/problem+json",
    ...(body ? { "Content-Type": "application/json" } : {}),
    ...headers,
  };
  const credential = credentialRef();
  if (credential) {
    headersOut["X-Spider-Credential-Ref"] = credential;
  }
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    signal,
    credentials: "same-origin",
    headers: headersOut,
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
    const err = new Error(describeRequestFailure(path, res.status, problem));
    err.status = res.status;
    err.problem = problem;
    err.body = data;
    err.consoleUnavailable = res.status === 404 || res.status === 500;
    throw err;
  }
  return data;
}

/** Identidade canônica: o POST devolve ExecutionSummary aninhado, não executionId no topo. */
export function extractCanonicalExecutionId(payload, fallback = null) {
  if (typeof payload === "string" && payload.trim()) {
    return payload.trim();
  }
  if (!payload || typeof payload !== "object") {
    return fallback || null;
  }
  const candidates = [
    payload.executionId,
    payload.executionRef,
    payload.execution && payload.execution.executionId,
    payload.execution && payload.execution.id,
    payload.summary && payload.summary.executionId,
    payload.id,
    payload.result && extractCanonicalExecutionId(payload.result, null),
  ];
  for (const value of candidates) {
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return fallback || null;
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
    },
  });
}

export function getContextIntentCatalog({ signal } = {}) {
  return request("/v1/context/intents", { signal });
}

export function resolveBusinessIntent(intentContract, { signal } = {}) {
  return request("/v1/context/intents/resolve", {
    method: "POST",
    body: intentContract,
    signal,
  });
}

export function interpretNaturalLanguage(objective, { signal } = {}) {
  return request("/v1/context/interpretations", {
    method: "POST",
    body: { objective },
    signal,
  });
}

export function executeContextIntent(decisionId, intentContract, { signal } = {}) {
  return request("/v1/context/executions", {
    method: "POST",
    body: { decisionId, intentContract },
    signal,
  });
}

export function getExecutionContext(executionId, { signal } = {}) {
  return request(`/v1/context/executions/${encodeURIComponent(executionId)}`, { signal });
}

export function submitMockSignal(body, { signal } = {}) {
  return request("/v1/canonical/signals", {
    method: "POST",
    body,
    signal,
    headers: credentialRef() ? { "X-Spider-Credential-Ref": credentialRef() } : {},
  });
}

export function getPlatformHealth({ signal } = {}) {
  return request("/actuator/health", { signal });
}

export function listCanonicalExecutions({ signal } = {}) {
  return request("/v1/canonical/executions", { signal });
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
    headers: credentialRef() ? { "X-Spider-Credential-Ref": credentialRef() } : {},
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

export function getWorkerRuntime({ signal } = {}) {
  return request("/v1/console/runtime", { signal });
}

export function listWorkerRuntimeWorkers({ signal } = {}) {
  return request("/v1/console/runtime/workers", { signal });
}

export function drainWorker(workerId, { signal } = {}) {
  return request(`/v1/console/runtime/workers/${encodeURIComponent(workerId)}/drain`, {
    method: "POST",
    signal,
    headers: credentialRef() ? { "X-Spider-Credential-Ref": credentialRef() } : {},
  });
}

export function getCapacitySnapshot({ signal } = {}) {
  return request("/v1/console/capacity", { signal });
}

export function getCapacityDecisions(limit = 50, { signal } = {}) {
  return request(`/v1/console/capacity/decisions?limit=${limit}`, { signal });
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

export function getMonitorEvents({ signal } = {}) {
  return request("/v1/console/monitor/events", { signal });
}

export function getSimulationReadiness({ signal } = {}) {
  return request("/v1/console/monitor/simulation", { signal });
}
