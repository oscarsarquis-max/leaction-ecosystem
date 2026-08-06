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
import { GuidedClauseOpening } from "@/components/guided/GuidedClauseOpening";
import { GuidedClauseSummary } from "@/components/guided/GuidedClauseSummary";
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
import {
  buildClauseNarrative,
  clauseHasAnswers,
  firstQuestionIndexForClause,
  getConsultiveOpening,
  lastQuestionIndexForClause,
} from "@/lib/guidedNarrative";
import { clauseMajor, visibleGuidedQuestions } from "@/lib/guidedShowWhen";

const CONTEXT_STEPS: GuidedStep[] = [
  "organization",
  "qms_scope",
  "products_services",
  "sites",
  "processes",
  "stakeholders",
];

type RoutePhase = "opening" | "question" | "summary";

export function AssessmentGuidedPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const assessment = useAssessment(assessmentId);
  const dash = useAuditDashboard(assessmentId);
  const sessionQ = useGuidedSession(assessmentId);
  const catalog = useGuidedCatalog(sessionQ.data?.catalog_version);
  const perms = useAssessmentPermissions(assessment.data?.status);
  const patch = usePatchGuidedSession(assessmentId ?? "");
  const upsert = useUpsertGuidedAnswer(assessmentId ?? "");

  const [localContext, setLocalContext] = useState<GuidedContext | null>(null);
  const [step, setStep] = useState<GuidedStep>("organization");
  const [questionIdx, setQuestionIdx] = useState(0);
  const [routePhase, setRoutePhase] = useState<RoutePhase>("opening");
  const [summaryMajor, setSummaryMajor] = useState<string | null>(null);
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
        localContext ?? session?.context,
      ),
    [catalog.data?.questions, session?.answers, session?.context, localContext],
  );

  useEffect(() => {
    if (!session || hydrated.current) return;
    hydrated.current = true;
    setLocalContext(session.context);
    setStep(session.current_step);
    if (session.current_step === "route") {
      if (session.current_question_id) {
        const i = questions.findIndex((q) => q.id === session.current_question_id);
        if (i >= 0) {
          setQuestionIdx(i);
          setRoutePhase("question");
          return;
        }
      }
      if (session.answered_count > 0) {
        const firstOpen = questions.findIndex(
          (q) =>
            !session.answers.some((a) => a.question_id === q.id && a.answer_value),
        );
        const idx = firstOpen >= 0 ? firstOpen : 0;
        setQuestionIdx(idx);
        const major = clauseMajor(questions[idx]?.clause_ref ?? "4");
        setRoutePhase(
          clauseHasAnswers(questions, session.answers, major) ? "question" : "opening",
        );
        return;
      }
      setQuestionIdx(0);
      setRoutePhase("opening");
    }
  }, [session, questions]);

  useEffect(() => {
    if (questions.length === 0) return;
    if (questions[questionIdx]) return;
    const resumeId = session?.current_question_id;
    if (resumeId) {
      const i = questions.findIndex((q) => q.id === resumeId);
      if (i >= 0) {
        setQuestionIdx(i);
        return;
      }
    }
    setQuestionIdx(Math.max(0, questions.length - 1));
  }, [questions, questionIdx, session?.current_question_id]);

  useEffect(() => {
    hydrated.current = false;
  }, [assessmentId]);

  const currentQuestion = questions[questionIdx];
  const activeMajor =
    summaryMajor ??
    (currentQuestion ? clauseMajor(currentQuestion.clause_ref) : "4");
  const opening = getConsultiveOpening(activeMajor);
  const clauseNarrative = useMemo(
    () =>
      buildClauseNarrative(
        summaryMajor ?? activeMajor,
        questions,
        session?.answers,
        catalog.data?.clause_groups,
      ),
    [
      summaryMajor,
      activeMajor,
      questions,
      session?.answers,
      catalog.data?.clause_groups,
    ],
  );

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

  function enterClause(major: string, preferOpening: boolean) {
    const first = firstQuestionIndexForClause(questions, major);
    if (first < 0) return;
    setSummaryMajor(null);
    setQuestionIdx(first);
    const has = clauseHasAnswers(questions, session?.answers, major);
    setRoutePhase(preferOpening && !has ? "opening" : "question");
    void goToStep("route", questions[first]?.id ?? null);
  }

  function goToFirstPending() {
    const pendingIdx = questions.findIndex(
      (q) => !session?.answers.some((a) => a.question_id === q.id && a.answer_value),
    );
    if (pendingIdx < 0) {
      setRoutePhase("question");
      return;
    }
    setSummaryMajor(null);
    setQuestionIdx(pendingIdx);
    setRoutePhase("question");
    setStep("route");
    void goToStep("route", questions[pendingIdx]?.id ?? null);
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
  const hideBottomNav =
    step === "review" ||
    (step === "route" && (routePhase === "opening" || routePhase === "summary"));

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
          explanation="Você está na preparação da avaliação. Descrevemos a organização e percorremos um roteiro consultivo nas cláusulas 4–10, em linguagem de negócio. Pode sair a qualquer momento: o progresso fica salvo."
          expectedResult="Contexto claro, etapas compreendidas e roteiro pronto para a execução em campo."
          progress={
            step === "route"
              ? `Perguntas aplicáveis: ${session!.answered_count} de ${session!.question_count} · percurso geral ${dash.percent}%`
              : `Etapa: ${stepMeta?.label ?? "—"} · percurso geral ${dash.percent}%`
          }
          nextStep={
            step === "review"
              ? "Revisar o resumo e seguir para o campo"
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
          {stepMeta && routePhase === "question" ? (
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

          {step === "route" ? (
            <div className="space-y-5">
              <GuidedClauseNav
                questions={questions}
                answers={session?.answers}
                currentQuestionId={currentQuestion?.id}
                clauseGroups={catalog.data?.clause_groups}
                onSelectQuestion={(idx) => {
                  const major = clauseMajor(questions[idx]?.clause_ref ?? "4");
                  enterClause(major, true);
                }}
              />

              {routePhase === "opening" && opening ? (
                <GuidedClauseOpening
                  opening={opening}
                  onStart={() => {
                    setRoutePhase("question");
                    const first = firstQuestionIndexForClause(questions, activeMajor);
                    if (first >= 0) {
                      setQuestionIdx(first);
                      void goToStep("route", questions[first]?.id ?? null);
                    }
                  }}
                />
              ) : null}

              {routePhase === "summary" ? (
                <GuidedClauseSummary
                  narrative={clauseNarrative}
                  onBackToQuestions={() => {
                    setSummaryMajor(null);
                    setRoutePhase("question");
                  }}
                  onReviewPending={() => {
                    const major = clauseNarrative.major;
                    const pendingIdx = questions.findIndex(
                      (q) =>
                        clauseMajor(q.clause_ref) === major &&
                        !session?.answers.some(
                          (a) => a.question_id === q.id && a.answer_value,
                        ),
                    );
                    setSummaryMajor(null);
                    setRoutePhase("question");
                    if (pendingIdx >= 0) {
                      setQuestionIdx(pendingIdx);
                      void goToStep("route", questions[pendingIdx]?.id ?? null);
                    }
                  }}
                  onContinue={() => {
                    const next = clauseNarrative.nextClauseMajor;
                    if (!next) {
                      setCelebration({
                        title: "Roteiro percorrido",
                        nextStepText:
                          "Próxima etapa: revisão final consultiva e seguimento no mapa.",
                      });
                      setSummaryMajor(null);
                      void goToStep("review", null);
                      return;
                    }
                    enterClause(next, true);
                  }}
                />
              ) : null}

              {routePhase === "question" && currentQuestion ? (
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
              ) : null}

              {routePhase === "question" && !currentQuestion ? (
                <GuidedEmptyState
                  title="Roteiro temporariamente indisponível"
                  why="As perguntas desta preparação não carregaram neste momento."
                  example="O roteiro cobre as cláusulas 4–10 em linguagem de negócio."
                  howToStart="Volte ao mapa e abra a preparação de novo — o contexto já preenchido permanece salvo."
                  action={{
                    label: "Voltar ao mapa",
                    to: `/assessments/${assessmentId}`,
                  }}
                />
              ) : null}
            </div>
          ) : null}

          {step === "review" ? (
            <GuidedReview
              session={session!}
              questions={questions}
              clauseGroups={catalog.data?.clause_groups}
              assessmentId={assessmentId}
              onGoToClause={(major) => {
                setStep("route");
                enterClause(major, false);
              }}
              onReviewPending={goToFirstPending}
            />
          ) : null}

          {!hideBottomNav ? (
            <nav className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-qmind-semantic-future pt-5">
              <button
                type="button"
                className="qm-btn-secondary"
                data-testid="guided-back"
                disabled={step === "organization" && questionIdx === 0}
                onClick={() => {
                  setCelebration(null);
                  if (step === "route" && questionIdx > 0) {
                    const prevMajor = clauseMajor(
                      questions[questionIdx]?.clause_ref ?? "",
                    );
                    const nextIdx = questionIdx - 1;
                    const nextMajor = clauseMajor(
                      questions[nextIdx]?.clause_ref ?? "",
                    );
                    if (nextMajor !== prevMajor) {
                      setSummaryMajor(prevMajor);
                      setRoutePhase("summary");
                      return;
                    }
                    setQuestionIdx(nextIdx);
                    void goToStep("route", questions[nextIdx]?.id ?? null);
                    return;
                  }
                  if (step === "route") {
                    void goToStep("stakeholders");
                    return;
                  }
                  const i = CONTEXT_STEPS.indexOf(step);
                  if (i > 0) void goToStep(CONTEXT_STEPS[i - 1]!);
                }}
              >
                Voltar
              </button>

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
                        "Próxima etapa: roteiro consultivo das cláusulas 4–10.",
                    });
                    setQuestionIdx(0);
                    setRoutePhase("opening");
                    void goToStep("route", questions[0]?.id ?? null);
                    return;
                  }
                  if (step === "route" && currentQuestion) {
                    const ans = answerMap.get(currentQuestion.id);
                    const localOk =
                      ans?.answer_value &&
                      (ans.answer_value !== "not_applicable" ||
                        !!ans.na_justification?.trim());
                    if (!localOk && !readOnly) {
                      setSaveState("error");
                      return;
                    }
                    const major = clauseMajor(currentQuestion.clause_ref);
                    const lastInClause = lastQuestionIndexForClause(
                      questions,
                      major,
                    );
                    if (questionIdx >= lastInClause) {
                      setSummaryMajor(major);
                      setRoutePhase("summary");
                      return;
                    }
                    const nextIdx = questionIdx + 1;
                    setQuestionIdx(nextIdx);
                    void goToStep("route", questions[nextIdx]?.id ?? null);
                  }
                }}
              >
                {step === "route" &&
                currentQuestion &&
                questionIdx >=
                  lastQuestionIndexForClause(
                    questions,
                    clauseMajor(currentQuestion.clause_ref),
                  )
                  ? "Ver resumo da etapa"
                  : "Avançar"}
              </button>
            </nav>
          ) : null}
        </div>
      </div>
    </section>
  );
}
