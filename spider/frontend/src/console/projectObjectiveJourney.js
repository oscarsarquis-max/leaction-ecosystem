/**
 * Projeção da Jornada do Objetivo a partir do read model contextual existente.
 * Não inventa progresso, route, adapter, target ou execução.
 */

export const OBJECTIVE_JOURNEY_PHASE_IDS = [
  "objective",
  "understanding",
  "policy",
  "plan",
  "capabilities",
  "resolution",
  "execution",
  "result",
];

export const OBJECTIVE_PHASE_MARKERS = {
  SUCCEEDED: "✓",
  ACCEPTED: "✓",
  READY: "✓",
  PARTIAL: "◐",
  PARTIALLY_AVAILABLE: "◐",
  MISSING_CONTEXT: "!",
  AMBIGUOUS: "?",
  NEEDS_INFORMATION: "!",
  NOT_EXECUTABLE: "○",
  POLICY_REJECTED: "✕",
  NOT_AUTHORIZED: "✕",
  REJECTED: "✕",
  FAILED: "✕",
  NOT_STARTED: "○",
  ACTIVE: "◉",
};

const PURPOSE_LABELS = {
  INVENTORY: "ESTOQUE",
  CASH_FLOW: "REFORÇO DE CAIXA",
  RAW_MATERIAL: "MATÉRIA-PRIMA",
  SEASONALITY: "SAZONALIDADE",
};

const CAPABILITY_LABELS = {
  IDENTIFY_CUSTOMER: "Identificar cliente",
  GET_CUSTOMER_PROFILE: "Consultar perfil do cliente",
  CHECK_CUSTOMER_REGISTRATION: "Verificar cadastro do cliente",
  GET_CREDIT_PROFILE: "Consultar perfil de crédito",
  FIND_ELIGIBLE_PRODUCTS: "Encontrar produtos elegíveis",
  SIMULATE_WORKING_CAPITAL: "Simular capital de giro",
  PRESENT_OPTIONS: "Apresentar opções",
  CREDIT_RELEASE_DIAGNOSTIC: "Diagnosticar liberação de crédito",
  COLLECTION_DIAGNOSTIC: "Diagnosticar cobrança pendente",
  BILLING_DIAGNOSTIC: "Diagnosticar faturamento",
  CUSTOMER_DATA_DIAGNOSTIC: "Diagnosticar dados cadastrais",
  SERVICE_REQUEST_DIAGNOSTIC: "Diagnosticar solicitação",
  INCIDENT_DIAGNOSTIC: "Diagnosticar incidente",
};

const TERMINAL_EXECUTION = new Set([
  "SUCCEEDED",
  "PARTIALLY_SUCCEEDED",
  "COMPENSATED",
  "FAILED",
  "TIMED_OUT",
  "REJECTED",
  "CANCELLED",
]);

function compact(details) {
  return details.filter(
    (item) => item.value !== null && item.value !== undefined && item.value !== "",
  );
}

export function purposeLabel(value) {
  return PURPOSE_LABELS[value] || value || "Não informada";
}

export function amountLabel(value) {
  if (value === null || value === undefined || value === "") return "Não informado";
  const parsed = Number(value);
  return Number.isFinite(parsed)
    ? parsed.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
    : String(value);
}

export function confidenceLabel(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? `${Math.round(parsed * 100)}%` : "—";
}

export function capabilityFriendlyName(capabilityId) {
  return CAPABILITY_LABELS[capabilityId] || capabilityId;
}

export function planStatusLabel(value) {
  const labels = {
    READY: "PRONTO",
    PARTIALLY_AVAILABLE: "PARCIALMENTE DISPONÍVEL",
    NOT_EXECUTABLE: "NÃO EXECUTÁVEL",
  };
  return labels[value] || value || "NÃO DETERMINADO";
}

export function operationLabel(constraints, intent) {
  if (intent === "SEEK_WORKING_CAPITAL") return "CONSULTA / SIMULAÇÃO";
  if (constraints?.readOnly === true && constraints?.mutationAllowed === false) {
    return "SOMENTE CONSULTA";
  }
  if (constraints?.mutationAllowed === true) return "MUTAÇÃO PERMITIDA";
  return "OPERAÇÃO RESTRITA";
}

export function domainLabel(catalog, domain) {
  return catalog?.items?.find((item) => item.domain === domain)?.domainLabel || domain || "—";
}

