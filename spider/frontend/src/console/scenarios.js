import { generateTraceparent } from "../lib/trace";

export const MOCK_SCENARIOS = [
  {
    id: "SUCCESS_MULTI_STEP",
    label: "Sucesso em múltiplas etapas",
    description: "Plano completo com todas as etapas concluídas.",
    routeCode: "SUCCESS_MULTI_STEP",
    mockScenario: "SUCCESS",
  },
  {
    id: "RETRY_THEN_SUCCESS",
    label: "Retry com sucesso",
    description: "Falha transitória seguida por nova tentativa bem-sucedida.",
    routeCode: "RETRY_THEN_SUCCESS",
    mockScenario: "RETRY_THEN_SUCCESS",
  },
  {
    id: "BUSINESS_NEGATIVE",
    label: "Negativa de negócio",
    description: "Resultado negativo de negócio, sem falha técnica.",
    routeCode: "BUSINESS_NEGATIVE",
    mockScenario: "BUSINESS_NEGATIVE",
  },
  {
    id: "WAIT_SIGNAL_RESUME",
    label: "Espera, sinal e retomada",
    description: "Execução aguarda um sinal externo e depois continua.",
    routeCode: "WAIT_SIGNAL_RESUME",
    mockScenario: "ACCEPTED_ASYNC",
    twoPhase: true,
  },
  {
    id: "CALLBACK_RECONCILIATION",
    label: "Callback e reconciliação",
    description: "Resultado assíncrono recebido e reconciliado pela Spider.",
    routeCode: "CALLBACK_RECONCILIATION",
    mockScenario: "SUCCESS",
    callbackRef: "callback:console-local-demo",
  },
  {
    id: "TECHNICAL_FAILURE",
    label: "Falha técnica",
    description: "Falha terminal registrada durante a execução.",
    routeCode: "TECHNICAL_FAILURE",
    mockScenario: "TECHNICAL_FAILURE",
  },
];

export function buildCanonicalRequest(scenario, { idempotencyKey, traceparent } = {}) {
  const now = new Date().toISOString();
  const corr = `corr-${scenario.id}-${Date.now()}`;
  return {
    contract: { schemaVersion: "1.0", contractVersion: "1.0.0" },
    execution: {
      executionId: `exec-${crypto.randomUUID()}`,
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
        mockScenario: scenario.mockScenario || scenario.id,
        channel: "operational-console",
        intent: "demo",
      },
    },
    callbackRef: scenario.callbackRef || null,
  };
}

export function buildWaitSignal(executionId, { correlationId } = {}) {
  return {
    signalContractVersion: "1.0",
    messageId: `sig-${crypto.randomUUID()}`,
    sourceRef: "source:mock-async@1.0",
    bindingRef: "binding:mock-universal@1.0",
    contractRef: "contract:signal:async-completion@1.0",
    executionId,
    stepId: "step-1",
    externalOperationRef: `ext-op-${executionId}-step-1`,
    occurredAt: new Date().toISOString(),
    correlationId: correlationId || `corr-signal-${executionId}`,
    completion: {
      disposition: "COMPLETED",
      outcome: { technicalStatus: "SUCCESS" },
      errors: [],
    },
  };
}

export function newIdempotencyKey(scenarioId) {
  return `idem-${scenarioId}-${crypto.randomUUID()}`;
}

export function newTraceparent() {
  return generateTraceparent();
}
