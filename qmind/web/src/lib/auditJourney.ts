/** Mapa visual da avaliação — espelha AssessmentStatus (sem 2ª máquina de estados). */

export type AssessmentStatus =
  | "draft"
  | "planned"
  | "in_progress"
  | "analysis"
  | "actions"
  | "report"
  | "closed"
  | "cancelled";

export type JourneyPhaseId =
  | "preparation"
  | "planning"
  | "field"
  | "analysis"
  | "actions"
  | "report"
  | "conclusion";

export type PhaseVisualState =
  | "completed"
  | "current"
  | "available"
  | "blocked";

export type JourneyPhaseDef = {
  id: JourneyPhaseId;
  label: string;
  /** Status backend que marca a fase como “atual”. */
  status: AssessmentStatus;
  objective: string;
  activities: string[];
  expectedResult: string;
  advanceCriteria: string;
  effortHint: string;
};

export const JOURNEY_PHASES: JourneyPhaseDef[] = [
  {
    id: "preparation",
    label: "Preparação",
    status: "draft",
    objective: "Conhecer a organização, o escopo e o contexto do sistema de qualidade.",
    activities: [
      "Registrar organização, produtos e processos",
      "Responder ao roteiro orientado (cláusulas 4–10, linguagem de negócio)",
      "Indicar evidências ou deixar para depois",
    ],
    expectedResult: "Contexto claro e respostas iniciais para planejar a avaliação.",
    advanceCriteria: "Contexto preenchido e roteiro da preparação concluído ou revisado.",
    effortHint: "cerca de 45–90 minutos",
  },
  {
    id: "planning",
    label: "Planejamento",
    status: "planned",
    objective: "Definir equipe, escopo formal e como a avaliação será conduzida.",
    activities: [
      "Confirmar escopo e equipe",
      "Planejar entrevistas e amostragem",
      "Preparar a execução em campo",
    ],
    expectedResult: "Plano pronto para iniciar a coleta em campo.",
    advanceCriteria: "Avaliação planejada e equipe definida.",
    effortHint: "cerca de 30–60 minutos",
  },
  {
    id: "field",
    label: "Execução em campo",
    status: "in_progress",
    objective: "Conduzir entrevistas, registrar respostas e reunir evidências.",
    activities: [
      "Realizar entrevistas",
      "Responder perguntas do roteiro de campo",
      "Anexar ou descrever evidências",
    ],
    expectedResult: "Base factual da avaliação (entrevistas + evidências).",
    advanceCriteria: "Coleta suficiente para analisar constatações.",
    effortHint: "varia conforme o escopo",
  },
  {
    id: "analysis",
    label: "Análise",
    status: "analysis",
    objective: "Transformar achados de campo em constatações e maturidade.",
    activities: [
      "Registrar constatações",
      "Revisar tipificação",
      "Elaborar visão de maturidade (quando aplicável)",
    ],
    expectedResult: "Constatações revisáveis e priorizadas.",
    advanceCriteria: "Constatações relevantes em análise ou aprovadas.",
    effortHint: "cerca de 1–3 horas",
  },
  {
    id: "actions",
    label: "Plano de ação",
    status: "actions",
    objective: "Definir ações corretivas e de melhoria com responsáveis.",
    activities: [
      "Criar plano de ação",
      "Definir itens, prazos e donos",
      "Acompanhar validação",
    ],
    expectedResult: "Plano rastreável de melhorias.",
    advanceCriteria: "Itens principais definidos para as constatações prioritárias.",
    effortHint: "cerca de 1–2 horas",
  },
  {
    id: "report",
    label: "Relatório",
    status: "report",
    objective: "Consolidar a avaliação em um relatório compreensível.",
    activities: [
      "Gerar rascunho do relatório",
      "Revisar conteúdo",
      "Publicar versão",
    ],
    expectedResult: "Relatório publicado e compartilhado.",
    advanceCriteria: "Relatório publicado.",
    effortHint: "cerca de 30–90 minutos",
  },
  {
    id: "conclusion",
    label: "Conclusão",
    status: "closed",
    objective: "Encerrar a avaliação com rastreabilidade completa.",
    activities: ["Revisar pendências finais", "Encerrar a avaliação"],
    expectedResult: "Avaliação encerrada e histórica.",
    advanceCriteria: "Pendências críticas resolvidas ou registradas.",
    effortHint: "poucos minutos",
  },
];

const STATUS_ORDER: AssessmentStatus[] = [
  "draft",
  "planned",
  "in_progress",
  "analysis",
  "actions",
  "report",
  "closed",
];

export function statusIndex(status: string | undefined | null): number {
  if (!status) return 0;
  if (status === "cancelled") return -1;
  const i = STATUS_ORDER.indexOf(status as AssessmentStatus);
  return i < 0 ? 0 : i;
}

export type JourneyDisplayOptions = {
  /** Preparação concluída em draft → barra trata Planejamento como fase atual. */
  preparationReady?: boolean;
};

/**
 * Índice visual da fase atual (0…6).
 * Em draft com preparação pronta, avança visualmente para Planejamento (1).
 */
export function journeyDisplayIndex(
  status: string | undefined | null,
  options?: JourneyDisplayOptions,
): number {
  if (!status || status === "cancelled") return 0;
  const idx = statusIndex(status);
  if (status === "draft" && options?.preparationReady) return 1;
  return Math.max(0, idx);
}