export function missingQuestion(key) {
  const questions = {
    proposalId: "Qual é o número da proposta?",
    collectionId: "Qual é o identificador da cobrança?",
    invoiceId: "Qual é o identificador do faturamento?",
    customerId: "Qual é o identificador do cliente?",
    serviceRequestId: "Qual é o número da solicitação?",
    incidentId: "Qual é o identificador do incidente?",
    purpose: "Qual é a finalidade empresarial do capital de giro?",
  };
  return questions[key] || `Informe o dado obrigatório: ${key}.`;
}

function provenanceSource(preview) {
  return preview?.intentContract?.provenance?.source || null;
}

function isNaturalLanguage(preview) {
  return provenanceSource(preview) === "NATURAL_LANGUAGE";
}

function interpretationStatusOf(preview) {
  return preview?.interpretationStatus || preview?.interpretation?.status || null;
}

function missingContextOf(preview) {
  return preview?.interpretation?.missingContext || [];
}

function candidateIntentsOf(preview) {
  return preview?.interpretation?.candidateIntents || [];
}

function executedCapabilityIds(preview, executionEvidence) {
  const executionId = executionEvidence?.executionId || preview?.executionId;
  if (!executionId) return new Set();
  const ids = new Set();
  const capabilityRef = preview?.route?.capabilityRef;
  if (capabilityRef) ids.add(capabilityRef);
  return ids;
}

function executionStateOf(preview, executionEvidence) {
  return executionEvidence?.executionState || preview?.executionState || null;
}

function capabilityRequired(plan, capability) {
  const step = plan?.steps?.find(
    (item) => item.stepId === capability.stepId || item.capabilityId === capability.capabilityId,
  );
  return step?.required !== false;
}

export function projectCapabilityVisual(capability, executedIds) {
  const capabilityId = capability?.capabilityId;
  if (capabilityId && executedIds.has(capabilityId)) {
    return { kind: "executed", marker: "✓", label: "EXECUTADA" };
  }
  if (capability?.status === "RESOLVED" && capability?.availability === "AVAILABLE") {
    return { kind: "available", marker: "◉", label: "DISPONÍVEL" };
  }
  return { kind: "required", marker: "○", label: "NECESSÁRIA" };
}

export function projectCapabilityResolution(capability) {
  const resolved =
    capability?.status === "RESOLVED" && capability?.availability === "AVAILABLE";
  const route = capability?.selectedRoute;
  if (resolved && route?.routeRef) {
    return {
      capabilityId: capability.capabilityId,
      routeRef: route.routeRef,
      adapterRef: route.adapterRef || null,
      target: route.targetOperation || null,
      available: true,
      executor: [route.adapterRef, route.targetOperation].filter(Boolean).join(" · ") || route.routeRef,
    };
  }
  return {
    capabilityId: capability.capabilityId,
    routeRef: route?.routeRef || "NO_ELIGIBLE_ROUTE",
    adapterRef: route?.adapterRef || null,
    target: "NOT_AVAILABLE",
    available: false,
    executor: "Não disponível",
  };
}

function phase(id, title, status, summary, result) {
  return {
    id,
    title,
    status,
    summary,
    result,
    marker: OBJECTIVE_PHASE_MARKERS[status] || "○",
    started: status !== "NOT_STARTED",
  };
}

function relatedFromJourney(preview, ids) {
  const journey = preview?.contextJourney || [];
  return journey
    .filter((item) => ids.includes(item.id) || ids.some((id) => String(item.id || "").startsWith(id)))
    .map((item) => ({
      id: `journey-${item.id}`,
      eventType: item.id,
      source: item.layer || "CONTEXT",
      outcome: item.state,
      occurredAt: item.occurredAt,
      title: item.title,
    }));
}

function relatedFromOperational(operationalEvents, types) {
  return (operationalEvents || [])
    .filter((event) => {
      const type = String(event.eventType || "");
      return types.some((prefix) => type === prefix || type.startsWith(prefix));
    })
    .map((event) => ({
      id: `operational-${event.eventId || event.eventType}-${event.occurredAt || ""}`,
      eventType: event.eventType,
      source: event.source || "OPERATIONAL_EVENT",
      outcome: event.outcome,
      occurredAt: event.occurredAt,
    }));
}

