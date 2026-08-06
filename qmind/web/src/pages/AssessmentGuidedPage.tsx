import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  GUIDED_STEPS,
  type GuidedAnswerUpsert,
  type GuidedContext,
  type GuidedStep,
} from "@/api/guidedTypes";
import { QmindApiError } from "@/api/qmindApi";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { AccessDeniedPanel, LoadingPanel } from "@/components/StatePanels";
import { GuidedContextSteps } from "@/components/guided/GuidedContextSteps";
import { GuidedProgress } from "@/components/guided/GuidedProgress";
import { GuidedReview } from "@/components/guided/GuidedReview";
import { GuidedClauseNav } from "@/components/guided/GuidedClauseNav";
import { GuidedRouteStep } from "@/components/guided/GuidedRouteStep";
import { JourneyBar } from "@/components/navigation/JourneyBar";
import {
  GuidedEmptyState,
  PageHeader,
  SectionIntroduction,
} from "@/components/qm";
import { MilestoneCelebration } from "@/components/shared/MilestoneCelebration";
import { useAssessment } from "@/hooks/useAssessmentDetail";
import { useAssessmentPermissions } from "@/hooks/useAssessmentPermissions";
import { useAuditDashboard } from "@/hooks/useAuditDashboard";
import {
  useGuidedCatalog,
  useGuidedSession,
  usePatchGuidedSession,
  useUpsertGuidedAnswer,
} from "@/hooks/useGuidedAssessment";
import { labelAssessmentType } from "@/lib/labels";
import { visibleGuidedQuestions } from "@/lib/guidedShowWhen";

const CONTEXT_STEPS: GuidedStep[] = [
  "organization",
  "qms_scope",
  "products_services",
  "sites",
  "processes",
  "stakeholders",
];

