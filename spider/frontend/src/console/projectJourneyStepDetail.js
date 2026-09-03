const EXECUTION_FAILURE_STATES = new Set(["FAILED", "TIMED_OUT", "REJECTED", "CANCELLED"]);

function sectionData(section) {
  return section?.available ? section.data : null;
}

function timelineEvents(input) {
  return sectionData(input.timeline) || [];
}

function stepList(input) {
  return sectionData(input.steps) || [];
}

function routeName(summary) {
  return summary?.routeRef || summary?.operationRef || null;
}

function isRetryDemo(summary) {
  return String(routeName(summary) || "").toUpperCase().includes("RETRY_THEN_SUCCESS");
}

function attemptContext(stage, input) {
  const match = stage.id.match(/^interaction-(.+)-(\d+)$/);
  if (!match) return null;
  const [, stepRef, numberText] = match;
  const number = Number(numberText);
  const step = stepList(input).find((item) => (item.stepRef || item.stepId) === stepRef);
  const attempts = step?.attempts || [];
  const attempt = attempts.find((item) => Number(item.attemptNumber) === number);
  return { step, attempts, attempt, stepRef, number };
}

function retryContext(stage, input) {
  const match = stage.id.match(/^retry-(.+)-(\d+)$/);
  if (!match) return null;
  const [, stepRef, numberText] = match;
  const number = Number(numberText);
  const step = stepList(input).find((item) => (item.stepRef || item.stepId) === stepRef);
  const attempts = step?.attempts || [];
  const previous = attempts.find((item) => Number(item.attemptNumber) === number);
  const next = attempts.find((item) => Number(item.attemptNumber) === number + 1);
  return { step, attempts, previous, next, stepRef, number };
}

function totalAttempts(input) {
  return stepList(input).reduce(
    (sum, step) => sum + (step.attempts?.length || step.attemptCount || 0),
    0,
  );
}

function countContinuity(stages, id) {
  return stages.filter((item) => item.id === id || item.id.startsWith(`${id}-`)).length;
}

function compactDetails(details) {
  return details.filter((item) => item.value !== null && item.value !== undefined && item.value !== "");
}

function normalizeTimeline(event) {
  return {
    id: `timeline-${event.eventId || event.sequence || event.title}`,
    eventType: event.eventType,
    occurredAt: event.occurredAt,
    source: event.source || "PERSISTED",
    outcome: event.state || event.severity,
    durationMs: event.durationMs,
  };
}

function normalizeOperational(event) {
  return {
    id: `operational-${event.eventId || event.eventType}-${event.occurredAt || ""}`,
    eventType: event.eventType,
    occurredAt: event.occurredAt,
    source: event.source || "OPERATIONAL_EVENT",
    outcome: event.outcome,
    durationMs: event.durationMs,
  };
}

function relatedTimeline(stage, input) {
  const events = timelineEvents(input);
  const interaction = attemptContext(stage, input);
  if (interaction) {
    return events.filter(
      (event) =>
        event.eventType === "ATTEMPT" &&
        event.stepRef === interaction.stepRef &&
        Number(event.attemptNumber) === interaction.number,
    );
  }
  const retry = retryContext(stage, input);
  if (retry) {
    return events.filter(
      (event) =>
        event.eventType === "ATTEMPT" &&
        event.stepRef === retry.stepRef &&
        [retry.number, retry.number + 1].includes(Number(event.attemptNumber)),
    );
  }
  if (stage.id === "request" || stage.id === "canonical" || stage.id === "engine") {
    return events.filter((event) => event.eventType === "STATE_TRANSITION").slice(0, 1);
  }
  if (stage.id === "persistence" || stage.id === "completion") {
    return events
      .filter((event) => event.eventType === "STATE_TRANSITION")
      .slice(-1);
  }
  if (stage.id === "wait") return events.filter((event) => String(event.eventType).startsWith("WAIT_"));
  return [];
}

