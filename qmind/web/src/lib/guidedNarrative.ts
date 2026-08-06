/**
 * Método consultivo do Wizard — abertura, fechamento e revisão final.
 * Linguagem de negócio; sem julgamento automático de conformidade.
 */
import type {
  AnswerValue,
  GuidedAnswer,
  GuidedClauseGroup,
  GuidedContext,
  GuidedQuestion,
  GuidedSession,
} from "@/api/guidedTypes";
import { CLAUSE_NAV_ORDER, clauseMajor } from "@/lib/guidedShowWhen";

/** Rótulos neutros — nunca “conforme” / “não conforme”. */
export type NeutralTag =
  | "Prática informada"
  | "Ponto consistente"
  | "Precisa de esclarecimento"
  | "Evidência pendente"
  | "Atenção recomendada"
  | "Revisão do consultor";

export type ConsultiveOpening = {
  major: string;
  businessName: string;
  whatIsEvaluated: string;
  objective: string;
  whyItMatters: string;
  expectedBenefits: string[];
  problemsAvoided: string[];
  expectedResult: string;
};

export type NarrativeItem = {
  questionId: string;
  theme: string;
  question: string;
  tags: NeutralTag[];
  answerValue: AnswerValue | null;
  description: string;
  naJustification: string;
  evidenceNote: string;
  evidenceCount: number;
  evidenceAwaitingUpload?: number;
  evidenceProcessing?: number;
  evidenceApproved?: number;
  evidenceRejected?: number;
  provideLater: boolean;
};

export type ClauseStageStats = {
  answered: number;
  applicable: number;
  evidenceCount: number;
  pending: number;
  reviewPoints: number;
};

export type ClauseNarrative = {
  major: string;
  businessName: string;
  objective: string;
  whatCompanyInformed: string;
  applicable: number;
  answered: number;
  pending: number;
  stats: ClauseStageStats;
  informedPractices: NarrativeItem[];
  linkedOrDescribedEvidence: NarrativeItem[];
  promisedEvidence: NarrativeItem[];
  partialAnswers: NarrativeItem[];
  negativeAnswers: NarrativeItem[];
  unknownAnswers: NarrativeItem[];
  notApplicable: NarrativeItem[];
  clarificationPoints: NarrativeItem[];
  strengtheningOpportunities: string[];
  possibleBusinessImpacts: string[];
  nextClauseMajor: string | null;
  nextClauseLabel: string | null;
};

export type BusinessJourneyStep = {
  order: number;
  major: string;
  title: string;
  answered: number;
  applicable: number;
};

export type FinalReviewModel = {
  profileLines: { label: string; value: string }[];
  scopeLines: { label: string; value: string }[];
  products: string[];
  sites: string[];
  processes: string[];
  stakeholders: string[];
  businessJourney: BusinessJourneyStep[];
  answeredCount: number;
  applicableCount: number;
  evidenceAvailableCount: number;
  evidencePendingCount: number;
  evidenceRelatedCount: number;
  evidenceAwaitingUploadCount: number;
  evidenceProcessingCount: number;
  evidenceApprovedCount: number;
  evidenceRejectedCount: number;
  evidencePromisedLaterCount: number;
  unknownCount: number;
  deepeningThemes: NarrativeItem[];
  pendingEvidenceItems: NarrativeItem[];
  nextSteps: string[];
  clauses: ClauseNarrative[];
};