function buildResult(preview, plan, capabilities, executedIds, executionEvidence) {
  const decision = preview?.decision;
  const interpretationStatus = interpretationStatusOf(preview);
  const missing = missingContextOf(preview);
  const candidates = candidateIntentsOf(preview);
  const executedCount = executedIds.size;
  const resolvedCount = capabilities.filter((item) => item.status === "RESOLVED").length;
  const unavailable = capabilities.filter((item) => item.status !== "RESOLVED");
  const understood = Boolean(preview?.intentContract?.intent);
  const planSelected = Boolean(plan?.planId);
  const executionId = executionEvidence?.executionId || preview?.executionId || null;
  const executionState = executionStateOf(preview, executionEvidence);

  const achieved = [];
  const pending = [];
  if (understood) achieved.push("compreender o objetivo");
  if (planSelected) achieved.push("selecionar o plano");
  if (resolvedCount > 0) {
    achieved.push(
      `resolver ${resolvedCount} ${resolvedCount === 1 ? "capability" : "capabilities"}`,
    );
  }
  if (executedCount > 0) {
    achieved.push(
      `executar ${executedCount} ${executedCount === 1 ? "capability" : "capabilities"}`,
    );
  } else if (planSelected) {
    pending.push("execução no Data Plane");
  }
  unavailable.forEach((item) => pending.push(capabilityFriendlyName(item.capabilityId)));

  if (interpretationStatus === "AMBIGUOUS" || decision === "AMBIGUOUS") {
    return {
      status: "AMBIGUOUS",
      conclusion: "OBJETIVO AMBÍGUO",
      achieved,
      pending: candidates.length
        ? candidates.map((intent) => `alternativa: ${intent}`)
        : ["esclarecer o objetivo"],
      missing: [],
      candidates,
      executionId: null,
      executionState: null,
    };
  }
  if (decision === "MISSING_CONTEXT" || interpretationStatus === "MISSING_CONTEXT") {
    return {
      status: "NEEDS_INFORMATION",
      conclusion: "PRECISA DE INFORMAÇÃO",
      achieved,
      pending: missing.map(missingQuestion),
      missing,
      candidates: [],
      executionId: null,
      executionState: null,
    };
  }
  if (decision === "NOT_AUTHORIZED" || decision === "POLICY_REJECTED" || decision === "REJECTED") {
    return {
      status: decision,
      conclusion: "POLÍTICA REJEITOU",
      achieved,
      pending: ["revisar autorização ou política"],
      missing,
      candidates: [],
      executionId: null,
      executionState: null,
    };
  }
  if (!planSelected) {
    return {
      status: "NOT_STARTED",
      conclusion: "PLANO NÃO INICIADO",
      achieved,
      pending: pending.length ? pending : ["determinar plano"],
      missing,
      candidates,
      executionId: null,
      executionState: null,
    };
  }
  if (plan.status === "NOT_EXECUTABLE") {
    return {
      status: "NOT_EXECUTABLE",
      conclusion: "PLANO NÃO EXECUTÁVEL",
      achieved,
      pending,
      missing: [],
      candidates: [],
      executionId: null,
      executionState: null,
    };
  }
  if (plan.status === "PARTIALLY_AVAILABLE") {
    return {
      status: "PARTIAL",
      conclusion: "PLANO PARCIALMENTE DISPONÍVEL",
      achieved,
      pending,
      missing: [],
      candidates: [],
      executionId,
      executionState,
    };
  }
  if (executionId && executionState === "SUCCEEDED") {
    return {
      status: "SUCCEEDED",
      conclusion: "SUCCEEDED",
      achieved,
      pending,
      missing: [],
      candidates: [],
      executionId,
      executionState,
      durationMs: executionEvidence?.durationMs || null,
      outcome: executionEvidence?.outcome || executionState,
    };
  }
  if (executionId && TERMINAL_EXECUTION.has(executionState)) {
    return {
      status: executionState,
      conclusion: executionState,
      achieved,
      pending,
      missing: [],
      candidates: [],
      executionId,
      executionState,
      durationMs: executionEvidence?.durationMs || null,
      outcome: executionEvidence?.outcome || executionState,
    };
  }
  return {
    status: plan.status === "READY" ? "READY" : plan.status || "NOT_STARTED",
    conclusion: plan.status === "READY" ? "PLANO PRONTO" : planStatusLabel(plan.status),
    achieved,
    pending: executionId ? pending : [...pending.filter((item) => item !== "execução no Data Plane"), "confirmação para executar"],
    missing: [],
    candidates: [],
    executionId,
    executionState,
  };
}