function relatedOperational(stage, input) {
  const events = input.operationalEvents || [];
  const interaction = attemptContext(stage, input);
  const retry = retryContext(stage, input);
  if (interaction || retry) {
    const context = interaction || retry;
    const attemptNumbers = interaction
      ? [interaction.number]
      : [retry.number, retry.number + 1];
    return events.filter((event) => {
      const metadata = event.metadata || {};
      const eventAttempt = Number(metadata.attemptNumber || metadata.attempt);
      const eventStep = metadata.stepRef || metadata.stepId;
      const categoryMatches = ["INTERACTION", "TRANSPORT"].includes(String(event.category));
      const typeMatches = /^(INTERACTION_|OUTBOUND_)/.test(String(event.eventType || ""));
      return (
        (categoryMatches || typeMatches) &&
        attemptNumbers.includes(eventAttempt) &&
        (!eventStep || eventStep === context.stepRef)
      );
    });
  }
  const prefixes = {
    request: ["EXECUTION_STARTED"],
    authentication: ["SECURITY_"],
    capacity: ["CAPACITY_"],
    engine: ["EXECUTION_STARTED"],
    worker: ["WORKER_", "SCHEDULE_", "WORK_ITEM_", "LEASE_", "BACKLOG_"],
    wait: ["EXECUTION_WAITING"],
    resume: ["EXECUTION_RESUMED"],
    signal: ["SIGNAL_"],
    callback: ["CALLBACK_"],
    completion: ["EXECUTION_SUCCEEDED", "EXECUTION_FAILED", "EXECUTION_REJECTED"],
  };
  let accepted = prefixes[stage.id] || [];
  if (stage.id === "interaction-op") accepted = ["INTERACTION_", "OUTBOUND_"];
  if (!accepted.length) return [];
  return events.filter((event) =>
    accepted.some((prefix) => String(event.eventType || "").startsWith(prefix)),
  );
}

function relatedEvents(stage, input) {
  const events = [
    ...relatedTimeline(stage, input).map(normalizeTimeline),
    ...relatedOperational(stage, input).map(normalizeOperational),
  ];
  return events.filter(
    (event, index) => events.findIndex((candidate) => candidate.id === event.id) === index,
  );
}