export const CONSULTIVE_OPENINGS: Record<string, ConsultiveOpening> = {
  "4": {
    major: "4",
    businessName: "Compreender a organização",
    whatIsEvaluated:
      "Se a empresa entende seu contexto, partes interessadas, escopo e processos.",
    objective:
      "Estabelecer uma visão clara de como a organização funciona e do que influencia sua capacidade de entregar qualidade.",
    whyItMatters:
      "Sem esse mapa, decisões de qualidade ficam soltas e o time discute sintomas em vez de causas.",
    expectedBenefits: [
      "Menos pontos cegos",
      "Processos e responsabilidades mais claros",
      "Escopo coerente",
      "Melhor compreensão de clientes e outras partes relevantes",
    ],
    problemsAvoided: [
      "Escopo confuso ou incompleto",
      "Processos sem dono",
      "Surpresas com exigências de clientes ou órgãos",
    ],
    expectedResult:
      "Um retrato útil da organização — o suficiente para conduzir a avaliação com foco no negócio.",
  },
  "5": {
    major: "5",
    businessName: "Liderança e direção",
    whatIsEvaluated:
      "Como a liderança conduz a qualidade, mantém foco no cliente e distribui responsabilidades.",
    objective:
      "Fazer da qualidade uma responsabilidade da gestão, não apenas de uma área isolada.",
    whyItMatters:
      "Sem apoio da direção, práticas de qualidade viram esforço local e perdem força no dia a dia.",
    expectedBenefits: [
      "Decisões mais alinhadas",
      "Responsabilidades claras",
      "Maior foco no cliente",
      "Apoio efetivo da direção",
    ],
    problemsAvoided: [
      "Política só no papel",
      "Papéis ambíguos",
      "Qualidade tratada como ‘problema do departamento’",
    ],
    expectedResult:
      "Clareza sobre como a direção orienta a qualidade e quem responde pelo quê.",
  },
  "6": {
    major: "6",
    businessName: "Planejar resultados",
    whatIsEvaluated: "Riscos, oportunidades, objetivos e mudanças.",
    objective:
      "Transformar intenções em prioridades, responsáveis, prazos e ações acompanháveis.",
    whyItMatters:
      "Planejar mal gera surpresa operacional; planejar bem direciona energia ao que importa.",
    expectedBenefits: [
      "Menos surpresas",
      "Prevenção de problemas",
      "Objetivos mensuráveis",
      "Mudanças mais controladas",
      "Recursos direcionados ao que realmente importa",
    ],
    problemsAvoided: [
      "Metas genéricas sem plano",
      "Riscos conhecidos e ignorados",
      "Mudanças feitas no improviso",
    ],
    expectedResult:
      "Prioridades e tratamentos claros — o que prevenir, o que melhorar e quem acompanha.",
  },
  "7": {
    major: "7",
    businessName: "Criar capacidade para entregar",
    whatIsEvaluated:
      "Pessoas, competências, infraestrutura, conhecimento, comunicação, medição e informação documentada.",
    objective:
      "Verificar se a organização possui condições reais para executar o que planejou.",
    whyItMatters:
      "Sem capacidade, o plano fica no discurso e a operação carrega o risco sozinha.",
    expectedBenefits: [
      "Menos dependência de conhecimento informal",
      "Pessoas mais preparadas",
      "Equipamentos e infraestrutura adequados",
      "Comunicação mais clara",
      "Informações confiáveis e atualizadas",
      "Maior consistência operacional",
    ],
    problemsAvoided: [
      "Erros por versão errada de documento",
      "Funções críticas sem treino",
      "Medições pouco confiáveis",
    ],
    expectedResult:
      "Um quadro honesto da capacidade atual para sustentar a entrega com qualidade.",
  },
  "8": {
    major: "8",
    businessName: "Entregar ao cliente com controle",
    whatIsEvaluated:
      "Como requisitos são entendidos e como produtos ou serviços são planejados, executados, verificados e entregues.",
    objective:
      "Assegurar que a operação transforme requisitos do cliente em entregas controladas e confiáveis.",
    whyItMatters:
      "É nesta etapa que o cliente sente a qualidade — ou o retrabalho.",
    expectedBenefits: [
      "Menos erros e retrabalho",
      "Pedidos mais bem compreendidos",
      "Fornecedores mais controlados",
      "Alterações mais seguras",
      "Problemas identificados antes da entrega",
      "Maior previsibilidade para o cliente",
    ],
    problemsAvoided: [
      "Aceitar pedido mal entendido",
      "Liberar entrega sem critério",
      "Problemas que só aparecem no cliente",
    ],
    expectedResult:
      "Uma leitura da operação do pedido à entrega — o que está sob controle e o que merece atenção.",
  },
  "9": {
    major: "9",
    businessName: "Medir, analisar e decidir",
    whatIsEvaluated:
      "Indicadores, satisfação do cliente, avaliação interna e análise da direção.",
    objective:
      "Permitir que a empresa tome decisões baseadas em resultados e identifique desvios antes que se agravem.",
    whyItMatters:
      "Sem medição útil, a gestão opera no escuro e reage tarde.",
    expectedBenefits: [
      "Decisões apoiadas por dados",
      "Problemas detectados mais cedo",
      "Melhor entendimento da satisfação do cliente",
      "Avaliações internas mais úteis",
      "Direção consciente dos resultados e prioridades",
    ],
    problemsAvoided: [
      "Indicadores que ninguém usa",
      "Feedback do cliente arquivado sem ação",
      "Análise da direção só formal",
    ],
    expectedResult:
      "Clareza sobre como a empresa enxerga desempenho e decide o que mudar.",
  },
  "10": {
    major: "10",
    businessName: "Corrigir e melhorar",
    whatIsEvaluated:
      "Como a empresa reage a problemas, investiga causas, evita recorrências e promove melhoria contínua.",
    objective:
      "Transformar falhas e oportunidades em aprendizado e melhoria sustentável.",
    whyItMatters:
      "Corrigir só o sintoma faz o problema voltar; melhorar de propósito reduz reincidência.",
    expectedBenefits: [
      "Redução de reincidências",
      "Correções mais eficazes",
      "Aprendizado organizacional",
      "Melhoria contínua dos processos",
      "Maior confiança do cliente",
    ],
    problemsAvoided: [
      "Mesmo erro repetido",
      "Ação corretiva só no papel",
      "Melhoria só em crise",
    ],
    expectedResult:
      "Uma visão de como a organização aprende com problemas e fortalece o sistema ao longo do tempo.",
  },
};