function interruptedAfter(preview) {
  const decision = preview?.decision;
  const interpretationStatus = interpretationStatusOf(preview);
  if (interpretationStatus === "AMBIGUOUS" || decision === "AMBIGUOUS") return "understanding";
  if (decision === "MISSING_CONTEXT" || interpretationStatus === "MISSING_CONTEXT") return "policy";
  if (decision === "NOT_AUTHORIZED" || decision === "POLICY_REJECTED" || decision === "REJECTED") {
    return "policy";
  }
  return null;
}

export function projectObjectiveJourney(input = {}) {
  const preview = input.preview || null;
  const catalog = input.catalog || null;
  const executionEvidence = input.executionEvidence || null;
  const operationalEvents = input.operationalEvents || [];
  if (!preview) return null;

  const contract = preview.intentContract || null;
  const plan = preview.executionPlan || null;
  const capabilities = (preview.capabilities || []).map((capability) => ({
    ...capability,
    required: capabilityRequired(plan, capability),
    friendlyName: capabilityFriendlyName(capability.capabilityId),
    visual: null,
    resolution: projectCapabilityResolution(capability),
  }));
  const executedIds = executedCapabilityIds(preview, executionEvidence);
  capabilities.forEach((capability) => {
    capability.visual = projectCapabilityVisual(capability, executedIds);
  });
  const result = buildResult(preview, plan, capabilities, executedIds, executionEvidence);
  const interrupt = interruptedAfter(preview);
  const laterStarted = !interrupt;
  const timestamp =
    preview.createdAt || preview.interpretation?.interpretedAt || null;
  const entities = contract?.entities || {};
  const naturalLanguage = isNaturalLanguage(preview) || Boolean(preview.requestedObjective && preview.interpretation);
  const usedAi =
    provenanceSource(preview) !== "BUSINESS_CARD" &&
    Boolean(preview.interpretation) &&
    (isNaturalLanguage(preview) || Boolean(preview.requestedObjective));
  const missing = missingContextOf(preview);
  const candidates = candidateIntentsOf(preview);
  const policyDecision = preview.decision || interpretationStatusOf(preview) || "NOT_STARTED";
  const contextSufficient =
    Boolean(contract?.intent) && missing.length === 0 && policyDecision === "ACCEPTED";
  const mutationAllowed = contract?.constraints?.mutationAllowed === true;
  const resolvedCount = capabilities.filter((item) => item.status === "RESOLVED").length;
  const availableCount = resolvedCount;
  const unavailableCount = capabilities.filter((item) => item.status !== "RESOLVED").length;
  const executedCount = capabilities.filter((item) => item.visual.kind === "executed").length;
  const executionId = executionEvidence?.executionId || preview.executionId || null;

  const objectiveText =
    preview.requestedObjective ||
    catalog?.items?.find((item) => item.intent === contract?.intent)?.description ||
    contract?.objective ||
    "—";

  const understandingStatus = interrupt === "understanding"
    ? "AMBIGUOUS"
    : contract?.intent
      ? "SUCCEEDED"
      : interpretationStatusOf(preview) || "NOT_STARTED";

  const policyStatus = !laterStarted && interrupt === "understanding"
    ? "NOT_STARTED"
    : interrupt === "policy"
      ? policyDecision
      : policyDecision === "ACCEPTED"
        ? "SUCCEEDED"
        : policyDecision || "NOT_STARTED";

  const planStatus = laterStarted && plan?.planId ? plan.status || "SUCCEEDED" : "NOT_STARTED";
  const capabilitiesStatus = laterStarted && capabilities.length > 0 ? planStatus : "NOT_STARTED";
  const resolutionStatus = laterStarted && capabilities.length > 0 ? planStatus : "NOT_STARTED";
  const executionStatus = laterStarted
    ? executedCount > 0
      ? executionStateOf(preview, executionEvidence) === "SUCCEEDED"
        ? "SUCCEEDED"
        : executionStateOf(preview, executionEvidence) || "SUCCEEDED"
      : executionId
        ? executionStateOf(preview, executionEvidence) || "ACTIVE"
        : "NOT_STARTED"
    : "NOT_STARTED";

  const phases = [
    phase(
      "objective",
      "OBJETIVO",
      objectiveText && objectiveText !== "—" ? "SUCCEEDED" : "NOT_STARTED",
      [objectiveText, provenanceSource(preview)].filter(Boolean).join(" · "),
      amountLabel(entities.amount) !== "Não informado"
        ? amountLabel(entities.amount)
        : "Declaração recebida",
    ),
    phase(
      "understanding",
      "ENTENDIMENTO",
      understandingStatus,
      contract?.intent
        ? [
            contract.intent,
            entities.purpose ? purposeLabel(entities.purpose) : null,
            confidenceLabel(contract.confidence),
          ]
            .filter(Boolean)
            .join(" · ")
        : preview.interpretationMessage || "Sem intent reconhecido",
      contract
        ? [domainLabel(catalog, contract.domain), understandingStatus].filter(Boolean).join(" · ")
        : understandingStatus,
    ),
    phase(
      "policy",
      "POLICY",
      policyStatus,
      policyStatus === "NOT_STARTED"
        ? "Não iniciada"
        : [policyDecision, preview.policyRef, contract ? operationLabel(contract.constraints, contract.intent) : null]
            .filter(Boolean)
            .join(" · "),
      policyStatus === "NOT_STARTED"
        ? "Aguardando entendimento"
        : [
            contextSufficient ? "SUFFICIENT" : missing.length ? "MISSING_CONTEXT" : "INSUFFICIENT",
            mutationAllowed ? "MUTATION_ALLOWED" : "NOT_ALLOWED",
            preview.policyRef,
          ]
            .filter(Boolean)
            .join(" · "),
    ),
    phase(
      "plan",
      "PLANO",
      planStatus,
      plan?.planType
        ? `${plan.planType} · ${planStatusLabel(plan.status)}`
        : "Não determinado",
      plan
        ? `${planStatusLabel(plan.status)} · ${capabilities.length} capabilities`
        : "NOT_STARTED",
    ),
    phase(
      "capabilities",
      "CAPACIDADES",
      capabilitiesStatus,
      capabilities.length
        ? `${capabilities.length} necessárias · ${resolvedCount} disponíveis · ${executedCount} executadas`
        : "Não iniciadas",
      capabilitiesStatus === "NOT_STARTED" ? "NOT_STARTED" : `${unavailableCount} indisponíveis`,
    ),
    phase(
      "resolution",
      "RESOLUÇÃO",
      resolutionStatus,
      resolutionStatus === "NOT_STARTED"
        ? "Não iniciada"
        : `${resolvedCount} com executor · ${unavailableCount} sem executor`,
      resolutionStatus === "NOT_STARTED" ? "NOT_STARTED" : "Capability → Route → Adapter → Target",
    ),
    phase(
      "execution",
      "EXECUÇÃO",
      executionStatus,
      executedCount > 0
        ? `${executedCount} capability(s) no Data Plane`
        : "Nenhuma capability executada",
      executionId || "Sem execução",
    ),
    phase("result", "RESULTADO", result.status, result.conclusion, result.achieved.join("; ") || result.status),
  ];

  return {
    decisionId: preview.decisionId || null,
    intent: contract?.intent || null,
    planId: plan?.planId || null,
    executionId,
    provenance: provenanceSource(preview),
    usedAi,
    naturalLanguage,
    timestamp,
    objectiveText,
    contract,
    plan,
    capabilities,
    availableCount,
    resolvedCount,
    unavailableCount,
    executedCount,
    executedIds: [...executedIds],
    result,
    interrupt,
    missing,
    candidates,
    policyDecision,
    policyRef: preview.policyRef || null,
    contextSufficient,
    mutationAllowed,
    interpretation: usedAi
      ? {
          provider: preview.interpretation?.provider || null,
          model: preview.interpretation?.model || null,
          promptVersion: preview.interpretation?.promptVersion || null,
          interpretedAt: preview.interpretation?.interpretedAt || null,
        }
      : null,
    phases,
    events: {
      objective: [
        ...relatedFromJourney(preview, ["objective-received", "objective-selected"]),
        ...relatedFromOperational(operationalEvents, ["INTENT_CREATED"]),
      ],
      understanding: [
        ...relatedFromJourney(preview, ["ai-interpreted", "intent-created"]),
        ...relatedFromOperational(operationalEvents, ["AI_INTERPRETATION", "INTENT_CREATED"]),
      ],
      policy: [
        ...relatedFromJourney(preview, ["policy-validated"]),
        ...relatedFromOperational(operationalEvents, ["INTENT_VALIDATED", "POLICY"]),
      ],
      plan: [
        ...relatedFromJourney(preview, ["execution-plan-resolved", "execution-plan-rejected"]),
        ...relatedFromOperational(operationalEvents, ["EXECUTION_PLAN"]),
      ],
      capabilities: [
        ...relatedFromJourney(preview, ["capabilities-resolved", "plan-capability-"]),
        ...relatedFromOperational(operationalEvents, ["CAPABILITY_"]),
      ],
      resolution: [
        ...relatedFromJourney(preview, ["route-resolved", "plan-capability-"]),
        ...relatedFromOperational(operationalEvents, ["ROUTE_RESOLVED", "CAPABILITY_"]),
      ],
      execution: [
        ...relatedFromOperational(operationalEvents, ["EXECUTION_", "INTERACTION", "ATTEMPT"]),
      ],
      result: [
        ...relatedFromOperational(operationalEvents, ["EXECUTION_SUCCEEDED", "EXECUTION_FAILED"]),
      ],
    },
    correlation: compact([
      { label: "decisionId", value: preview.decisionId },
      { label: "intent", value: contract?.intent },
      { label: "planId", value: plan?.planId },
      { label: "executionId", value: executionId },
      { label: "interactionId", value: executionEvidence?.interactionId || null },
    ]),
  };
}