function baseDetail(stage, input, stages) {
  const summary = input.summary || {};
  const details = compactDetails([
    { label: "Execução", value: summary.executionId },
    { label: "Rota", value: routeName(summary) },
  ]);
  const result = {
    summary: "Etapa observada na jornada real desta execução.",
    whatHappened: "Há evidência desta etapa no read model operacional.",
    technicalDetails: details,
    nextSteps: null,
  };

  if (stage.id === "request") {
    result.summary = "O Spider recebeu a solicitação pelo ingress canônico.";
    result.whatHappened =
      stage.state === "SUCCEEDED"
        ? "A solicitação foi aceita para processamento e associada a esta execução."
        : "A solicitação foi identificada e aguarda novas evidências do processamento.";
    result.technicalDetails = compactDetails([
      ...details,
      { label: "Recebida em", value: summary.startedAt },
      { label: "Correlação", value: summary.correlationRef },
    ]);
    result.nextSteps = "Validar o contrato e resolver a rota canônica aplicável.";
  } else if (stage.id === "canonical") {
    result.summary = "A solicitação foi reconhecida pelo contrato canônico.";
    result.whatHappened =
      "O Spider associou identificação, correlação e rota à execução antes de iniciar o processamento.";
    result.nextSteps = "Materializar o plano e iniciar a Engine.";
  } else if (stage.id === "engine") {
    result.summary = "A Engine iniciou o processamento da rota resolvida.";
    result.whatHappened =
      "A execução e seus passos foram registrados e processados conforme o plano persistido.";
    result.technicalDetails = compactDetails([
      ...details,
      { label: "Estado da execução", value: summary.state },
      { label: "Passos concluídos", value: summary.completedSteps },
      { label: "Total de passos", value: summary.totalSteps },
    ]);
    result.nextSteps = "Executar as interações previstas no plano.";
  } else if (stage.id === "persistence") {
    result.summary = `O estado ${summary.state || stage.state} foi persistido.`;
    result.whatHappened =
      "O read model registra o estado e as evidências técnicas disponíveis para consulta operacional.";
    result.technicalDetails = compactDetails([
      ...details,
      { label: "Estado persistido", value: summary.state },
      { label: "Outcome técnico", value: summary.technicalStatus },
      { label: "Atualizado em", value: summary.updatedAt },
    ]);
    result.nextSteps = summary.completedAt
      ? "A execução já alcançou um estado terminal."
      : "Persistir as próximas transições conforme o processamento avançar.";
  } else if (stage.id === "completion") {
    const retries = countContinuity(stages, "retry");
    result.summary = `A execução terminou em ${summary.state || stage.state}.`;
    result.whatHappened =
      stage.state === "SUCCEEDED"
        ? "A execução atingiu estado terminal com sucesso após percorrer as etapas evidenciadas."
        : stage.state === "NOT_REACHED"
          ? "A execução ainda não apresentou evidência de conclusão."
          : "A execução atingiu um estado terminal sem sucesso.";
    result.technicalDetails = compactDetails([
      ...details,
      { label: "Estado final", value: summary.state },
      { label: "Outcome técnico", value: summary.technicalStatus },
      { label: "Duração total", value: summary.durationMs, unit: "ms" },
      { label: "Tentativas", value: totalAttempts(input) },
      { label: "Retries", value: retries },
      { label: "Waits", value: countContinuity(stages, "wait") },
      { label: "Callbacks", value: countContinuity(stages, "callback") },
      { label: "Signals", value: countContinuity(stages, "signal") },
      { label: "Concluída em", value: summary.completedAt },
    ]);
    result.nextSteps =
      stage.state === "NOT_REACHED"
        ? "Acompanhar as próximas evidências desta execução."
        : "Não há etapas pendentes nesta execução.";
  } else if (stage.id === "wait") {
    const wait = sectionData(input.waitInfo) || {};
    result.summary = "A execução entrou em espera por continuidade externa.";
    result.whatHappened =
      "O processamento permanece suspenso até a chegada do callback ou signal correlacionado, ou até a expiração registrada.";
    result.technicalDetails = compactDetails([
      ...details,
      { label: "Estado da espera", value: wait.waitState },
      { label: "Tipo", value: wait.waitType },
      { label: "Expira em", value: wait.expiresAt },
      { label: "Definição do signal", value: wait.signalDefinitionRef },
    ]);
    result.nextSteps = "Aguardar callback ou signal correlacionado.";
  } else if (stage.id === "signal") {
    result.summary = "Um signal correlacionado participou da continuidade.";
    result.whatHappened = "O Data Plane registrou evidência operacional do signal desta execução.";
    result.nextSteps =
      stage.state === "SUCCEEDED" ? "Retomar ou concluir o processamento associado." : null;
  } else if (stage.id === "resume") {
    result.summary = "A execução foi retomada após a espera.";
    result.whatHappened = "Uma evidência operacional confirma que a continuidade foi liberada.";
    result.nextSteps = "Continuar o processamento a partir do ponto persistido.";
  } else if (stage.id === "callback") {
    const callback = sectionData(input.callback) || {};
    result.summary = "O callback participou da continuidade da execução.";
    result.whatHappened = "O read model expõe o estado seguro do callback associado.";
    result.technicalDetails = compactDetails([
      ...details,
      { label: "Estado do outbox", value: callback.outboxState },
      { label: "Confirmação", value: callback.confirmationState },
      { label: "Tentativas", value: callback.attemptCount },
      { label: "Próxima ação", value: callback.nextAction },
    ]);
  } else if (stage.id === "capacity") {
    result.summary = "Uma decisão real de capacidade afetou esta execução.";
    result.whatHappened =
      stage.state === "SUCCEEDED"
        ? "A admissão foi permitida pela política observada."
        : "A admissão foi adiada, rejeitada ou descartada conforme o evento operacional.";
    result.nextSteps =
      stage.state === "SUCCEEDED"
        ? "Prosseguir para o processamento."
        : "Aguardar nova elegibilidade ou revisar a política de capacidade aplicável.";
  } else if (stage.id === "worker") {
    result.summary = "O runtime de workers participou do processamento.";
    result.whatHappened = "Eventos operacionais de worker, schedule, claim ou fencing evidenciam esta etapa.";
  }
  return result;
}