/** Nomes curtos para navegação (alinha com aberturas). */
export const CLAUSE_BUSINESS_NAME: Record<string, string> = Object.fromEntries(
  Object.entries(CONSULTIVE_OPENINGS).map(([k, v]) => [k, v.businessName]),
);

const BUSINESS_JOURNEY: { major: string; title: string }[] = [
  { major: "4", title: "Entender a organização" },
  { major: "5", title: "Direcionar pela liderança" },
  { major: "6", title: "Planejar resultados" },
  { major: "7", title: "Garantir capacidade" },
  { major: "8", title: "Controlar a entrega" },
  { major: "9", title: "Avaliar desempenho" },
  { major: "10", title: "Melhorar continuamente" },
];

function answerMap(answers: GuidedAnswer[] | undefined): Map<string, GuidedAnswer> {
  return new Map((answers ?? []).map((a) => [a.question_id, a]));
}

function businessName(major: string, clauseGroups?: GuidedClauseGroup[]): string {
  return (
    CONSULTIVE_OPENINGS[major]?.businessName ??
    clauseGroups?.find((g) => g.id === major)?.label ??
    `Etapa ${major}`
  );
}

function linkedEvidenceCount(answer: GuidedAnswer | undefined): number {
  if (answer?.evidence_links?.length) return answer.evidence_links.length;
  return answer?.evidence_ids?.length ?? 0;
}

function evidenceBuckets(answer: GuidedAnswer | undefined) {
  const links = answer?.evidence_links ?? [];
  let awaitingUpload = 0;
  let processing = 0;
  let approved = 0;
  let rejected = 0;
  for (const link of links) {
    const s = link.evidence_status;
    if (s === "upload_pending") awaitingUpload += 1;
    else if (s === "approved") approved += 1;
    else if (s === "rejected") rejected += 1;
    else if (s) processing += 1;
  }
  return {
    related: linkedEvidenceCount(answer),
    awaitingUpload,
    processing,
    approved,
    rejected,
    promisedLater: answer?.provide_later ? 1 : 0,
  };
}

function tagsFor(answer: GuidedAnswer | undefined): NeutralTag[] {
  const tags: NeutralTag[] = [];
  const v = answer?.answer_value ?? null;
  const linked = linkedEvidenceCount(answer);
  if (v === "yes") {
    tags.push("Prática informada");
    if (linked > 0 || answer?.evidence_note?.trim()) {
      tags.push("Ponto consistente");
    }
  }
  if (v === "partial" || v === "unknown") tags.push("Precisa de esclarecimento");
  if (v === "no") tags.push("Atenção recomendada");
  if (v === "partial" || v === "unknown" || v === "no") {
    tags.push("Revisão do consultor");
  }
  const hasDescribed = !!answer?.evidence_note?.trim();
  if (
    answer?.provide_later ||
    ((v === "yes" || v === "partial") && linked === 0 && !hasDescribed)
  ) {
    tags.push("Evidência pendente");
  }
  return [...new Set(tags)];
}