export function AssessmentGuidedPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const assessment = useAssessment(assessmentId);
  const dash = useAuditDashboard(assessmentId);
  const catalog = useGuidedCatalog();
  const sessionQ = useGuidedSession(assessmentId);
  const perms = useAssessmentPermissions(assessment.data?.status);
  const patch = usePatchGuidedSession(assessmentId ?? "");
  const upsert = useUpsertGuidedAnswer(assessmentId ?? "");

  const [localContext, setLocalContext] = useState<GuidedContext | null>(null);
  const [step, setStep] = useState<GuidedStep>("organization");
  const [questionIdx, setQuestionIdx] = useState(0);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">(
    "idle",
  );
  const [celebration, setCelebration] = useState<{
    title: string;
    nextStepText: string;
  } | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hydrated = useRef(false);

  const session = sessionQ.data;
  const questions = useMemo(
    () =>
      visibleGuidedQuestions(
        catalog.data?.questions ?? [],
        session?.answers,
      ),
    [catalog.data?.questions, session?.answers],
  );

  useEffect(() => {
    if (!session || hydrated.current) return;
    hydrated.current = true;
    setLocalContext(session.context);
    setStep(session.current_step);
    if (session.current_question_id) {
      const i = questions.findIndex((q) => q.id === session.current_question_id);
      if (i >= 0) setQuestionIdx(i);
    } else if (session.answered_count > 0) {
      const firstOpen = questions.findIndex(
        (q) => !session.answers.some((a) => a.question_id === q.id && a.answer_value),
      );
      if (firstOpen >= 0) setQuestionIdx(firstOpen);
    }
  }, [session, questions]);

  useEffect(() => {
    if (questionIdx >= questions.length && questions.length > 0) {
      setQuestionIdx(questions.length - 1);
    }
  }, [questions.length, questionIdx]);

  // Reset hydrate when assessment changes
  useEffect(() => {
    hydrated.current = false;
  }, [assessmentId]);

  const currentQuestion = questions[questionIdx];
  const answerMap = useMemo(() => {
    const m = new Map((session?.answers ?? []).map((a) => [a.question_id, a]));
    return m;
  }, [session?.answers]);

  const stepMeta = GUIDED_STEPS.find((s) => s.id === step);

  async function persistContext(
    next: GuidedContext,
    nextStep?: GuidedStep,
    questionId?: string | null,
  ) {
    if (!assessmentId || !perms.canMutate) return;
    setSaveState("saving");
    try {
      await patch.mutateAsync({
        context: next,
        current_step: nextStep ?? step,
        current_question_id: questionId,
      });
      setSaveState("saved");
    } catch {
      setSaveState("error");
    }
  }

  function scheduleContextSave(next: GuidedContext) {
    setLocalContext(next);
    if (!perms.canMutate) return;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      void persistContext(next);
    }, 600);
  }

  async function goToStep(next: GuidedStep, qid?: string | null) {
    setStep(next);
    if (localContext) {
      await persistContext(localContext, next, qid);
    } else if (assessmentId && perms.canMutate) {
      setSaveState("saving");
      try {
        await patch.mutateAsync({
          current_step: next,
          current_question_id: qid,
        });
        setSaveState("saved");
      } catch {
        setSaveState("error");
      }
    }
  }

  async function saveAnswer(body: GuidedAnswerUpsert) {
    if (!currentQuestion || !assessmentId) return;
    setSaveState("saving");
    try {
      await upsert.mutateAsync({ questionId: currentQuestion.id, body });
      setSaveState("saved");
    } catch {
      setSaveState("error");
      throw new Error("save_failed");
    }
  }

  if (!assessmentId) {
    return (
      <GuidedEmptyState
        title="Avaliação não encontrada"
        why="O link pode estar incompleto."
        example="As avaliações aparecem em “Minhas avaliações” com fase e próxima ação."
        howToStart="Volte à lista e abra a avaliação desejada."
        action={{ label: "Ir para minhas avaliações", to: "/assessments" }}
      />
    );
  }

  if (assessment.isLoading || sessionQ.isLoading || catalog.isLoading) {
    return <LoadingPanel title="Preparando o roteiro guiado…" />;
  }

  if (assessment.isError || sessionQ.isError || catalog.isError) {
    const err = assessment.error ?? sessionQ.error ?? catalog.error;
    if (err instanceof QmindApiError && (err.status === 401 || err.status === 403)) {
      return <AccessDeniedPanel message={err.message} />;
    }
    return (
      <ApiErrorBanner
        title="Não foi possível abrir o roteiro guiado"
        error={err}
        onRetry={() => {
          void assessment.refetch();
          void sessionQ.refetch();
          void catalog.refetch();
        }}
      />
    );
  }

  const a = assessment.data!;
  const ctx = localContext ?? session!.context;
  const readOnly = !perms.canMutate;

  return (
    <section
      className="-mx-4 -mt-8 min-h-[70vh] space-y-6 bg-qmind-app pb-10 sm:-mx-0 sm:rounded-qmind-md"
      data-testid="guided-wizard"
    >
      <JourneyBar
        status={a.status}
        preparationReady={false}
        percent={dash.percent}
        pendingCount={dash.pending.length}
        pending={dash.pending}
        assessmentId={assessmentId}
      />

      <div className="mx-auto max-w-5xl space-y-6 px-4 sm:px-6">
        <p className="text-sm text-qmind-text-muted">
          <Link to="/assessments" className="hover:underline">
            Minhas avaliações
          </Link>
          {" / "}
          <Link to={`/assessments/${assessmentId}`} className="hover:underline">
            Mapa
          </Link>
          {" / "}
          Preparação
        </p>

        <PageHeader
          eyebrow="Fase · Preparação"
          title={`${labelAssessmentType(a.type)}`}
          explanation="Você está na preparação da avaliação. Vamos descrever a organização e responder a um roteiro em linguagem de negócio. Pode sair a qualquer momento: o progresso fica salvo."
          expectedResult="Contexto claro e roteiro inicial pronto para a próxima fase do mapa."
          progress={
            step === "route"
              ? `Perguntas: ${session!.answered_count} de ${session!.question_count} · percurso geral ${dash.percent}%`
              : `Etapa: ${stepMeta?.label ?? "—"} · percurso geral ${dash.percent}%`
          }
          nextStep={
            step === "review"
              ? "Revisar o resumo e voltar ao mapa"
              : "Preencher e avançar"
          }
        />

        <GuidedProgress
          currentStep={step}
          routeProgress={
            step === "route"
              ? {
                  answered: session!.answered_count,
                  total: session!.question_count,
                }
              : undefined
          }
        />

        {celebration ? (
          <MilestoneCelebration
            title={celebration.title}
            nextStepText={celebration.nextStepText}
            onContinue={() => setCelebration(null)}
          />
        ) : null}

        <div className="rounded-qmind-md bg-qmind-surface p-6 shadow-qmind-card sm:p-8">
          {stepMeta ? (
            <header className="mb-6 border-b border-qmind-semantic-future pb-5">
              <SectionIntroduction
                title={stepMeta.label}
                body={stepMeta.hint}
                expectedResult={
                  step === "review"
                    ? "Confirmar o que foi preenchido antes de seguir no mapa."
                    : step === "route"
                      ? "Pergunta respondida com clareza; evidência tratada ou marcada para depois."
                      : "Informação suficiente para a próxima etapa da preparação."
                }
              />
              {step !== "route" ? (
                <p className="mt-3 text-right" data-testid="save-state">
                  {saveState === "saving" ? (
                    <span className="text-sm text-qmind-text-muted">
                      Salvando rascunho...
                    </span>
                  ) : saveState === "saved" ? (
                    <span className="text-sm font-medium text-qmind-semantic-success">
                      ✓ Salvo
                    </span>
                  ) : saveState === "error" ? (
                    <span className="text-sm font-medium text-qmind-semantic-danger">
                      Erro ao salvar
                    </span>
                  ) : null}
                </p>
              ) : null}
            </header>
          ) : null}

          {CONTEXT_STEPS.includes(step) ? (
            <GuidedContextSteps
              step={step}
              context={ctx}
              readOnly={readOnly}
              onChange={scheduleContextSave}
            />
          ) : null}

          {step === "route" && currentQuestion ? (
            <div className="space-y-5">
              <GuidedClauseNav
                questions={questions}
                currentQuestionId={currentQuestion.id}
                clauseGroups={catalog.data?.clause_groups}
                onSelectQuestion={(idx) => {
                  setQuestionIdx(idx);
                  void goToStep("route", questions[idx]?.id ?? null);
                }}
              />
              <GuidedRouteStep
                assessmentId={assessmentId}
                question={currentQuestion}
                questionIndex={questionIdx}
                questionTotal={questions.length}
                answer={answerMap.get(currentQuestion.id)}
                readOnly={readOnly}
                saving={upsert.isPending}
                saveState={saveState}
                onSave={saveAnswer}
              />
            </div>
          ) : null}

          {step === "route" && !currentQuestion ? (
            <GuidedEmptyState
              title="Roteiro temporariamente indisponível"
              why="As perguntas desta preparação não carregaram neste momento."
              example="O roteiro traz perguntas em linguagem de negócio sobre contexto e liderança."
              howToStart="Volte ao mapa e abra a preparação de novo — o contexto já preenchido permanece salvo."
              action={{
                label: "Voltar ao mapa",
                to: `/assessments/${assessmentId}`,
              }}
            />
          ) : null}

          {step === "review" ? (
            <GuidedReview
              session={session!}
              questions={questions}
              clauseGroups={catalog.data?.clause_groups}
            />
          ) : null}

          <nav className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-qmind-semantic-future pt-5">
            <button
              type="button"
              className="qm-btn-secondary"
              data-testid="guided-back"
              disabled={step === "organization" && questionIdx === 0}
              onClick={() => {
                setCelebration(null);
                if (step === "route" && questionIdx > 0) {
                  const nextIdx = questionIdx - 1;
                  setQuestionIdx(nextIdx);
                  void goToStep("route", questions[nextIdx]?.id ?? null);
                  return;
                }
                if (step === "route") {
                  void goToStep("stakeholders");
                  return;
                }
                if (step === "review") {
                  void goToStep("route", questions[questions.length - 1]?.id ?? null);
                  setQuestionIdx(Math.max(questions.length - 1, 0));
                  return;
                }
                const i = CONTEXT_STEPS.indexOf(step);
                if (i > 0) void goToStep(CONTEXT_STEPS[i - 1]!);
              }}
            >
              Voltar
            </button>

            {step !== "review" ? (
              <button
                type="button"
                className="qm-btn-primary"
                data-testid="guided-next"
                onClick={() => {
                  if (CONTEXT_STEPS.includes(step)) {
                    const i = CONTEXT_STEPS.indexOf(step);
                    if (i < CONTEXT_STEPS.length - 1) {
                      void goToStep(CONTEXT_STEPS[i + 1]!);
                      return;
                    }
                    setCelebration({
                      title: "Contexto validado com sucesso",
                      nextStepText:
                        "Próxima etapa: responder o roteiro em linguagem de negócio.",
                    });
                    setQuestionIdx(0);
                    void goToStep("route", questions[0]?.id ?? null);
                    return;
                  }
                  if (step === "route") {
                    const ans = answerMap.get(currentQuestion?.id ?? "");
                    const localOk =
                      ans?.answer_value &&
                      (ans.answer_value !== "not_applicable" ||
                        !!ans.na_justification?.trim());
                    if (!localOk && !readOnly) {
                      setSaveState("error");
                      return;
                    }
                    if (questionIdx < questions.length - 1) {
                      const nextIdx = questionIdx + 1;
                      setQuestionIdx(nextIdx);
                      void goToStep("route", questions[nextIdx]?.id ?? null);
                      return;
                    }
                    setCelebration({
                      title: "Roteiro validado com sucesso",
                      nextStepText:
                        "Próxima etapa: revisar o resumo e seguir no mapa da avaliação.",
                    });
                    void goToStep("review", null);
                  }
                }}
              >
                {step === "route" && questionIdx >= questions.length - 1
                  ? "Ir para revisão"
                  : "Avançar"}
              </button>
            ) : (
              <Link
                to={`/assessments/${assessmentId}/work`}
                className="qm-btn-primary"
                data-testid="guided-done"
              >
                Concluir preparação e ir ao Planejamento
              </Link>
            )}
          </nav>
        </div>
      </div>
    </section>
  );
}
