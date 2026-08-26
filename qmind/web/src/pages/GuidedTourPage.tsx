import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useOrganization } from "@/org/OrganizationProvider";
import { useAssessments } from "@/hooks/useAssessments";
import { useImprovementCases } from "@/hooks/useImprovementCases";
import { useImprovementCaseActions } from "@/hooks/useImprovementCaseActions";
import { useImprovementCaseEvolution } from "@/hooks/useImprovementCaseEvolution";
import { useIsoIntelligenceCockpitCases } from "@/hooks/useIsoIntelligenceCockpit";
import { canReadCockpit } from "@/lib/permissions";
import {
  GUIDED_TOUR_STEPS,
  chapterIdFromStepIndex,
  clearGuidedTour,
  readGuidedTourStepIndex,
  setGuidedTourStepIndex,
  stepIndexFromChapterParam,
  writeGuidedTourActive,
} from "@/lib/guidedTour";
import {
  EMPTY_TOUR_DEMO_FACTS,
  GUIDED_TOUR_V2_STEPS,
  deriveTourDemoFacts,
  humanActionLabel,
  humanAssessmentLabel,
  humanCaseLabel,
  resolveTourStepAvailability,
  selectFocusActionItem,
  selectFocusAssessment,
  selectFocusImprovementCase,
  selectFocusImprovementCaseForChapter,
  type JourneyChapterId,
} from "@/journeyV2";
import { LoadingPanel, ErrorPanel } from "@/components/StatePanels";

/**
 * Apresentação guiada autenticada V2 — orientação e navegação GET-only.
 * ready = há conteúdo real demonstrável (Evolution/Cockpit/ações).
 */