function toItem(q: GuidedQuestion, a: GuidedAnswer | undefined): NarrativeItem {
  const buckets = evidenceBuckets(a);
  return {
    questionId: q.id,
    theme: q.theme,
    question: q.question,
    tags: tagsFor(a),
    answerValue: a?.answer_value ?? null,
    description: a?.description?.trim() ?? "",
    naJustification: a?.na_justification?.trim() ?? "",
    evidenceNote: a?.evidence_note?.trim() ?? "",
    evidenceCount: buckets.related,
    evidenceAwaitingUpload: buckets.awaitingUpload,
    evidenceProcessing: buckets.processing,
    evidenceApproved: buckets.approved,
    evidenceRejected: buckets.rejected,
    provideLater: !!a?.provide_later,
  };
}

function nextVisibleMajor(
  major: string,
  visibleQuestions: GuidedQuestion[],
): string | null {
  const orderIdx = CLAUSE_NAV_ORDER.indexOf(
    major as (typeof CLAUSE_NAV_ORDER)[number],
  );
  for (let i = orderIdx + 1; i < CLAUSE_NAV_ORDER.length; i++) {
    const m = CLAUSE_NAV_ORDER[i]!;
    if (visibleQuestions.some((q) => clauseMajor(q.clause_ref) === m)) return m;
  }
  return null;
}

function strengtheningLines(n: {
  partialAnswers: NarrativeItem[];
  negativeAnswers: NarrativeItem[];
  unknownAnswers: NarrativeItem[];
  promisedEvidence: NarrativeItem[];
}): string[] {
  const lines: string[] = [];
  if (n.partialAnswers.length > 0) {
    lines.push(
      "Há práticas em evolução que merecem avaliação conjunta com a equipe.",
    );
  }
  if (n.negativeAnswers.length > 0) {
    lines.push(
      "Pontos ainda não estabelecidos podem contribuir para falhas recorrentes se ficarem sem tratamento.",
    );
  }
  if (n.unknownAnswers.length > 0) {
    lines.push(
      "Temas sem clareza tendem a melhorar quando alguém da operação e da gestão alinham a resposta.",
    );
  }
  if (n.promisedEvidence.length > 0) {
    lines.push(
      "Evidências prometidas ajudam a reduzir dúvida na próxima etapa — vale priorizar as críticas.",
    );
  }
  if (lines.length === 0) {
    lines.push(
      "Nesta etapa, o quadro informado pode contribuir para um planejamento de campo mais objetivo.",
    );
  }
  return lines;
}

function impactLines(opening: ConsultiveOpening | undefined, n: ClauseNarrative): string[] {
  const base = opening?.expectedBenefits.slice(0, 3).map(
    (b) => `Pode contribuir para: ${b.charAt(0).toLowerCase()}${b.slice(1)}.`,
  ) ?? [];
  if (n.pending > 0) {
    base.push("Completar as pendências ajuda a reduzir pontos cegos antes da execução em campo.");
  }
  if (n.negativeAnswers.length + n.partialAnswers.length > 0) {
    base.push(
      "Os pontos de atenção merecem avaliação na preparação do trabalho em campo.",
    );
  }
  return base.slice(0, 4);
}

export function getConsultiveOpening(major: string): ConsultiveOpening | null {
  return CONSULTIVE_OPENINGS[major] ?? null;
}

