import type {
  ActionItemOut,
  AssessmentOut,
  CockpitCaseItemOut,
  ImprovementCaseEvolutionOut,
  ImprovementCaseOut,
} from "@qmind/api-client";
import { selectFocusAssessment } from "@/lib/selectFocusAssessment";
import {
  canMutateAgileExecution,
  canReadAssessments,
  canReadCockpit,
  canReadImprovementCases,
} from "@/lib/permissions";
import { GUIDED_SPEAK, JOURNEY_V2_CHAPTERS } from "./content";
import type {
  GuidedTourStepAvailability,
  GuidedTourStepDef,
  JourneyChapterId,
  TourDemoContext,
  TourDemoFacts,
} from "./types";

/**
 * Preferência determinística de caso demonstrativo:
 * acting → reviewing → analyzing → open → closed; desempate por updated_at desc.
 */
const CASE_STATUS_RANK: Record<ImprovementCaseOut["status"], number> = {
  acting: 0,
  reviewing: 1,
  analyzing: 2,
  open: 3,
  closed: 4,
};

export function selectFocusImprovementCase(
  items: ImprovementCaseOut[],
): ImprovementCaseOut | null {
  const active = items.filter(Boolean);
  if (active.length === 0) return null;
  return [...active].sort((a, b) => {
    const ra = CASE_STATUS_RANK[a.status] ?? 99;
    const rb = CASE_STATUS_RANK[b.status] ?? 99;
    if (ra !== rb) return ra - rb;
    const ta = Date.parse(a.updated_at ?? a.created_at ?? "") || 0;
    const tb = Date.parse(b.updated_at ?? b.created_at ?? "") || 0;
    return tb - ta;
  })[0]!;
}

/**
 * Preferência determinística de ação:
 * itens não concluídos primeiro; desempate por updated_at desc.
 */
const DONE_ACTION = new Set([
  "done",
  "cancelled",
  "validated",
  "ineffective",
  "ineffective_closed",
  "implemented",
]);

export function selectFocusActionItem(
  items: ActionItemOut[],
): ActionItemOut | null {
  if (items.length === 0) return null;
  const open = items.filter((i) => !DONE_ACTION.has(i.status));
  const pool = open.length > 0 ? open : items;
  return [...pool].sort((a, b) => {
    const ta = Date.parse(a.updated_at ?? a.created_at ?? "") || 0;
    const tb = Date.parse(b.updated_at ?? b.created_at ?? "") || 0;
    return tb - ta;
  })[0]!;
}

export { selectFocusAssessment };

export const EMPTY_TOUR_DEMO_FACTS: TourDemoFacts = {
  hasAnalysisRun: false,
  hasActionItem: false,
  hasMeasurement: false,
  hasExecutionIntelligence: false,
  hasOutcome: false,
};

/** Deriva fatos demonstráveis só de leituras (Evolution + lista de ações). */
export function deriveTourDemoFacts(args: {
  evolution: ImprovementCaseEvolutionOut | null | undefined;
  actionItems: ActionItemOut[];
}): TourDemoFacts {
  const evo = args.evolution ?? null;
  const analysis = evo?.analysis_summary;
  const hasAnalysisRun =
    (analysis?.total_runs ?? 0) > 0 && analysis?.latest_run != null;

  const fromList = selectFocusActionItem(args.actionItems);
  const fromEvoItems = selectFocusActionItem(evo?.action_summary?.items ?? []);
  const hasActionItem =
    !!fromList ||
    !!fromEvoItems ||
    (evo?.action_summary?.total ?? 0) > 0;

  const measurement = evo?.measurement_summary;
  const indicatorCount = measurement?.indicator_count ?? 0;
  const posture = measurement?.measurement_posture;
  const hasMeasurement =
    indicatorCount > 0 ||
    (posture != null && posture !== "not_planned");

  const hasExecutionIntelligence = !!evo?.execution_intelligence?.run_id;

  const hasOutcome =
    !!evo?.latest_outcome_observation ||
    (evo?.outcome_observations?.length ?? 0) > 0;

  return {
    hasAnalysisRun,
    hasActionItem,
    hasMeasurement,
    hasExecutionIntelligence,
    hasOutcome,
  };
}

/**
 * Usa o read-model do Cockpit (GET) para preferir um caso com conteúdo
 * alinhado ao capítulo — sem mutação e sem fan-out OI.
 */