export function GuidedTourPage() {
  const org = useOrganization();
  const assessments = useAssessments();
  const cases = useImprovementCases();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [stepIndex, setStepIndex] = useState(() => {
    const rawChapter = searchParams.get("chapter");
    if (rawChapter != null) return stepIndexFromChapterParam(rawChapter);
    return readGuidedTourStepIndex();
  });
  const [pickedAssessmentId, setPickedAssessmentId] = useState("");
  const [pickedCaseId, setPickedCaseId] = useState("");
  const prevOrgRef = useRef<string | null>(null);

  const roles = org.currentOrganization?.roles ?? [];
  const step = GUIDED_TOUR_V2_STEPS[stepIndex] ?? GUIDED_TOUR_V2_STEPS[0]!;
  const total = GUIDED_TOUR_V2_STEPS.length;

  const cockpitEnabled = canReadCockpit(roles);
  const cockpitCases = useIsoIntelligenceCockpitCases({ limit: 25 });
  const cockpitItems = useMemo(() => {
    if (!cockpitEnabled || cockpitCases.isError) return [];
    return (cockpitCases.data?.pages ?? []).flatMap((p) => p.items ?? []);
  }, [cockpitEnabled, cockpitCases.data, cockpitCases.isError]);

  const focusAssessment = useMemo(() => {
    const items = assessments.data ?? [];
    if (pickedAssessmentId) {
      return (
        items.find((a) => a.id === pickedAssessmentId) ??
        selectFocusAssessment(items)
      );
    }
    return selectFocusAssessment(items);
  }, [assessments.data, pickedAssessmentId]);

  const focusCase = useMemo(() => {
    const items = cases.data ?? [];
    if (pickedCaseId) {
      return items.find((c) => c.id === pickedCaseId) ?? selectFocusImprovementCase(items);
    }
    return selectFocusImprovementCaseForChapter(step.id, items, cockpitItems);
  }, [cases.data, pickedCaseId, step.id, cockpitItems]);

  const actions = useImprovementCaseActions(focusCase?.id);
  const evolution = useImprovementCaseEvolution(focusCase?.id);

  const actionPool = useMemo(() => {
    const fromHook = actions.data?.items ?? [];
    if (fromHook.length > 0) return fromHook;
    return evolution.data?.action_summary?.items ?? [];
  }, [actions.data, evolution.data]);

  const focusAction = useMemo(
    () => selectFocusActionItem(actionPool),
    [actionPool],
  );

  const facts = useMemo(
    () =>
      deriveTourDemoFacts({
        evolution: evolution.data,
        actionItems: actionPool,
      }),
    [evolution.data, actionPool],
  );

  // Limpa seleção e progresso somente quando a organização muda de fato.
  useEffect(() => {
    const id = org.currentOrganizationId;
    if (prevOrgRef.current && id && prevOrgRef.current !== id) {
      setPickedAssessmentId("");
      setPickedCaseId("");
      clearGuidedTour();
      setStepIndex(0);
    }
    prevOrgRef.current = id;
  }, [org.currentOrganizationId]);

  useEffect(() => {
    const chapter = chapterIdFromStepIndex(stepIndex);
    const current = searchParams.get("chapter");
    if (current !== chapter) {
      setSearchParams({ chapter }, { replace: true });
    }
    if (org.currentOrganizationId) {
      setGuidedTourStepIndex(stepIndex);
      writeGuidedTourActive(org.currentOrganizationId, stepIndex);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- sync chapter URL once per step
  }, [stepIndex, org.currentOrganizationId, setSearchParams]);

  const evolutionNeeded =
    step.id === "analyze" ||
    step.id === "execute" ||
    step.id === "evidence_measure" ||
    step.id === "interpret";

  const availability = resolveTourStepAvailability(step, {
    organizationId: org.currentOrganizationId,
    roles,
    assessmentId: focusAssessment?.id ?? null,
    caseId: focusCase?.id ?? null,
    actionItemId: focusAction?.id ?? null,
    assessmentsLoading: assessments.isLoading,
    casesLoading: cases.isLoading,
    actionsLoading: actions.isLoading,
    evolutionLoading: evolutionNeeded && !!focusCase?.id && evolution.isLoading,
    assessmentsError: assessments.isError,
    casesError: cases.isError,
    actionsError: actions.isError,
    evolutionError: evolutionNeeded && evolution.isError,
    facts: evolutionNeeded ? facts : EMPTY_TOUR_DEMO_FACTS,
  });

  if (org.loading && !org.currentOrganizationId) {
    return <LoadingPanel title="Carregando organizações…" />;
  }

  if (!org.currentOrganizationId) {
    return (
      <ErrorPanel
        title="Organização necessária"
        message="Selecione uma organização ativa para iniciar a apresentação guiada."
        action={{
          label: "Ir para avaliações",
          onClick: () => void navigate("/assessments"),
        }}
      />
    );
  }

  const activateAndOpen = () => {
    if (availability.status !== "ready" || !availability.href) return;
    writeGuidedTourActive(org.currentOrganizationId!, stepIndex);
    void navigate(availability.href);
  };

  const goStep = (next: number) => {
    const clamped = Math.max(0, Math.min(next, total - 1));
    setStepIndex(clamped);
  };

  const goChapter = (id: JourneyChapterId) => {
    const idx = GUIDED_TOUR_V2_STEPS.findIndex((s) => s.id === id);
    if (idx >= 0) goStep(idx);
  };

  const statusLabel: Record<typeof availability.status, string> = {
    ready: "Pronto para abrir no produto",
    unavailable: "Indisponível nesta organização",
    forbidden: "Sem permissão para esta tela",
    loading: "Carregando contexto…",
    error: "Erro recuperável ao carregar",
  };

  return (
    <div className="space-y-6" data-testid="guided-tour-page">
      <header className="qm-page-header space-y-2">
        <p className="qm-page-header__eyebrow">Apresentação guiada · Jornada V2</p>
        <h1 className="qm-page-header__title">{step.title}</h1>
        <p className="qm-page-header__explain">
          Capítulo {stepIndex + 1} de {total} ·{" "}
          {org.currentOrganization?.organizationName ?? "organização ativa"}
        </p>
        <div
          className="h-2 w-full overflow-hidden rounded-full bg-[var(--qm-surface-soft)]"
          role="progressbar"
          aria-valuemin={1}
          aria-valuemax={total}
          aria-valuenow={stepIndex + 1}
          aria-label="Progresso da apresentação guiada"
          data-testid="guided-tour-progress"
        >
          <div
            className="h-full rounded-full bg-[var(--qm-accent)] transition-[width] duration-300 motion-reduce:transition-none"
            style={{ width: `${((stepIndex + 1) / total) * 100}%` }}
          />
        </div>
      </header>

      <nav aria-label="Capítulos da apresentação">
        <ol className="flex flex-wrap gap-2" data-testid="guided-tour-chapters">
          {GUIDED_TOUR_V2_STEPS.map((s, i) => (
            <li key={s.id}>
              <button
                type="button"
                className={
                  i === stepIndex
                    ? "rounded-md bg-[var(--qm-accent)] px-2 py-1 text-sm text-white"
                    : "rounded-md border border-[var(--qm-line)] px-2 py-1 text-sm text-[var(--qm-muted)]"
                }
                aria-current={i === stepIndex ? "step" : undefined}
                onClick={() => goChapter(s.id)}
              >
                {i + 1}. {JOURNEY_LABEL[s.id]}
              </button>
            </li>
          ))}
        </ol>
      </nav>

      <section className="qm-panel space-y-4 p-5">
        <div>
          <h2 className="text-base font-semibold text-[var(--qm-ink)]">
            O que mostrar
          </h2>
          <p className="mt-1 text-[var(--qm-muted)]">{step.demonstrate}</p>
        </div>
        <div>
          <h2 className="text-base font-semibold text-[var(--qm-ink)]">
            Mensagem principal
          </h2>
          <p className="mt-1 text-[var(--qm-muted)]">{step.message}</p>
        </div>
        <div>
          <h2 className="text-base font-semibold text-[var(--qm-ink)]">
            Limite / decisão humana
          </h2>
          <p className="mt-1 text-[var(--qm-muted)]">{step.limitation}</p>
        </div>

        <div
          className="rounded-md border border-[var(--qm-line)] bg-[var(--qm-surface-soft)] p-4"
          data-testid={`guided-tour-status-${availability.status}`}
          role="status"
        >
          <p className="text-sm font-medium text-[var(--qm-ink)]">
            {statusLabel[availability.status]}
          </p>
          {availability.reason ? (
            <p
              className="mt-1 text-sm text-[var(--qm-muted)]"
              data-testid="guided-tour-status-reason"
            >
              {availability.reason}
            </p>
          ) : null}
        </div>

        {(step.contextRequirement === "assessment" ||
          step.contextRequirement === "organization") &&
        (assessments.data?.length ?? 0) > 1 ? (
          <label className="block text-sm">
            <span className="font-medium text-[var(--qm-ink)]">
              Avaliação demonstrativa
            </span>
            <select
              className="qm-field mt-1 w-full"
              value={pickedAssessmentId || focusAssessment?.id || ""}
              onChange={(e) => setPickedAssessmentId(e.target.value)}
              data-testid="guided-tour-assessment-select"
            >
              <option value="">Seleção automática</option>
              {(assessments.data ?? []).map((a) => (
                <option key={a.id} value={a.id}>
                  {humanAssessmentLabel(a)}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        {(step.contextRequirement === "case" ||
          step.contextRequirement === "action") &&
        (cases.data?.length ?? 0) > 1 ? (
          <label className="block text-sm">
            <span className="font-medium text-[var(--qm-ink)]">
              Caso demonstrativo
            </span>
            <select
              className="qm-field mt-1 w-full"
              value={pickedCaseId || focusCase?.id || ""}
              onChange={(e) => setPickedCaseId(e.target.value)}
              data-testid="guided-tour-case-select"
            >
              <option value="">Seleção automática</option>
              {(cases.data ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {humanCaseLabel(c)}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        {focusAssessment && step.contextRequirement === "assessment" ? (
          <p className="text-sm text-[var(--qm-muted)]">
            Avaliação em foco:{" "}
            <strong className="text-[var(--qm-ink)]">
              {humanAssessmentLabel(focusAssessment)}
            </strong>
          </p>
        ) : null}

        {focusCase &&
        (step.contextRequirement === "case" ||
          step.contextRequirement === "action") ? (
          <p className="text-sm text-[var(--qm-muted)]">
            Caso em foco:{" "}
            <strong className="text-[var(--qm-ink)]">
              {humanCaseLabel(focusCase)}
            </strong>
          </p>
        ) : null}

        {focusAction && step.contextRequirement === "action" ? (
          <p className="text-sm text-[var(--qm-muted)]">
            Ação em foco:{" "}
            <strong className="text-[var(--qm-ink)]">
              {humanActionLabel(focusAction)}
            </strong>
          </p>
        ) : null}
      </section>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          className="qm-btn-primary"
          disabled={availability.status !== "ready"}
          onClick={activateAndOpen}
          data-testid="guided-tour-open-product"
        >
          Abrir no produto
        </button>
        <button
          type="button"
          className="qm-btn-secondary"
          disabled={stepIndex >= total - 1}
          onClick={() => goStep(stepIndex + 1)}
          data-testid="guided-tour-next"
        >
          Próximo capítulo
        </button>
        <button
          type="button"
          className="qm-btn-secondary"
          disabled={stepIndex <= 0}
          onClick={() => goStep(stepIndex - 1)}
          data-testid="guided-tour-prev"
        >
          Capítulo anterior
        </button>
        <Link to="/" className="qm-btn-secondary">
          Voltar à apresentação pública
        </Link>
        <button
          type="button"
          className="qm-btn-secondary"
          onClick={() => {
            clearGuidedTour();
            void navigate("/assessments");
          }}
          data-testid="guided-tour-end"
        >
          Encerrar apresentação
        </button>
      </div>

      <span className="sr-only">{GUIDED_TOUR_STEPS.length} capítulos</span>
    </div>
  );
}

const JOURNEY_LABEL: Record<JourneyChapterId, string> = {
  understand: "Compreender",
  assess: "Avaliar",
  recognize: "Reconhecer",
  analyze: "Analisar",
  execute: "Executar",
  evidence_measure: "Medir",
  interpret: "Interpretar",
  control: "Controlar",
  decide: "Decidir",
};