export function buildClauseNarrative(
  major: string,
  visibleQuestions: GuidedQuestion[],
  answers: GuidedAnswer[] | undefined,
  clauseGroups?: GuidedClauseGroup[],
): ClauseNarrative {
  const opening = CONSULTIVE_OPENINGS[major];
  const qs = visibleQuestions.filter((q) => clauseMajor(q.clause_ref) === major);
  const byId = answerMap(answers);
  const items = qs.map((q) => toItem(q, byId.get(q.id)));
  const answeredItems = items.filter((i) => i.answerValue != null);
  const answered = answeredItems.length;
  const applicable = qs.length;
  const pending = Math.max(applicable - answered, 0);
  const evidenceCount = answeredItems.filter(
    (i) => i.evidenceCount > 0 || !!i.evidenceNote,
  ).length;

  const informedPractices = answeredItems.filter((i) => i.answerValue === "yes");
  const linkedOrDescribedEvidence = answeredItems.filter(
    (i) => i.evidenceCount > 0 || !!i.evidenceNote,
  );
  const promisedEvidence = answeredItems.filter((i) => i.provideLater);
  const partialAnswers = answeredItems.filter((i) => i.answerValue === "partial");
  const negativeAnswers = answeredItems.filter((i) => i.answerValue === "no");
  const unknownAnswers = answeredItems.filter((i) => i.answerValue === "unknown");
  const notApplicable = answeredItems.filter(
    (i) => i.answerValue === "not_applicable",
  );
  const clarificationPoints = answeredItems.filter(
    (i) =>
      i.tags.includes("Precisa de esclarecimento") ||
      i.tags.includes("Atenção recomendada") ||
      i.tags.includes("Revisão do consultor"),
  );

  const name = businessName(major, clauseGroups);
  const whatCompanyInformed =
    answered === 0
      ? `Ainda não há respostas suficientes sobre “${name}” para uma leitura útil.`
      : `A empresa informou ${answered} de ${applicable} pontos aplicáveis nesta etapa` +
        (informedPractices.length > 0
          ? `, com ${informedPractices.length} prática(s) descrita(s) como presentes.`
          : ".");

  const next = nextVisibleMajor(major, visibleQuestions);
  const draft: ClauseNarrative = {
    major,
    businessName: name,
    objective: opening?.objective ?? "",
    whatCompanyInformed,
    applicable,
    answered,
    pending,
    stats: {
      answered,
      applicable,
      evidenceCount,
      pending,
      reviewPoints: clarificationPoints.length,
    },
    informedPractices,
    linkedOrDescribedEvidence,
    promisedEvidence,
    partialAnswers,
    negativeAnswers,
    unknownAnswers,
    notApplicable,
    clarificationPoints,
    strengtheningOpportunities: [],
    possibleBusinessImpacts: [],
    nextClauseMajor: next,
    nextClauseLabel: next ? businessName(next, clauseGroups) : null,
  };
  draft.strengtheningOpportunities = strengtheningLines(draft);
  draft.possibleBusinessImpacts = impactLines(opening, draft);
  return draft;
}