export function preferCaseIdFromCockpit(
  stepId: JourneyChapterId,
  items: CockpitCaseItemOut[],
): string | null {
  if (items.length === 0) return null;
  switch (stepId) {
    case "interpret":
      return (
        items.find((i) => i.intelligence_freshness === "current")?.case_id ??
        items.find((i) => i.intelligence_freshness === "stale")?.case_id ??
        null
      );
    case "execute":
      return items.find((i) => i.action_count > 0)?.case_id ?? null;
    case "evidence_measure":
      return (
        items.find((i) => i.measurement_posture !== "not_planned")?.case_id ??
        null
      );
    case "analyze":
      return (
        items.find((i) => i.case_status === "analyzing")?.case_id ??
        items.find((i) => i.case_status === "acting")?.case_id ??
        items.find((i) => i.case_status === "reviewing")?.case_id ??
        null
      );
    case "decide":
      return (
        items.find((i) => i.closure_readiness === "ready_for_review")?.case_id ??
        items.find((i) => i.outcome_observed_at != null)?.case_id ??
        null
      );
    default:
      return null;
  }
}

export function selectFocusImprovementCaseForChapter(
  stepId: JourneyChapterId,
  cases: ImprovementCaseOut[],
  cockpitItems: CockpitCaseItemOut[] | null | undefined,
): ImprovementCaseOut | null {
  if (cases.length === 0) return null;
  const preferredId = preferCaseIdFromCockpit(stepId, cockpitItems ?? []);
  if (preferredId) {
    const hit = cases.find((c) => c.id === preferredId);
    if (hit) return hit;
  }
  return selectFocusImprovementCase(cases);
}

export const GUIDED_TOUR_V2_STEPS: GuidedTourStepDef[] = JOURNEY_V2_CHAPTERS.map(
  (chapter, order) => {
    const speak = GUIDED_SPEAK[chapter.id];
    return {
      id: chapter.id,
      order,
      title: speak.title,
      demonstrate: speak.demonstrate,
      message: speak.message,
      limitation: speak.limitation,
      contextRequirement: speak.contextRequirement,
    };
  },
);

function resolveHref(
  stepId: JourneyChapterId,
  ctx: TourDemoContext,
): string | null {
  switch (stepId) {
    case "understand":
      return "/assessments";
    case "assess":
      return ctx.assessmentId ? `/assessments/${ctx.assessmentId}/guided` : null;
    case "recognize":
    case "analyze":
    case "evidence_measure":
    case "interpret":
    case "decide":
      return ctx.caseId ? `/improvement-cases/${ctx.caseId}` : null;
    case "execute":
      // Só card real — board vazio não é demonstrável.
      return ctx.actionItemId ? `/execution/cards/${ctx.actionItemId}` : null;
    case "control":
      return "/cockpit";
    default:
      return null;
  }
}

function canAccessStep(
  stepId: JourneyChapterId,
  roles: readonly string[],
): boolean {
  switch (stepId) {
    case "understand":
    case "assess":
      return canReadAssessments(roles);
    case "recognize":
    case "analyze":
    case "evidence_measure":
    case "interpret":
    case "decide":
      return canReadImprovementCases(roles);
    case "execute":
      return canMutateAgileExecution(roles) || canReadImprovementCases(roles);
    case "control":
      return canReadCockpit(roles);
    default:
      return false;
  }
}

const UNAVAILABLE: Record<GuidedTourStepDef["contextRequirement"], string> = {
  organization: "Selecione uma organização ativa para continuar a apresentação.",
  assessment:
    "Não há avaliação demonstrável nesta organização. Crie ou avance uma avaliação fora do tour e retorne.",
  case: "Não há Improvement Case demonstrável. Registre um caso fora do tour e retorne.",
  action:
    "Não há ação/card demonstrável. Vincule uma ação a um caso fora do tour e retorne.",
  cockpit: "O Cockpit não está disponível para o seu papel nesta organização.",
};

const CONTENT_UNAVAILABLE: Partial<Record<JourneyChapterId, string>> = {
  analyze:
    "Não há análise OI persistida neste caso. Gere uma análise fora do tour e retorne.",
  execute:
    "Não há ação/card demonstrável neste caso. Atribua uma ação fora do tour e retorne — o board vazio não demonstra execução.",
  evidence_measure:
    "Não há indicador ou medição registrada neste caso. Prepare a medição fora do tour e retorne.",
  interpret:
    "A execução ainda não foi interpretada neste caso (sem Execution Intelligence persistida). Execute a interpretação fora do tour e retorne.",
};

function needsEvolutionFacts(stepId: JourneyChapterId): boolean {
  return (
    stepId === "analyze" ||
    stepId === "evidence_measure" ||
    stepId === "interpret" ||
    stepId === "execute"
  );
}

/**
 * Resolve destino e disponibilidade — somente leitura; sem mutação.
 * ready = há conteúdo real para demonstrar na tela de destino.
 */
