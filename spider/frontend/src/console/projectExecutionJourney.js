/**
 * Projeção visual da execução a partir do read model existente.
 * Não inventa progresso: só entra no caminho o que houver evidência
 * (summary, timeline persistida, steps/attempts, wait/callback, Operational Events).
 */

export const JOURNEY_VISUAL_STATES = [
  "NOT_REACHED",
  "ACTIVE",
  "SUCCEEDED",
  "WAITING",
  "RETRYING",
  "DELAYED",
  "REJECTED",
  "FAILED",
];

export const JOURNEY_MARKERS = {
  SUCCEEDED: "✓",
  FAILED: "✕",
  REJECTED: "✕",
  WAITING: "…",
  RETRYING: "↻",
  DELAYED: "↻",
  ACTIVE: "◉",
  NOT_REACHED: "○",
};

const TERMINAL = new Set([
  "SUCCEEDED",
  "PARTIALLY_SUCCEEDED",
  "COMPENSATED",
  "FAILED",
  "TIMED_OUT",
  "REJECTED",
  "CANCELLED",
]);

function blob(value) {
  try {
    return JSON.stringify(value || {});
  } catch {
    return String(value || "");
  }
}

function timelineHits(timeline, pattern) {
  const events = timeline?.available ? timeline.data || [] : [];
  const re = pattern instanceof RegExp ? pattern : new RegExp(pattern);
  return events.some((event) => re.test(blob(event)));
}

function opEventsOf(operationalEvents, prefixOrName) {
  const events = operationalEvents || [];
  return events.filter((event) => {
    const type = String(event.eventType || "");
    return type === prefixOrName || type.startsWith(prefixOrName);
  });
}

function mapAttemptVisual(state) {
  const s = String(state || "").toUpperCase();
  if (s === "SUCCEEDED" || s === "COMPLETED" || s === "SUCCESS") return "SUCCEEDED";
  if (s === "FAILED" || s === "ERROR") return "FAILED";
  if (s === "REJECTED") return "REJECTED";
  if (s === "RUNNING" || s === "STARTED" || s === "PENDING") return "ACTIVE";
  return s ? "ACTIVE" : "NOT_REACHED";
}

function mapCapacityVisual(eventType) {
  const type = String(eventType || "");
  if (type.includes("ADMITTED")) return "SUCCEEDED";
  if (type.includes("DELAYED")) return "DELAYED";
  if (type.includes("SHED") || type.includes("LOAD_SHED")) return "REJECTED";
  if (type.includes("REJECTED") || type.includes("EXHAUSTED") || type.includes("SATURATED")) {
    return "REJECTED";
  }
  if (type.includes("OPEN")) return "FAILED";
  return "ACTIVE";
}

function stage(id, title, layer, state, evidence) {
  return {
    id,
    title,
    layer,
    state,
    evidence,
    marker: JOURNEY_MARKERS[state] || "○",
  };
}

function contextStage(item) {
  const visual = JOURNEY_VISUAL_STATES.includes(item?.state) ? item.state : "NOT_REACHED";
  const isPlan = item?.layer === "PLAN";
  return {
    ...stage(
      `context-${item.id}`,
      item.title,
      isPlan ? "plano" : "contexto",
      visual,
      "context-read-model",
    ),
    zone: isPlan ? "PLAN" : "CONTEXT",
    contextDetail: item,
  };
}

function completionVisual(executionState) {
  const s = String(executionState || "");
  if (s === "SUCCEEDED" || s === "PARTIALLY_SUCCEEDED" || s === "COMPENSATED") return "SUCCEEDED";
  if (s === "FAILED" || s === "TIMED_OUT" || s === "CANCELLED") return "FAILED";
  if (s === "REJECTED") return "REJECTED";
  if (s === "WAITING_EXTERNAL") return "NOT_REACHED";
  if (s === "RUNNING" || s === "PLANNED" || s === "RECEIVED" || s === "VALIDATED" || s === "RESOLVED") {
    return "NOT_REACHED";
  }
  return "NOT_REACHED";
}

export function humanStepName(step, stepRef, fallbackIndex = 0) {
  const explicit = step?.name || step?.title || step?.description;
  if (explicit) return String(explicit);
  const ref = String(stepRef || "");
  const numbered = ref.match(/^step-(\d+)$/i);
  if (numbered) return `Etapa ${numbered[1]}`;
  if (Number.isFinite(Number(step?.order))) return `Etapa ${Number(step.order) + 1}`;
  const stripped = ref.replace(/^step-/i, "");
  if (stripped && stripped !== ref) return `Etapa ${stripped}`;
  return `Etapa ${fallbackIndex + 1}`;
}

export function stepCapabilityHint(step) {
  return step?.capability || step?.capabilityCode || step?.capabilityRef || step?.adapterRef || step?.provider || null;
}