export function buildFinalReview(
  session: GuidedSession,
  visibleQuestions: GuidedQuestion[],
  clauseGroups?: GuidedClauseGroup[],
): FinalReviewModel {
  const ctx: GuidedContext = session.context;
  const byId = answerMap(session.answers);
  const applicableCount = visibleQuestions.length;
  const answeredCount = visibleQuestions.filter(
    (q) => byId.get(q.id)?.answer_value != null,
  ).length;

  const allItems = visibleQuestions.map((q) => toItem(q, byId.get(q.id)));
  const answeredItems = allItems.filter((i) => i.answerValue != null);

  const clauses = CLAUSE_NAV_ORDER.map((major) =>
    buildClauseNarrative(major, visibleQuestions, session.answers, clauseGroups),
  ).filter((c) => c.applicable > 0);

  const businessJourney: BusinessJourneyStep[] = BUSINESS_JOURNEY.map(
    (step, idx) => {
      const c = clauses.find((x) => x.major === step.major);
      return {
        order: idx + 1,
        major: step.major,
        title: step.title,
        answered: c?.answered ?? 0,
        applicable: c?.applicable ?? 0,
      };
    },
  );

  const deepeningThemes = answeredItems.filter(
    (i) =>
      i.answerValue === "partial" ||
      i.answerValue === "no" ||
      i.answerValue === "unknown" ||
      i.provideLater,
  );

  const pendingEvidenceItems = answeredItems.filter(
    (i) => i.provideLater || i.tags.includes("Evidência pendente"),
  );

  const nextSteps: string[] = [];
  if (answeredCount < applicableCount) {
    nextSteps.push("Revisar pendências do roteiro nas etapas ainda incompletas.");
  }
  if (pendingEvidenceItems.length > 0) {
    nextSteps.push("Anexar ou descrever as evidências marcadas para depois.");
  }
  if (deepeningThemes.length > 0) {
    nextSteps.push(
      "Aprofundar com a equipe os temas parciais, negativos ou desconhecidos — merecem avaliação antes do campo.",
    );
  }
  nextSteps.push(
    "Concluir a preparação e seguir para a execução em campo no mapa da avaliação.",
  );
  nextSteps.push(
    "Este resumo organiza o que foi informado; qualquer conclusão sobre conformidade fica para revisão humana.",
  );

  const related = answeredItems.reduce((n, i) => n + i.evidenceCount, 0);
  const awaiting = answeredItems.reduce(
    (n, i) => n + (i.evidenceAwaitingUpload ?? 0),
    0,
  );
  const processing = answeredItems.reduce(
    (n, i) => n + (i.evidenceProcessing ?? 0),
    0,
  );
  const approved = answeredItems.reduce(
    (n, i) => n + (i.evidenceApproved ?? 0),
    0,
  );
  const rejected = answeredItems.reduce(
    (n, i) => n + (i.evidenceRejected ?? 0),
    0,
  );
  const promised = answeredItems.filter((i) => i.provideLater).length;

  return {
    profileLines: [
      { label: "Nome", value: ctx.organization_profile.trade_name },
      { label: "Resumo", value: ctx.organization_profile.summary },
      { label: "Porte", value: ctx.organization_profile.size_band },
    ],
    scopeLines: [
      { label: "Escopo", value: ctx.qms_scope.description },
      { label: "Exclusões", value: ctx.qms_scope.exclusions },
      {
        label: "Justificativa das exclusões",
        value: ctx.qms_scope.exclusion_justification,
      },
    ],
    products: ctx.products_services.map((p) => p.name || "(sem nome)"),
    sites: ctx.sites.map((s) =>
      [s.name, s.location].filter(Boolean).join(" — ") || "(sem nome)",
    ),
    processes: ctx.processes.map((p) => p.name || "(sem nome)"),
    stakeholders: ctx.stakeholders.map((s) => s.name || "(sem nome)"),
    businessJourney,
    answeredCount,
    applicableCount,
    evidenceAvailableCount: answeredItems.filter(
      (i) => i.evidenceCount > 0 || !!i.evidenceNote,
    ).length,
    evidencePendingCount: pendingEvidenceItems.length,
    evidenceRelatedCount: related,
    evidenceAwaitingUploadCount: awaiting,
    evidenceProcessingCount: processing,
    evidenceApprovedCount: approved,
    evidenceRejectedCount: rejected,
    evidencePromisedLaterCount: promised,
    unknownCount: answeredItems.filter((i) => i.answerValue === "unknown").length,
    deepeningThemes,
    pendingEvidenceItems,
    nextSteps,
    clauses,
  };
}

export function narrativeAvoidsJudgment(text: string): boolean {
  const forbidden =
    /\b(conforme|não conforme|nao conforme|non-?conform|aprovad[oa]|reprovad[oa]|certificad[oa])\b/i;
  return !forbidden.test(text);
}

export function firstQuestionIndexForClause(
  questions: GuidedQuestion[],
  major: string,
): number {
  return questions.findIndex((q) => clauseMajor(q.clause_ref) === major);
}

export function lastQuestionIndexForClause(
  questions: GuidedQuestion[],
  major: string,
): number {
  let last = -1;
  questions.forEach((q, i) => {
    if (clauseMajor(q.clause_ref) === major) last = i;
  });
  return last;
}

export function clauseHasAnswers(
  questions: GuidedQuestion[],
  answers: GuidedAnswer[] | undefined,
  major: string,
): boolean {
  const ids = new Set(
    questions.filter((q) => clauseMajor(q.clause_ref) === major).map((q) => q.id),
  );
  return (answers ?? []).some(
    (a) => ids.has(a.question_id) && a.answer_value != null,
  );
}