function catalogTitle(catalog, intent) {
  return catalog?.items?.find((item) => item.intent === intent)?.title || intent;
}

export function projectObjectivePhaseDetail(phaseId, projection, catalog) {
  if (!projection) return null;
  const phase = projection.phases.find((item) => item.id === phaseId);
  if (!phase) return null;
  const contract = projection.contract;
  const plan = projection.plan;
  const previewEntities = contract?.entities || {};
  const relatedEvents = projection.events[phaseId] || [];
  const base = {
    phaseId,
    title: phase.title,
    status: phase.status,
    summary: phase.summary,
    result: phase.result,
    whatHappened: "",
    decision: "",
    data: [],
    nextSteps: "",
    relatedEvents,
    usedAi: false,
  };

  if (phaseId === "objective") {
    base.whatHappened = "O usuário declarou um objetivo. A interface projeta a declaração original, a origem e os dados explícitos.";
    base.decision = "Nenhuma decisão de planejamento ou execução ocorreu nesta fase.";
    base.data = compact([
      { label: "Declaração", value: projection.objectiveText },
      { label: "Origem", value: projection.provenance },
      { label: "Timestamp", value: projection.timestamp },
      { label: "Finalidade", value: previewEntities.purpose ? purposeLabel(previewEntities.purpose) : null },
      { label: "Valor", value: previewEntities.amount ? amountLabel(previewEntities.amount) : null },
      { label: "Situação empresarial", value: previewEntities.businessSituation || null },
      { label: "decisionId", value: projection.decisionId },
    ]);
    base.nextSteps = "Interpretar o objetivo no vocabulário controlado.";
    return base;
  }

  if (phaseId === "understanding") {
    base.usedAi = projection.usedAi;
    base.whatHappened = projection.usedAi
      ? "A IA interpretou a linguagem natural e produziu somente um Intent Contract estruturado."
      : projection.provenance === "BUSINESS_CARD"
        ? "A situação frequente materializou o Intent Contract sem interpretação por IA."
        : "O entendimento usou somente o contrato já disponível.";
    base.decision =
      projection.interrupt === "understanding"
        ? "O entendimento está ambíguo. Nenhum plano foi gerado."
        : contract?.intent
          ? `Intent reconhecido: ${contract.intent}.`
          : "Nenhum intent foi reconhecido.";
    base.data = compact([
      { label: "Intent", value: contract?.intent },
      { label: "Domínio", value: domainLabel(catalog, contract?.domain) },
      { label: "Finalidade", value: previewEntities.purpose ? purposeLabel(previewEntities.purpose) : null },
      { label: "Valor", value: previewEntities.amount ? amountLabel(previewEntities.amount) : null },
      { label: "Confiança", value: contract ? confidenceLabel(contract.confidence) : null },
      { label: "Status", value: phase.status },
      { label: "IA nesta fase", value: projection.usedAi ? "sim" : "não" },
      { label: "Provider", value: projection.usedAi ? projection.interpretation?.provider : null },
      { label: "Modelo", value: projection.usedAi ? projection.interpretation?.model : null },
    ]);
    if (projection.interrupt === "understanding") {
      base.data.push(
        ...projection.candidates.map((intent) => ({
          label: "Alternativa",
          value: catalogTitle(catalog, intent),
        })),
      );
      base.nextSteps = "Escolher uma das alternativas permitidas. Plano, capabilities e execução não iniciam.";
    } else {
      base.nextSteps = "Aplicar o Context Guard ao Intent Contract.";
    }
    return base;
  }

  if (phaseId === "policy") {
    base.whatHappened = "O Context Guard avaliou o Intent Contract. A decisão é determinística e anterior ao Plan Resolver.";
    base.decision = `CONTEXT GUARD ${projection.policyDecision}`;
    base.data = compact([
      { label: "Context", value: projection.contextSufficient ? "SUFFICIENT" : projection.missing.length ? "MISSING_CONTEXT" : "INSUFFICIENT" },
      { label: "Mutation", value: projection.mutationAllowed ? "ALLOWED" : "NOT_ALLOWED" },
      { label: "Policy", value: projection.policyDecision },
      { label: "Policy ref", value: projection.policyRef },
      { label: "Operação", value: contract ? operationLabel(contract.constraints, contract.intent) : null },
    ]);
    if (projection.missing.length) {
      base.data.push(
        ...projection.missing.map((key) => ({ label: "Informação ausente", value: missingQuestion(key) })),
      );
      base.nextSteps = "Informar o dado ausente. Plano e execução permanecem NOT_STARTED.";
    } else if (phase.status === "NOT_STARTED") {
      base.nextSteps = "Aguardar um entendimento aceito.";
    } else {
      base.nextSteps = "Determinar o Execution Plan.";
    }
    return base;
  }

  if (phaseId === "plan") {
    base.whatHappened =
      "O Plan Resolver determinístico selecionou o Execution Plan a partir do Intent Contract aceito. A IA não participa desta fase.";
    base.decision = plan ? `${plan.planType} · ${plan.status}` : "Plano não determinado.";
    base.data = compact([
      { label: "planType", value: plan?.planType },
      { label: "Status", value: plan?.status },
      { label: "planId", value: plan?.planId },
      { label: "Versão", value: plan?.schemaVersion },
      { label: "Capabilities", value: plan ? String(plan.steps?.length || 0) : null },
      { label: "Disponíveis", value: plan ? String(projection.resolvedCount) : null },
      { label: "Indisponíveis", value: plan ? String(projection.unavailableCount) : null },
      { label: "Motivos", value: plan?.statusReasons?.join(" · ") || null },
    ]);
    base.nextSteps =
      plan?.status === "READY"
        ? "Resolver capabilities e, se o plano estiver integralmente executável, confirmar a execução."
        : plan
          ? "Exibir disponibilidade real. Capabilities indisponíveis não serão executadas."
          : "Nenhum plano a resolver.";
    return base;
  }

  if (phaseId === "capabilities") {
    base.whatHappened =
      "O plano foi decomposto nas Business Capabilities necessárias. Necessária, disponível e executada são estados distintos.";
    base.decision = `${projection.resolvedCount} disponíveis de ${projection.capabilities.length} necessárias; ${projection.executedCount} executadas.`;
    base.data = projection.capabilities.map((capability) => ({
      label: capability.capabilityId,
      value: `${capability.visual.label}${capability.required ? " · obrigatória" : " · opcional"}`,
    }));
    base.nextSteps = "Selecionar uma capability para ver resolução e evidência.";
    return base;
  }

  if (phaseId === "resolution") {
    base.whatHappened =
      "O Capability Resolver determinístico liga cada capability a route, adapter e target reais, ou declara indisponibilidade. A IA não participa.";
    base.decision = "A resolução vem do catálogo e do ambiente; nada é inventado na interface.";
    base.data = projection.capabilities.map((capability) => ({
      label: capability.capabilityId,
      value: capability.resolution.available
        ? `${capability.resolution.routeRef} → ${capability.resolution.executor}`
        : `${capability.resolution.routeRef} → ${capability.resolution.target}`,
    }));
    base.nextSteps = projection.executedCount
      ? "Navegar à Execution Journey do Data Plane para a capability executada."
      : "Executar somente o que estiver realmente disponível e integralmente executável.";
    return base;
  }

  if (phaseId === "execution") {
    base.whatHappened =
      "PLAN JOURNEY explica o que precisa ser feito. DATA PLANE JOURNEY explica como foi executado. Somente capabilities realmente executadas aparecem aqui.";
    base.decision = projection.executionId
      ? `Execução correlacionada ${projection.executionId}.`
      : "Nenhuma execução foi iniciada.";
    base.data = compact([
      { label: "executionId", value: projection.executionId },
      { label: "Estado", value: projection.result.executionState },
      { label: "Capabilities executadas", value: String(projection.executedCount) },
      { label: "Duração", value: projection.result.durationMs, unit: projection.result.durationMs ? "ms" : null },
    ]);
    base.nextSteps = projection.executionId
      ? "Abrir a Execution Journey 020B para Solicitação, Contrato, Engine, Interaction, Retry, Wait, Persistência e Conclusão."
      : "Sem Data Plane enquanto o plano não for integralmente executável e confirmado.";
    return base;
  }

  base.whatHappened =
    "O resultado é determinístico e derivado dos estados reais. Não há Response Composer por IA.";
  base.decision = projection.result.conclusion;
  base.data = compact([
    { label: "Conclusão", value: projection.result.conclusion },
    { label: "Status", value: projection.result.status },
    { label: "Conseguiu", value: projection.result.achieved.map((item) => `✓ ${item}`).join(" · ") || "—" },
    { label: "Ainda não disponível", value: projection.result.pending.map((item) => `○ ${item}`).join(" · ") || "—" },
    { label: "executionId", value: projection.result.executionId },
    { label: "Outcome", value: projection.result.outcome },
    { label: "Duração", value: projection.result.durationMs, unit: projection.result.durationMs ? "ms" : null },
  ]);
  base.nextSteps =
    projection.result.status === "NEEDS_INFORMATION"
      ? "Informar o contexto ausente."
      : projection.result.status === "AMBIGUOUS"
        ? "Escolher uma alternativa do catálogo."
        : projection.result.status === "PARTIAL" || projection.result.status === "NOT_EXECUTABLE"
          ? "Não tratar plano parcial como completo."
          : "Consultar a Execution Journey quando houver execução.";
  return base;
}