export function interactionStageTitle(step, stepRef, attemptNumber, fallbackIndex = 0) {
  const name = humanStepName(step, stepRef, fallbackIndex);
  const capability = stepCapabilityHint(step);
  const attempt = `tentativa ${attemptNumber}`;
  return capability ? `${name} · ${capability} · ${attempt}` : `${name} · ${attempt}`;
}

export function stableAttemptIdentity(stepRef, attempt = {}) {
  const number = attempt.attemptNumber ?? "";
  const attemptId = attempt.attemptId || attempt.attemptRef || "";
  return `${stepRef}::${number}::${attemptId}`;
}

function resolveAttempts(step, timeline) {
  const listed = Array.isArray(step.attempts) ? step.attempts : [];
  if (listed.length) {
    return listed;
  }
  const events = timeline?.available ? timeline.data || [] : [];
  const stepRef = step.stepRef || step.stepId;
  return events
    .filter(
      (event) =>
        String(event.eventType) === "ATTEMPT" &&
        (event.attemptNumber || event.title) &&
        (!event.stepRef || !stepRef || event.stepRef === stepRef),
    )
    .map((event) => ({
      attemptNumber: event.attemptNumber,
      state: event.state,
    }));
}

/**
 * @param {{
 *   summary?: object,
 *   timeline?: { available?: boolean, data?: object[] },
 *   steps?: { available?: boolean, data?: object[] },
 *   waitInfo?: { available?: boolean, data?: object },
 *   callback?: { available?: boolean, data?: object },
 *   operationalEvents?: object[],
 *   contextJourney?: object[],
 * }} input
 */
