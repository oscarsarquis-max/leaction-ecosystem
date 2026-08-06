import {
  JOURNEY_PHASES,
  visualStateForPhase,
  type JourneyPhaseDef,
  type PhaseVisualState,
} from "@/lib/auditJourney";

export type OrgPhaseUiState =
  | "completed"
  | "current"
  | "pending"
  | "not_started"
  | "blocked";

export type OrgPhaseCard = {
  phase: JourneyPhaseDef;
  uiState: OrgPhaseUiState;
  stateLabel: string;
  pendingCount: number;
  /** Checklist / itens reais quando confiáveis; senão vazio. */
  doneHints: string[];
  pendingHints: string[];
  /** Percentual só quando há métrica confiável na fase atual. */
  reliablePercent: number | null;
};

function toUiState(
  visual: PhaseVisualState,
  isCurrent: boolean,
  pendingCount: number,
): OrgPhaseUiState {
  if (visual === "completed") return "completed";
  if (visual === "blocked") return "blocked";
  if (visual === "current") return "current";
  // available = próxima liberada
  if (isCurrent) return "current";
  if (pendingCount > 0) return "pending";
  return "not_started";
}

function stateLabel(ui: OrgPhaseUiState): string {
  switch (ui) {
    case "completed":
      return "Concluído";
    case "current":
      return "Em andamento";
    case "pending":
      return "Pendente";
    case "blocked":
      return "Bloqueado";
    default:
      return "Não iniciado";
  }
}

type DashSlice = {
  status: string | undefined | null;
  preparationReady: boolean;
  pending: string[];
  checklist: { id: string; label: string; done: boolean }[];
  counts: {
    guidedAnswered: number;
    guidedTotal: number;
    interviewsDone: number;
    interviewsTotal: number;
    evidences: number;
    findings: number;
    findingsOpen: number;
    plans: number;
    reports: number;
    reportPublished: boolean;
    scopeItems: number;
  };
  hasLead: boolean;
  auditPlanReady?: boolean;
  auditPlanPercent?: number;
};

/**
 * Estados das fases a partir da máquina existente + contagens reais.
 * Não inventa percentuais quando a métrica não é confiável.
 */
export function buildOrgPhaseCards(dash: DashSlice | null): OrgPhaseCard[] {
  if (!dash) {
    return JOURNEY_PHASES.map((phase) => ({
      phase,
      uiState: "not_started" as const,
      stateLabel: "Não iniciado",
      pendingCount: 0,
      doneHints: [],
      pendingHints: [],
      reliablePercent: null,
    }));
  }

  const opts = { preparationReady: dash.preparationReady };
  const curVisual = JOURNEY_PHASES.map((p) =>
    visualStateForPhase(p, dash.status, opts),
  );

  return JOURNEY_PHASES.map((phase, idx) => {
    const visual = curVisual[idx]!;
    const isCurrent = visual === "current";
    let pendingHints: string[] = [];
    let doneHints: string[] = [];
    let pendingCount = 0;
    let reliablePercent: number | null = null;

    if (phase.id === "preparation") {
      doneHints = dash.checklist.filter((c) => c.done).map((c) => c.label);
      pendingHints = dash.checklist.filter((c) => !c.done).map((c) => c.label);
      pendingCount = pendingHints.length;
      if (dash.counts.guidedTotal > 0) {
        reliablePercent = Math.round(
          (dash.counts.guidedAnswered / dash.counts.guidedTotal) * 100,
        );
      }
    } else if (phase.id === "planning" && isCurrent) {
      if (dash.auditPlanReady) doneHints.push("Plano da Auditoria pronto");
      else pendingHints.push("Elaborar Plano da Auditoria");
      if (dash.counts.scopeItems >= 1) doneHints.push("Escopo formal iniciado");
      else pendingHints.push("Incluir item de escopo");
      if (dash.hasLead) doneHints.push("Líder da avaliação definido");
      else pendingHints.push("Confirmar líder da avaliação");
      pendingCount = pendingHints.length;
      if (typeof dash.auditPlanPercent === "number") {
        reliablePercent = dash.auditPlanPercent;
      }
    } else if (phase.id === "field" && (isCurrent || visual === "completed")) {
      if (dash.counts.interviewsDone > 0) {
        doneHints.push(
          `${dash.counts.interviewsDone} entrevista(s) concluída(s)`,
        );
      }
      if (dash.counts.evidences > 0) {
        doneHints.push(`${dash.counts.evidences} evidência(s) registrada(s)`);
      }
      if (isCurrent) {
        pendingHints = [...dash.pending];
        pendingCount = pendingHints.length;
      }
    } else if (phase.id === "analysis" && (isCurrent || visual === "completed")) {
      if (dash.counts.findings > 0) {
        doneHints.push(`${dash.counts.findings} constatação(ões)`);
      }
      if (dash.counts.findingsOpen > 0 && isCurrent) {
        pendingHints.push(
          `${dash.counts.findingsOpen} constatação(ões) em aberto`,
        );
      }
      if (isCurrent) pendingHints = [...new Set([...pendingHints, ...dash.pending])];
      pendingCount = pendingHints.length;
    } else if (phase.id === "actions" && (isCurrent || visual === "completed")) {
      if (dash.counts.plans > 0) doneHints.push("Plano de ação criado");
      if (isCurrent) pendingHints = [...dash.pending];
      pendingCount = pendingHints.length;
    } else if (phase.id === "report" && (isCurrent || visual === "completed")) {
      if (dash.counts.reportPublished) doneHints.push("Relatório publicado");
      else if (dash.counts.reports > 0) doneHints.push("Relatório em elaboração");
      if (isCurrent) pendingHints = [...dash.pending];
      pendingCount = pendingHints.length;
    } else if (phase.id === "conclusion" && visual === "completed") {
      doneHints.push("Avaliação encerrada");
    } else if (isCurrent) {
      pendingHints = [...dash.pending];
      pendingCount = pendingHints.length;
    }

    const uiState = toUiState(visual, isCurrent, pendingCount);
    return {
      phase,
      uiState,
      stateLabel: stateLabel(uiState),
      pendingCount,
      doneHints,
      pendingHints,
      reliablePercent: isCurrent ? reliablePercent : null,
    };
  });
}

