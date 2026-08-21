import { generateTraceparent } from "../lib/trace";

export const MOCK_SCENARIOS = [
  {
    id: "SUCCESS_MULTI_STEP",
    label: "Sucesso multi-step",
    description: "Rota Mock com vários steps bem-sucedidos.",
    routeCode: "SUCCESS_MULTI_STEP",
  },
  {
    id: "RETRY_THEN_SUCCESS",
    label: "Retry → sucesso",
    description: "Primeira attempt falha transitória; segunda sucede.",
    routeCode: "RETRY_THEN_SUCCESS",
  },
  {
    id: "BUSINESS_NEGATIVE",
    label: "Negativa de negócio",
    description: "Outcome de negócio negativo distinto de falha técnica.",
    routeCode: "BUSINESS_NEGATIVE",
  },
  {
    id: "WAIT_SIGNAL_RESUME",
    label: "Wait / signal / resume",
    description: "Aguarda sinal externo; requer signal HTTP Mock habilitado.",
    routeCode: "WAIT_SIGNAL_RESUME",
  },
  {
    id: "CALLBACK_RECONCILIATION",
    label: "Callback / reconciliation",
    description: "Outbox e reconciliação após resultado.",
    routeCode: "CALLBACK_RECONCILIATION",
  },
  {
    id: "TECHNICAL_FAILURE",
    label: "Falha técnica",
    description: "Falha técnica terminal no adapter Mock.",
    routeCode: "TECHNICAL_FAILURE",
  },
];

export function buildCanonicalRequest(scenario, { idempotencyKey, traceparent } = {}) {
  const now = new Date().toISOString();
  const corr = `corr-${scenario.id}-${Date.now()}`;
  return {
    contract: { schemaVersion: "1.0", contractVersion: "1.0.0" },
    execution: {
      executionId: null,
      requestedAt: now,
      idempotencyKey: idempotencyKey || null,
    },
    contextRef: {
      contextId: `ctx-${scenario.id}`,
      intentId: "intent:demo",
      capabilityId: "capability:mock",
      productServiceId: "product:mock",
      journeyId: "journey:mock",
    },
    origin: {
      channel: "operational-console",
      originatorId: "console-local-demo",
      interactionRef: corr,
    },
    trace: {
      correlationId: corr,
      traceparent: traceparent || null,
      tracestate: null,
    },
    target: {
      capability: "mock",
      operation: scenario.routeCode,
    },
    payload: {
      canonicalData: {
        scenario: scenario.id,
        mockScenario: scenario.id,
        channel: "operational-console",
        intent: "demo",
      },
    },
    callbackRef: null,
  };
}

export function newIdempotencyKey(scenarioId) {
  return `idem-${scenarioId}-${crypto.randomUUID()}`;
}

export function newTraceparent() {
  return generateTraceparent();
}