export function projectExecutionJourney(input = {}) {
  const summary = input.summary || {};
  const timeline = input.timeline;
  const steps = input.steps;
  const waitInfo = input.waitInfo;
  const callback = input.callback;
  const operationalEvents = input.operationalEvents || [];
  const executionState = summary.state;
  const stages = (input.contextJourney || []).map(contextStage);

  if (!summary.executionId) {
    return { executionId: null, state: null, stages: [] };
  }

  const received =
    Boolean(summary.startedAt) ||
    timelineHits(timeline, /RECEIVED|STATE_TRANSITION/) ||
    opEventsOf(operationalEvents, "EXECUTION_STARTED").length > 0 ||
    opEventsOf(operationalEvents, "SATELLITE_REQUEST_RECEIVED").length > 0;
  stages.push(
    {
      ...stage(
        "request",
        "Solicitação recebida",
        "entrada",
        received ? "SUCCEEDED" : "ACTIVE",
        received ? "summary+timeline" : "summary",
      ),
      zone: "DATA",
    },
  );

  const satelliteRequested = opEventsOf(operationalEvents, "SATELLITE_REQUEST_RECEIVED");
  if (satelliteRequested.length) {
    const company = opEventsOf(operationalEvents, "SATELLITE_COMPANY_AUTHORIZED");
    const dispatched = opEventsOf(operationalEvents, "CAPABILITY_DISPATCHED");
    const outbound = opEventsOf(operationalEvents, "OUTBOUND_REQUEST_STARTED");
    const provider = opEventsOf(operationalEvents, "PROVIDER_RESULT_RECEIVED");
    const returned = opEventsOf(operationalEvents, "SATELLITE_RESPONSE_RETURNED");
    const capability = dispatched.at(-1)?.metadata?.reasonCode || null;
    const itemCount = provider.at(-1)?.metadata?.itemCount;
    const environment = provider.at(-1)?.metadata?.environment || dispatched.at(-1)?.metadata?.environment;
    stages.push(
      stage("sat-finance-requested", "Finance solicitou", "satélite", "SUCCEEDED", "SATELLITE_REQUEST_RECEIVED"),
    );
    stages.push(
      stage(
        "sat-company",
        "Empresa autorizada",
        "satélite",
        company.length ? "SUCCEEDED" : "NOT_REACHED",
        company.length ? "SATELLITE_COMPANY_AUTHORIZED" : "ausente",
      ),
    );
    stages.push(
      stage(
        "sat-capability",
        capability ? `Capacidade ${capability}` : "Capacidade selecionada no registry",
        "satélite",
        dispatched.length ? "SUCCEEDED" : "NOT_REACHED",
        dispatched.length ? "CAPABILITY_DISPATCHED" : "ausente",
      ),
    );
    stages.push(
      stage(
        "sat-provider",
        "Provider ActionHub Pay acionado",
        "satélite",
        outbound.length || provider.length ? "SUCCEEDED" : dispatched.length ? "ACTIVE" : "NOT_REACHED",
        outbound.length ? "OUTBOUND_REQUEST_STARTED" : provider.length ? "PROVIDER_RESULT_RECEIVED" : "ausente",
      ),
    );
    stages.push(
      stage(
        "sat-response",
        itemCount != null
          ? `Resposta recebida · ${itemCount} item(ns)${environment ? ` · ${environment}` : ""}`
          : "Resposta recebida",
        "satélite",
        provider.length ? (provider.at(-1)?.outcome === "FAILURE" ? "FAILED" : "SUCCEEDED") : "NOT_REACHED",
        provider.length ? "PROVIDER_RESULT_RECEIVED" : "ausente",
      ),
    );
    stages.push(
      stage(
        "sat-returned",
        "Resultado devolvido à origem",
        "satélite",
        returned.length ? "SUCCEEDED" : "NOT_REACHED",
        returned.length ? "SATELLITE_RESPONSE_RETURNED" : "ausente",
      ),
    );
  }

  const securityEvents = opEventsOf(operationalEvents, "SECURITY_");
  if (securityEvents.length) {
    const rejected = securityEvents.some((event) => String(event.eventType).includes("REJECTED"));
    stages.push(
      stage(
        "authentication",
        "Autenticação / segurança",
        "entrada",
        rejected ? "REJECTED" : "SUCCEEDED",
        "operational-events",
      ),
    );
  }

  const validated = timelineHits(timeline, /VALIDATED|REQUEST_VALIDATED/);
  const hasRoute = Boolean(summary.routeRef);
  if (validated || hasRoute) {
    stages.push(
      stage(
        "canonical",
        "Contrato canônico",
        "canonicalização",
        validated || hasRoute ? "SUCCEEDED" : "NOT_REACHED",
        validated ? "timeline" : "summary.routeRef",
      ),
    );
  }

  const capacityEvents = opEventsOf(operationalEvents, "CAPACITY_");
  if (capacityEvents.length) {
    const last = capacityEvents[capacityEvents.length - 1];
    stages.push(
      stage(
        "capacity",
        "Admissão / capacidade",
        "resiliência",
        mapCapacityVisual(last.eventType),
        "operational-events",
      ),
    );
  }

  const engineStarted =
    timelineHits(timeline, /RESOLVED|PLANNED|RUNNING|ROUTE_SELECTED|PLAN_MATERIALIZED|STEPS_STARTED/) ||
    opEventsOf(operationalEvents, "EXECUTION_STARTED").length > 0 ||
    ["RUNNING", "WAITING_EXTERNAL", "SUCCEEDED", "FAILED", "REJECTED", "TIMED_OUT"].includes(
      executionState,
    );
  if (engineStarted) {
    let engineState = "SUCCEEDED";
    if (executionState === "RUNNING" || executionState === "PLANNED" || executionState === "RESOLVED") {
      engineState = "ACTIVE";
    }
    if (executionState === "RECEIVED" || executionState === "VALIDATED") {
      engineState = "ACTIVE";
    }
    stages.push(stage("engine", "Engine", "execução", engineState, "timeline+state"));
  }

  const workerEvents = [
    ...opEventsOf(operationalEvents, "SCHEDULE_"),
    ...opEventsOf(operationalEvents, "WORK_ITEM_"),
    ...opEventsOf(operationalEvents, "LEASE_"),
  ];
  if (workerEvents.length) {
    const failed = workerEvents.some((event) =>
      /FAILED|FENCED|EXPIRED/.test(String(event.eventType)),
    );
    stages.push(
      stage(
        "worker",
        "Worker / schedule",
        "runtime",
        failed ? "FAILED" : "SUCCEEDED",
        "operational-events",
      ),
    );
  }

  const stepList = steps?.available ? steps.data || [] : [];
  const seenAttempts = new Set();
  stepList.forEach((step, stepIndex) => {
    const attempts = resolveAttempts(step, timeline);
    const stepRef = step.stepRef || step.stepId || "step";
    if (!attempts.length && (step.attemptCount > 0 || step.state)) {
      const identity = stableAttemptIdentity(stepRef, { attemptNumber: "", attemptId: step.stepRef || step.stepId });
      if (seenAttempts.has(identity)) return;
      seenAttempts.add(identity);
      stages.push({
        ...stage(
          `interaction-${stepRef}`,
          humanStepName(step, stepRef, stepIndex),
          "integração",
          mapAttemptVisual(step.state),
          "steps",
        ),
        stepRef,
        stepOrder: Number.isFinite(Number(step.order)) ? Number(step.order) + 1 : stepIndex + 1,
        attemptNumber: null,
        attemptId: null,
        capability: stepCapabilityHint(step),
      });
      return;
    }
    attempts.forEach((attempt, index) => {
      const number = attempt.attemptNumber || index + 1;
      const identity = stableAttemptIdentity(stepRef, { ...attempt, attemptNumber: number });
      if (seenAttempts.has(identity)) return;
      seenAttempts.add(identity);
      const visual = mapAttemptVisual(attempt.state);
      stages.push({
        ...stage(
          `interaction-${stepRef}-${number}`,
          interactionStageTitle(step, stepRef, number, stepIndex),
          "integração",
          visual,
          "attempts",
        ),
        stepRef,
        stepOrder: Number.isFinite(Number(step.order)) ? Number(step.order) + 1 : stepIndex + 1,
        attemptNumber: number,
        attemptId: attempt.attemptId || attempt.attemptRef || null,
        capability: stepCapabilityHint(step),
      });
      const next = attempts[index + 1];
      if ((visual === "FAILED" || visual === "REJECTED") && next) {
        const nextVisual = mapAttemptVisual(next.state);
        stages.push(
          stage(
            `retry-${stepRef}-${number}`,
            "Retry",
            "continuidade",
            nextVisual === "ACTIVE" ? "RETRYING" : "SUCCEEDED",
            "attempts",
          ),
        );
      } else if ((visual === "FAILED" || visual === "REJECTED") && !next && executionState === "RUNNING") {
        stages.push(
          stage(`retry-${stepRef}-${number}`, "Retry", "continuidade", "RETRYING", "attempts+state"),
        );
      }
    });
  });

  const interactionOps = opEventsOf(operationalEvents, "INTERACTION_").concat(
    opEventsOf(operationalEvents, "OUTBOUND_"),
  );
  if (!stepList.length && interactionOps.length) {
    const failed = interactionOps.some((event) =>
      /TIMEOUT|ERROR|FAILED/.test(String(event.eventType)),
    );
    const completed = interactionOps.some((event) => event.eventType === "INTERACTION_COMPLETED");
    stages.push(
      stage(
        "interaction-op",
        "Interaction",
        "integração",
        failed ? "FAILED" : completed ? "SUCCEEDED" : "ACTIVE",
        "operational-events",
      ),
    );
  }

  const waitAvailable = Boolean(waitInfo?.available && waitInfo.data);
  const waitingEvent = opEventsOf(operationalEvents, "EXECUTION_WAITING").length > 0;
  if (waitAvailable || waitingEvent) {
    const waitState = waitInfo?.data?.waitState || (waitingEvent ? "WAITING" : "");
    let visual = "WAITING";
    if (/RESUMED|SIGNALLED|COMPLETED|CLOSED/.test(waitState)) visual = "SUCCEEDED";
    if (/EXPIRED|FAILED|CANCELLED/.test(waitState)) visual = "FAILED";
    if (waitState === "WAITING" || executionState === "WAITING_EXTERNAL") visual = "WAITING";
    stages.push(stage("wait", "Wait / sinal externo", "continuidade", visual, waitAvailable ? "waitInfo" : "operational-events"));
  }

  const resumed = opEventsOf(operationalEvents, "EXECUTION_RESUMED").length > 0;
  if (resumed) {
    stages.push(stage("resume", "Resume", "continuidade", "SUCCEEDED", "operational-events"));
  }

  const signalEvents = opEventsOf(operationalEvents, "SIGNAL_");
  if (signalEvents.length) {
    const rejected = signalEvents.some((event) => String(event.eventType).includes("REJECTED"));
    const accepted = signalEvents.some((event) => String(event.eventType).includes("ACCEPTED"));
    stages.push(
      stage(
        "signal",
        "Signal",
        "continuidade",
        rejected ? "REJECTED" : accepted ? "SUCCEEDED" : "ACTIVE",
        "operational-events",
      ),
    );
  }

  if (callback?.available && callback.data) {
    const cbState = String(callback.data.outboxState || callback.data.confirmationState || "");
    let visual = "ACTIVE";
    if (/DELIVERED|CONFIRMED|COMPLETED|ACCEPTED/.test(cbState)) visual = "SUCCEEDED";
    if (/FAILED|REJECTED|ERROR/.test(cbState)) visual = "FAILED";
    stages.push(stage("callback", "Callback", "continuidade", visual, "callback"));
  }

  const persisted = timelineHits(timeline, /PERSISTED|RESULT_STORED|STATE_TRANSITION/);
  if (persisted || summary.executionId) {
    const persistVisual =
      TERMINAL.has(executionState) || persisted ? "SUCCEEDED" : engineStarted ? "ACTIVE" : "NOT_REACHED";
    if (persistVisual !== "NOT_REACHED") {
      stages.push(
        stage("persistence", "Estado persistido", "conclusão", persistVisual, "timeline"),
      );
    }
  }

  stages.push(
    stage(
      "completion",
      "Execução concluída",
      "conclusão",
      completionVisual(executionState),
      "summary.state",
    ),
  );

  return {
    executionId: summary.executionId,
    state: executionState || null,
    stages,
  };
}

export function journeyHasLayer(projection, layer) {
  return (projection?.stages || []).some((item) => item.layer === layer);
}