export function projectJourneyStepDetail(stage, input = {}, stages = []) {
  const base = baseDetail(stage, input, stages);
  const summary = input.summary || {};
  const interaction = attemptContext(stage, input);
  const retry = retryContext(stage, input);

  if (interaction) {
    const { attempt, attempts, stepRef, number } = interaction;
    const failed = stage.state === "FAILED" || stage.state === "REJECTED";
    base.summary = failed
      ? `A tentativa ${number} da integração falhou.`
      : stage.state === "SUCCEEDED"
        ? `A tentativa ${number} da integração foi concluída com sucesso.`
        : `A tentativa ${number} da integração está em andamento.`;
    base.whatHappened =
      failed && isRetryDemo(summary)
        ? "Esta foi a primeira tentativa de integração com o mock alvo. O cenário RETRY_THEN_SUCCESS registrou uma falha transitória e retryable."
        : failed
          ? "A interação não foi concluída com sucesso. O painel apresenta somente o erro seguro persistido."
          : stage.state === "SUCCEEDED"
            ? "A interação com o alvo foi concluída e o resultado permitiu a continuidade da execução."
            : "A interação foi iniciada e ainda não apresentou resultado terminal.";
    base.technicalDetails = compactDetails([
      { label: "Execução", value: summary.executionId },
      { label: "Destino / rota", value: routeName(summary) },
      { label: "Passo", value: stepRef },
      { label: "Tentativa", value: `${number} de ${attempts.length || interaction.step?.attemptCount || number}` },
      { label: "Estado", value: attempt?.state || stage.state },
      { label: "Disposição", value: attempt?.disposition },
      { label: "Erro seguro", value: attempt?.safeErrorCode },
      { label: "Iniciada em", value: attempt?.startedAt },
      { label: "Concluída em", value: attempt?.completedAt },
      {
        label: "Duração",
        value:
          attempt?.startedAt && attempt?.completedAt
            ? Math.max(0, new Date(attempt.completedAt) - new Date(attempt.startedAt))
            : null,
        unit: "ms",
      },
    ]);
    const hasNext = attempts.some((item) => Number(item.attemptNumber) > number);
    base.nextSteps =
      failed && hasNext
        ? "A política de retry foi acionada e uma nova tentativa foi realizada."
        : failed
          ? "Não há nova tentativa evidenciada no read model."
          : "A execução segue para persistência e conclusão conforme o plano.";
  } else if (retry) {
    base.summary = `A falha da tentativa ${retry.number} acionou continuidade por retry.`;
    base.whatHappened =
      "A tentativa anterior terminou sem sucesso e a política aplicável permitiu uma nova tentativa. O backoff só seria exibido se estivesse presente no read model.";
    base.technicalDetails = compactDetails([
      { label: "Execução", value: summary.executionId },
      { label: "Destino / rota", value: routeName(summary) },
      { label: "Passo", value: retry.stepRef },
      { label: "Tentativa anterior", value: retry.number },
      { label: "Erro de origem", value: retry.previous?.safeErrorCode },
      { label: "Disposição anterior", value: retry.previous?.disposition },
      { label: "Próxima tentativa", value: retry.next?.attemptNumber },
      { label: "Estado da próxima", value: retry.next?.state },
    ]);
    base.nextSteps = retry.next
      ? `Executar a tentativa ${retry.next.attemptNumber} conforme a política aplicável.`
      : "Aguardar evidência da próxima tentativa.";
  }

  return {
    ...base,
    relatedEvents: relatedEvents(stage, input),
  };
}

export function chooseAutomaticJourneyStage(stages = [], executionState) {
  const continuity = [...stages].reverse().find((item) =>
    ["WAITING", "RETRYING", "DELAYED"].includes(item.state),
  );
  if (continuity) return continuity.id;
  const active = [...stages].reverse().find((item) => item.state === "ACTIVE");
  if (active) return active.id;
  if (EXECUTION_FAILURE_STATES.has(executionState)) {
    const failed = [...stages].reverse().find((item) =>
      item.id !== "completion" && ["FAILED", "REJECTED"].includes(item.state),
    );
    if (failed) return failed.id;
  }
  const completion = stages.find((item) => item.id === "completion" && item.state !== "NOT_REACHED");
  return completion?.id || stages[0]?.id || null;
}