export function projectObjectiveCapabilityDetail(capability, projection, executionEvidence) {
  if (!capability) return null;
  const resolution = capability.resolution;
  const executed = capability.visual?.kind === "executed";
  const relatedEvents = (projection?.events?.capabilities || []).filter(
    (event) =>
      String(event.eventType || "").includes(capability.capabilityId) ||
      String(event.eventType || "").includes(capability.stepId || ""),
  );
  return {
    capabilityId: capability.capabilityId,
    friendlyName: capability.friendlyName,
    description: capability.description,
    reason: capability.reason,
    inputContract: capability.inputContract,
    outputContract: capability.outputContract,
    required: capability.required,
    availability: capability.availability,
    resolutionStatus: capability.status,
    executionStatus: executed
      ? executionEvidence?.executionState || projection?.result?.executionState || "EXECUTED"
      : "NOT_EXECUTED",
    visual: capability.visual,
    routeRef: resolution.routeRef,
    adapterRef: resolution.adapterRef,
    target: resolution.target,
    executor: resolution.executor,
    available: resolution.available,
    executionId: executed ? projection?.executionId : null,
    relatedEvents,
    whatHappened: executed
      ? "Esta capability necessária estava disponível e foi efetivamente executada no Data Plane."
      : resolution.available
        ? "Esta capability é necessária e está disponível, mas ainda não foi executada."
        : "Esta capability é necessária ao plano, porém não há executor elegível no ambiente atual.",
    decision: resolution.available
      ? `${resolution.routeRef} → ${resolution.executor}`
      : "NO_ELIGIBLE_ROUTE → NOT_AVAILABLE",
    nextSteps: executed
      ? "Abrir a Data Plane Journey correspondente."
      : resolution.available
        ? "A execução só ocorre se o plano integral estiver READY e for confirmado."
        : "Não simular nem marcar como executada.",
  };
}