export function phaseForStatus(
  status: string | undefined | null,
  options?: JourneyDisplayOptions,
): JourneyPhaseId {
  if (status === "cancelled") return "preparation";
  const idx = journeyDisplayIndex(status, options);
  return JOURNEY_PHASES[Math.max(0, Math.min(idx, JOURNEY_PHASES.length - 1))]!.id;
}

export function visualStateForPhase(
  phase: JourneyPhaseDef,
  currentStatus: string | undefined | null,
  options?: JourneyDisplayOptions,
): PhaseVisualState {
  if (currentStatus === "cancelled") {
    return phase.id === "preparation" ? "current" : "blocked";
  }
  const cur = journeyDisplayIndex(currentStatus, options);
  const phaseIdx = statusIndex(phase.status);
  if (phaseIdx < cur) return "completed";
  if (phaseIdx === cur) return "current";
  if (phaseIdx === cur + 1) return "available";
  return "blocked";
}

export function overallPercent(
  currentStatus: string | undefined | null,
  phaseSubProgress = 0,
): number {
  const cur = statusIndex(currentStatus);
  if (cur < 0) return 0;
  if (currentStatus === "closed") return 100;
  const base = (cur / (STATUS_ORDER.length - 1)) * 100;
  const slice = 100 / (STATUS_ORDER.length - 1);
  const sub = Math.min(1, Math.max(0, phaseSubProgress));
  return Math.round(Math.min(99, base + slice * sub));
}

export type ContinueHrefOptions = {
  /** Preparação concluída (revisão/checklist) — libera rota de Planejamento. */
  preparationReady?: boolean;
};

/**
 * Próxima rota do percurso.
 * Em draft: só vai ao Planejamento (/work) quando a preparação estiver pronta;
 * caso contrário permanece na preparação (/guided).
 */
export function continueHref(
  assessmentId: string,
  status: string | undefined | null,
  options?: ContinueHrefOptions,
): { href: string; label: string } {
  switch (status) {
    case "draft":
      if (options?.preparationReady) {
        return {
          href: `/assessments/${assessmentId}/work`,
          label: "Ir para o Planejamento",
        };
      }
      return {
        href: `/assessments/${assessmentId}/guided`,
        label: "Continuar preparação",
      };
    case "planned":
      return {
        href: `/assessments/${assessmentId}/work`,
        label: "Continuar planejamento",
      };
    case "in_progress":
    case "analysis":
    case "actions":
    case "report":
      return {
        href: `/assessments/${assessmentId}/work`,
        label: "Continuar avaliação",
      };
    case "closed":
      return {
        href: `/assessments/${assessmentId}`,
        label: "Ver resumo da avaliação",
      };
    default:
      return {
        href: `/assessments/${assessmentId}`,
        label: "Abrir mapa da avaliação",
      };
  }
}

/** Preparação pronta para Planejamento (revisão final ou checklist completo). */
export function isPreparationReady(input: {
  currentStep?: string | null;
  guidedStatus?: string | null;
  checklistDone: boolean;
}): boolean {
  if (input.checklistDone) return true;
  if (input.currentStep === "review") return true;
  if (input.guidedStatus === "review" || input.guidedStatus === "completed") {
    return true;
  }
  return false;
}

export function blockReason(
  phase: JourneyPhaseDef,
  currentStatus: string | undefined | null,
  options?: JourneyDisplayOptions,
): string | null {
  const state = visualStateForPhase(phase, currentStatus, options);
  if (state !== "blocked") return null;
  const curPhase = JOURNEY_PHASES[journeyDisplayIndex(currentStatus, options)];
  return `Conclua “${curPhase?.label ?? "a fase atual"}” antes de avançar para “${phase.label}”.`;
}

export type JourneyChecklistItem = {
  id: string;
  label: string;
  done: boolean;
};

export function preparationChecklist(input: {
  hasOrgProfile: boolean;
  hasScope: boolean;
  hasProcesses: boolean;
  answered: number;
  totalQuestions: number;
  withEvidenceOrLater: number;
}): JourneyChecklistItem[] {
  return [
    {
      id: "org",
      label: "Organização descrita",
      done: input.hasOrgProfile,
    },
    {
      id: "scope",
      label: "Escopo do sistema informado",
      done: input.hasScope,
    },
    {
      id: "processes",
      label: "Processos principais listados",
      done: input.hasProcesses,
    },
    {
      id: "route",
      label: `Roteiro respondido (${input.answered}/${input.totalQuestions || "—"})`,
      done:
        input.totalQuestions > 0 && input.answered >= input.totalQuestions,
    },
    {
      id: "evidence",
      label: "Evidências tratadas (anexadas, descritas ou “depois”)",
      done:
        input.answered > 0 && input.withEvidenceOrLater >= Math.min(input.answered, 1),
    },
  ];
}

export function consistencyScore(input: {
  answered: number;
  withEvidenceOrLater: number;
  withDescription: number;
}): number {
  if (input.answered <= 0) return 0;
  const ev = input.withEvidenceOrLater / input.answered;
  const desc = input.withDescription / input.answered;
  return Math.round(((ev * 0.55 + desc * 0.45) * 100));
}