export function resolveTourStepAvailability(
  step: GuidedTourStepDef,
  ctx: TourDemoContext,
): GuidedTourStepAvailability {
  if (!ctx.organizationId) {
    return {
      status: "unavailable",
      href: null,
      reason: UNAVAILABLE.organization,
    };
  }

  if (!canAccessStep(step.id, ctx.roles)) {
    return {
      status: "forbidden",
      href: null,
      reason:
        "Seu papel nesta organização não tem acesso a esta tela. Peça a um perfil autorizado para demonstrar.",
    };
  }

  const req = step.contextRequirement;

  if (req === "assessment") {
    if (ctx.assessmentsLoading) {
      return { status: "loading", href: null, reason: null };
    }
    if (ctx.assessmentsError) {
      return {
        status: "error",
        href: null,
        reason: "Não foi possível carregar avaliações. Tente novamente.",
      };
    }
    if (!ctx.assessmentId) {
      return { status: "unavailable", href: null, reason: UNAVAILABLE.assessment };
    }
  }

  if (req === "case" || req === "action") {
    if (ctx.casesLoading) {
      return { status: "loading", href: null, reason: null };
    }
    if (ctx.casesError) {
      return {
        status: "error",
        href: null,
        reason: "Não foi possível carregar casos. Tente novamente.",
      };
    }
    if (!ctx.caseId) {
      return { status: "unavailable", href: null, reason: UNAVAILABLE.case };
    }
  }

  if (req === "action") {
    if (ctx.actionsLoading) {
      return { status: "loading", href: null, reason: null };
    }
    if (ctx.actionsError) {
      return {
        status: "error",
        href: null,
        reason: "Não foi possível carregar ações. Tente novamente.",
      };
    }
  }

  if (needsEvolutionFacts(step.id)) {
    if (ctx.evolutionLoading) {
      return { status: "loading", href: null, reason: null };
    }
    if (ctx.evolutionError) {
      return {
        status: "error",
        href: null,
        reason: "Não foi possível carregar a Evolution do caso. Tente novamente.",
      };
    }
  }

  if (req === "cockpit" && !canReadCockpit(ctx.roles)) {
    return { status: "forbidden", href: null, reason: UNAVAILABLE.cockpit };
  }

  // Conteúdo demonstrável por capítulo (além de “existe um caso”).
  if (step.id === "analyze" && !ctx.facts.hasAnalysisRun) {
    return {
      status: "unavailable",
      href: null,
      reason: CONTENT_UNAVAILABLE.analyze!,
    };
  }
  if (step.id === "execute" && (!ctx.facts.hasActionItem || !ctx.actionItemId)) {
    return {
      status: "unavailable",
      href: null,
      reason: CONTENT_UNAVAILABLE.execute!,
    };
  }
  if (step.id === "evidence_measure" && !ctx.facts.hasMeasurement) {
    return {
      status: "unavailable",
      href: null,
      reason: CONTENT_UNAVAILABLE.evidence_measure!,
    };
  }
  if (step.id === "interpret" && !ctx.facts.hasExecutionIntelligence) {
    return {
      status: "unavailable",
      href: null,
      reason: CONTENT_UNAVAILABLE.interpret!,
    };
  }

  const href = resolveHref(step.id, ctx);
  if (!href) {
    return {
      status: "unavailable",
      href: null,
      reason: UNAVAILABLE[req],
    };
  }

  return { status: "ready", href, reason: null };
}

export function indexOfChapter(id: JourneyChapterId): number {
  const idx = GUIDED_TOUR_V2_STEPS.findIndex((s) => s.id === id);
  return idx >= 0 ? idx : 0;
}

export function chapterIdAt(index: number): JourneyChapterId {
  const step = GUIDED_TOUR_V2_STEPS[index] ?? GUIDED_TOUR_V2_STEPS[0]!;
  return step.id;
}

/** Rótulo humano curto para listas (sem UUID). */
export function humanCaseLabel(c: ImprovementCaseOut): string {
  const problem = (c.problem_statement || "Caso").trim();
  const short = problem.length > 72 ? `${problem.slice(0, 69)}…` : problem;
  return `${short} · ${c.status}`;
}

export function humanAssessmentLabel(a: AssessmentOut): string {
  return `${a.type} · ${a.status} · ${a.updated_at.slice(0, 10)}`;
}

export function humanActionLabel(a: ActionItemOut): string {
  const title = (a.description || "Ação").trim();
  const short = title.length > 64 ? `${title.slice(0, 61)}…` : title;
  return `${short} · ${a.status}`;
}