export function homeNextAction(input: {
  assessmentId: string;
  status: string | undefined | null;
  preparationReady: boolean;
  continueHref: string;
  continueLabel: string;
  guidedAnswered: number;
  guidedTotal: number;
  pending: string[];
}): {
  title: string;
  description: string;
  reason: string;
  actionText: string;
  href: string;
} {
  const {
    assessmentId,
    status,
    preparationReady,
    guidedAnswered,
    guidedTotal,
    pending,
  } = input;

  if (!status || status === "cancelled") {
    return {
      title: "Inicie a primeira avaliação",
      description:
        "O percurso guia você da preparação ao relatório, em linguagem de negócio.",
      reason: "Ainda não há avaliação ativa nesta organização.",
      actionText: "Iniciar primeira avaliação",
      href: "/assessments/new",
    };
  }

  if (status === "draft" && !preparationReady) {
    const totalLabel =
      guidedTotal > 0
        ? `Você respondeu ${guidedAnswered} de ${guidedTotal} perguntas aplicáveis.`
        : "Continue preenchendo o contexto e o roteiro orientado.";
    return {
      title: "Continue o roteiro orientado",
      description: totalLabel,
      reason:
        pending[0] ??
        "A preparação ainda tem itens em aberto antes do planejamento.",
      actionText: "Continuar preparação",
      href: `/assessments/${assessmentId}/guided`,
    };
  }

  if (status === "draft" && preparationReady) {
    // Prefer continueHref/label from dashboard (Plano da Auditoria discovery).
    const label = input.continueLabel || "Abrir Plano da Auditoria";
    const href =
      input.continueHref || `/assessments/${assessmentId}/audit-plan`;
    return {
      title: "Organize o planejamento",
      description:
        "Abra o Plano da Auditoria para definir propósito, programação e pessoas.",
      reason: pending[0] ?? "Preparação pronta — elabore o Plano da Auditoria.",
      actionText: label,
      href,
    };
  }

  if (status === "planned") {
    const label = input.continueLabel || "Iniciar execução em campo";
    const href = input.continueHref || `/assessments/${assessmentId}/work`;
    return {
      title: "Inicie a execução em campo",
      description: "Com o plano pronto, abra entrevistas e evidências.",
      reason: pending[0] ?? "Avaliação planejada — pronta para começar em campo.",
      actionText: label,
      href,
    };
  }

  if (status === "in_progress") {
    return {
      title: "Continue a execução em campo",
      description: "Registre entrevistas, respostas e evidências.",
      reason: pending[0] ?? "Coleta em andamento.",
      actionText:
        pending.some((p) => /entrevista/i.test(p))
          ? "Iniciar entrevista"
          : "Revisar evidências",
      href: `/assessments/${assessmentId}/work`,
    };
  }

  if (status === "analysis") {
    return {
      title: "Trate as constatações",
      description: "Transforme o campo em constatações e maturidade.",
      reason: pending[0] ?? "Fase de análise em andamento.",
      actionText: "Tratar constatações",
      href: `/assessments/${assessmentId}/work`,
    };
  }

  if (status === "actions") {
    return {
      title: "Acompanhe o plano de ação",
      description: "Defina responsáveis, prazos e validação das ações.",
      reason: pending[0] ?? "Plano de ação em andamento.",
      actionText: "Acompanhar ações",
      href: `/assessments/${assessmentId}/work`,
    };
  }

  if (status === "report") {
    return {
      title: "Prepare o relatório",
      description: "Consolide, revise e publique o relatório da avaliação.",
      reason: pending[0] ?? "Relatório ainda não publicado.",
      actionText: "Preparar relatório",
      href: `/assessments/${assessmentId}/work`,
    };
  }

  if (status === "closed") {
    return {
      title: "Avaliação concluída",
      description: "Consulte o histórico ou inicie um novo ciclo quando fizer sentido.",
      reason: "Esta avaliação já foi encerrada.",
      actionText: "Ver resumo da avaliação",
      href: `/assessments/${assessmentId}`,
    };
  }

  return {
    title: "Continuar a avaliação",
    description: "Siga na etapa atual do percurso.",
    reason: pending[0] ?? "Há trabalho em aberto nesta avaliação.",
    actionText: input.continueLabel,
    href: input.continueHref,
  };
}
