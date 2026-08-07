import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import type { FieldCentralModel, FieldNextAction } from "@/lib/fieldCentralTypes";
import {
  useAssessmentEvidences,
  useAssessmentInterviews,
  useAssessmentQuestions,
  useBeginAssessmentAnalysis,
  useCancelInterviewMutation,
  useCompleteInterview,
  useCreateAnswer,
  useCreateInterview,
  useInterviewAnswers,
  useLinkEvidence,
  usePreviewEvidence,
  useStartInterviewMutation,
  useUploadEvidence,
} from "@/hooks/useFieldExecution";
import { useCreateScheduleMeeting } from "@/hooks/useAuditPlanSchedule";
import { labelInterviewMode, labelWorkflowStatus } from "@/lib/labels";
import {
  humanizeQuestionPrompt,
  isDemoOrTestQuestion,
} from "@/lib/humanizeAuditCopy";
import { validateEvidenceFile } from "@/lib/evidenceConstraints";
import type { EvidenceUploadPhase } from "@/lib/evidenceUpload";

type FocusTarget =
  | "opening"
  | "interview"
  | "evidence"
  | "unplanned"
  | "closing"
  | null;

function formatWhen(iso: string | null): string {
  if (!iso) return "Horário a definir";
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      timeZone: "America/Sao_Paulo",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function applyLocalAction(
  action: FieldNextAction,
  setFocus: (f: FocusTarget) => void,
  setInterviewId: (id: string | null) => void,
) {
  if (action.interviewId) setInterviewId(action.interviewId);
  switch (action.localAction) {
    case "focus_opening":
      setFocus("opening");
      break;
    case "focus_interview":
      setFocus("interview");
      break;
    case "focus_evidence":
      setFocus("evidence");
      break;
    case "focus_unplanned":
      setFocus("unplanned");
      break;
    case "focus_closing":
      setFocus("closing");
      break;
    default:
      break;
  }
}

export function FieldCentral({
  assessmentId,
  model,
  canEditField,
  canCollectEvidence,
}: {
  assessmentId: string;
  model: FieldCentralModel;
  canEditField: boolean;
  canCollectEvidence: boolean;
}) {
  const [focus, setFocus] = useState<FocusTarget>(null);
  const [selectedInterviewId, setSelectedInterviewId] = useState<string | null>(
    null,
  );
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (model.nextAction.interviewId) {
      setSelectedInterviewId(model.nextAction.interviewId);
    }
  }, [model.nextAction.interviewId]);

  if (model.mode === "draft_redirect") {
    return <DraftRedirect model={model} />;
  }
  if (model.mode === "planned_handoff") {
    return <PlannedHandoff model={model} />;
  }
  if (model.mode === "field_readonly") {
    return <FieldReadonlySummary model={model} assessmentId={assessmentId} />;
  }

  return (
    <div className="space-y-5" data-testid="field-central">
      {error ? <ApiErrorBanner error={error} /> : null}

      <NextActionPanel
        model={model}
        onLocal={(a) => applyLocalAction(a, setFocus, setSelectedInterviewId)}
      />

      <ProgressStrip model={model} />

      <TodayAgenda
        model={model}
        canEdit={canEditField}
        selectedInterviewId={selectedInterviewId}
        onSelectInterview={(id) => {
          setSelectedInterviewId(id);
          setFocus("interview");
        }}
        onError={setError}
        assessmentId={assessmentId}
      />

      {selectedInterviewId ? (
        <InterviewWorkspace
          assessmentId={assessmentId}
          interviewId={selectedInterviewId}
          canEdit={canEditField}
          onClose={() => {
            setSelectedInterviewId(null);
            setFocus(null);
          }}
          onError={setError}
        />
      ) : null}

      <EvidenceSection
        assessmentId={assessmentId}
        model={model}
        canCollect={canCollectEvidence}
        interviewId={selectedInterviewId}
        highlighted={focus === "evidence"}
        onError={setError}
      />

      <PendenciesList
        model={model}
        onLocal={(a) => applyLocalAction(a, setFocus, setSelectedInterviewId)}
      />

      {canEditField ? (
        <UnplannedActivity
          assessmentId={assessmentId}
          highlighted={focus === "unplanned"}
          onCreated={(id) => {
            setSelectedInterviewId(id);
            setFocus("interview");
          }}
          onError={setError}
        />
      ) : null}

      {model.closingPrep.show || focus === "closing" ? (
        <ClosingPrepBlock model={model} assessmentId={assessmentId} />
      ) : null}
    </div>
  );
}

function DraftRedirect({ model }: { model: FieldCentralModel }) {
  return (
    <section
      className="rounded-md border border-[var(--qm-line)] bg-[var(--qm-surface)] px-4 py-5"
      data-testid="field-draft-redirect"
    >
      <h2 className="font-display text-xl text-[var(--qm-ink)]">
        Ainda não é hora do campo
      </h2>
      <p className="mt-2 text-sm text-[var(--qm-muted)]">
        Esta avaliação está em preparação. Elabore o Plano da Auditoria antes de
        abrir a Central de Campo.
      </p>
      <Link
        to={model.nextAction.href!}
        className="qm-btn-primary mt-4 inline-flex"
        data-testid="field-cta-audit-plan"
      >
        {model.nextAction.label}
      </Link>
    </section>
  );
}

function PlannedHandoff({ model }: { model: FieldCentralModel }) {
  return (
    <section
      className="space-y-4 rounded-md border border-[var(--qm-line)] bg-[var(--qm-surface)] px-4 py-5"
      data-testid="field-planned-handoff"
    >
      <div>
        <h2 className="font-display text-xl text-[var(--qm-ink)]">
          Execução ainda não começou
        </h2>
        <p className="mt-2 text-sm text-[var(--qm-muted)]">
          A avaliação está planejada. Confirme abertura e inicie o campo pelo
          Plano da Auditoria — único caminho oficial.
        </p>
      </div>
      <ul className="space-y-2 text-sm">
        <li>
          <span className="font-semibold">Plano: </span>
          {model.planStatusLabel}
        </li>
        <li>
          <span className="font-semibold">Reunião de abertura: </span>
          {model.openingStatusLabel ?? "Não programada"}
        </li>
      </ul>
      <NextActionPanel model={model} />
      {model.pendencies.length > 0 ? <PendenciesList model={model} /> : null}
    </section>
  );
}

function FieldReadonlySummary({
  model,
  assessmentId,
}: {
  model: FieldCentralModel;
  assessmentId: string;
}) {
  return (
    <section
      className="space-y-4 rounded-md border border-[var(--qm-line)] bg-[var(--qm-surface)] px-4 py-5"
      data-testid="field-readonly"
    >
      <div>
        <h2 className="font-display text-xl text-[var(--qm-ink)]">
          Campo encerrado — visão em leitura
        </h2>
        <p className="mt-2 text-sm text-[var(--qm-muted)]">
          A execução em campo foi concluída. Controles de mutação ficam
          desabilitados; use a próxima ação para a fase atual.
        </p>
      </div>
      <NextActionPanel model={model} />
      <ProgressStrip model={model} />
      {model.pendencies.length > 0 ? <PendenciesList model={model} /> : null}
      <div className="flex flex-wrap gap-2">
        <Link
          to={model.nextAction.href || `/assessments/${assessmentId}/advanced`}
          className="qm-btn-primary inline-flex"
          data-testid="field-readonly-continue"
        >
          {model.nextAction.label}
        </Link>
        <Link
          to={`/assessments/${assessmentId}`}
          className="qm-btn-secondary inline-flex text-sm"
        >
          Abrir mapa da avaliação
        </Link>
      </div>
    </section>
  );
}

function NextActionPanel({
  model,
  onLocal,
}: {
  model: FieldCentralModel;
  onLocal?: (a: FieldNextAction) => void;
}) {
  const a = model.nextAction;
  const navigateOnly = !!a.href && !a.localAction;
  return (
    <section
      className="sticky top-2 z-10 rounded-md border border-[var(--qm-ink)]/15 bg-[var(--qm-surface)] px-4 py-4 shadow-sm"
      data-testid="field-next-action"
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--qm-muted)]">
        Próxima melhor ação
      </p>
      <p className="mt-1 font-display text-lg text-[var(--qm-ink)]">{a.label}</p>
      <p className="mt-1 text-sm text-[var(--qm-muted)]">{a.hint}</p>
      <div className="mt-3">
        {navigateOnly ? (
          <Link to={a.href!} className="qm-btn-primary inline-flex">
            {a.label}
          </Link>
        ) : a.href && a.localAction ? (
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="qm-btn-primary"
              data-testid="field-next-action-button"
              onClick={() => onLocal?.(a)}
            >
              {a.label}
            </button>
            <Link to={a.href} className="qm-btn-secondary inline-flex text-sm">
              Abrir no Plano
            </Link>
          </div>
        ) : (
          <button
            type="button"
            className="qm-btn-primary"
            data-testid="field-next-action-button"
            onClick={() => onLocal?.(a)}
          >
            {a.label}
          </button>
        )}
      </div>
    </section>
  );
}

function ProgressStrip({ model }: { model: FieldCentralModel }) {
  return (
    <div
      className="rounded-md border border-[var(--qm-line)] px-3 py-3 text-sm"
      data-testid="field-progress"
    >
      <p className="font-semibold text-[var(--qm-ink)]">Progresso do campo</p>
      <p className="mt-1 text-[var(--qm-muted)]">{model.progress.summary}</p>
      <div className="mt-2 grid gap-2 sm:grid-cols-3">
        <Metric
          label="Entrevistas"
          value={`${model.progress.interviewsDone}/${model.progress.interviewsPlanned || "—"}`}
        />
        <Metric
          label="Processos"
          value={`${model.progress.processesCovered}/${model.progress.processesPlanned || "—"}`}
        />
        <Metric
          label="Evidências ok"
          value={String(model.progress.evidencesReady)}
        />
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-[var(--qm-line)] px-2 py-1.5">
      <p className="text-lg font-semibold text-[var(--qm-ink)]">{value}</p>
      <p className="text-[11px] text-[var(--qm-muted)]">{label}</p>
    </div>
  );
}

function TodayAgenda({
  model,
  canEdit,
  selectedInterviewId,
  onSelectInterview,
  onError,
  assessmentId,
}: {
  model: FieldCentralModel;
  canEdit: boolean;
  selectedInterviewId: string | null;
  onSelectInterview: (id: string) => void;
  onError: (e: unknown) => void;
  assessmentId: string;
}) {
  const startIv = useStartInterviewMutation(assessmentId);
  const cancelIv = useCancelInterviewMutation(assessmentId);
  const [cancelId, setCancelId] = useState<string | null>(null);
  const [cancelReason, setCancelReason] = useState("");

  return (
    <section
      className="space-y-3 rounded-md border border-[var(--qm-line)] bg-[var(--qm-surface)] px-4 py-4"
      data-testid="field-today-agenda"
    >
      <div>
        <h2 className="font-display text-lg text-[var(--qm-ink)]">
          Agenda de hoje
        </h2>
        <p className="text-sm text-[var(--qm-muted)]">
          {model.todayLabel} — o que executar agora (não é o calendário
          completo).
        </p>
      </div>

      {model.todayItems.length === 0 ? (
        <p className="text-sm text-[var(--qm-muted)]" data-testid="field-today-empty">
          Nenhuma atividade para hoje. Registre algo não planejado se precisar.
        </p>
      ) : (
        <ul className="space-y-2">
          {model.todayItems.map((item) => (
            <li
              key={`${item.kind}-${item.id}`}
              className={`rounded-md border px-3 py-3 text-sm ${
                item.done
                  ? "border-[var(--qm-line)] opacity-60"
                  : "border-[var(--qm-ink)]/20 bg-[var(--qm-surface-soft)]"
              }`}
              data-testid={`field-today-item-${item.id}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--qm-muted)]">
                    {formatWhen(item.startsAt)} ·{" "}
                    {item.kind === "interview"
                      ? "Entrevista"
                      : item.planActivityKind === "opening_meeting"
                        ? "Abertura"
                        : item.kind === "meeting"
                          ? "Reunião"
                          : "Marco"}
                  </p>
                  <p className="font-semibold text-[var(--qm-ink)]">{item.title}</p>
                  <p className="text-[var(--qm-muted)]">{item.statusLabel}</p>
                  {item.processName ? (
                    <p className="text-[var(--qm-muted)]">
                      Processo: {item.processName}
                    </p>
                  ) : null}
                  {item.locationOrLink ? (
                    <p className="break-all text-[var(--qm-muted)]">
                      Onde: {item.locationOrLink}
                    </p>
                  ) : null}
                  {item.preparation ? (
                    <p className="text-[var(--qm-muted)]">
                      Preparar: {item.preparation}
                    </p>
                  ) : null}
                </div>
                <div className="flex flex-wrap gap-2">
                  {item.interviewId ? (
                    <button
                      type="button"
                      className="qm-btn-primary text-sm"
                      disabled={startIv.isPending}
                      onClick={() => {
                        const id = item.interviewId!;
                        if (
                          item.status === "planned" ||
                          item.status === "confirmed"
                        ) {
                          void startIv
                            .mutateAsync(id)
                            .then(() => onSelectInterview(id))
                            .catch(onError);
                        } else {
                          onSelectInterview(id);
                        }
                      }}
                    >
                      {item.primaryLabel}
                    </button>
                  ) : item.planActivityKind === "opening_meeting" ? (
                    <Link
                      to={`/assessments/${assessmentId}/audit-plan`}
                      className="qm-btn-primary inline-flex text-sm"
                    >
                      {item.primaryLabel}
                    </Link>
                  ) : null}
                  {canEdit &&
                  item.interviewId &&
                  !item.done &&
                  item.status !== "completed" ? (
                    <button
                      type="button"
                      className="qm-btn-secondary text-sm"
                      onClick={() => setCancelId(item.interviewId)}
                    >
                      Cancelar…
                    </button>
                  ) : null}
                </div>
              </div>
              {cancelId === item.interviewId ? (
                <div className="mt-2 space-y-2">
                  <input
                    className="qm-field"
                    placeholder="Motivo do cancelamento"
                    value={cancelReason}
                    onChange={(e) => setCancelReason(e.target.value)}
                    data-testid="field-cancel-reason"
                  />
                  <button
                    type="button"
                    className="qm-btn-primary text-sm"
                    disabled={
                      cancelReason.trim().length < 4 || cancelIv.isPending
                    }
                    onClick={() =>
                      void cancelIv
                        .mutateAsync({
                          interviewId: item.interviewId!,
                          reason: cancelReason,
                        })
                        .then(() => {
                          setCancelId(null);
                          setCancelReason("");
                        })
                        .catch(onError)
                    }
                  >
                    Confirmar cancelamento
                  </button>
                </div>
              ) : null}
              {selectedInterviewId === item.interviewId ? (
                <p className="mt-2 text-xs font-semibold text-[var(--qm-ink)]">
                  Em foco abaixo
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function InterviewWorkspace({
  assessmentId,
  interviewId,
  canEdit,
  onClose,
  onError,
}: {
  assessmentId: string;
  interviewId: string;
  canEdit: boolean;
  onClose: () => void;
  onError: (e: unknown) => void;
}) {
  const ivList = useAssessmentInterviews(assessmentId);
  const iv = useMemo(
    () => ivList.data?.find((i) => i.id === interviewId) ?? null,
    [ivList.data, interviewId],
  );
  const answers = useInterviewAnswers(interviewId);
  const questions = useAssessmentQuestions(assessmentId);
  const createAnswer = useCreateAnswer(assessmentId, interviewId);
  const complete = useCompleteInterview(assessmentId);
  const startIv = useStartInterviewMutation(assessmentId);
  const [body, setBody] = useState("");
  const [questionId, setQuestionId] = useState("");

  const status = iv?.status ?? "planned";
  const canStart =
    canEdit && (status === "planned" || status === "confirmed");
  const canAnswer = canEdit && status === "in_progress";
  const recommendedQuestions = useMemo(
    () =>
      (questions.data ?? []).filter(
        (q) => !isDemoOrTestQuestion(q.code, q.prompt_text),
      ),
    [questions.data],
  );

  return (
    <section
      className="space-y-3 rounded-md border border-[var(--qm-ink)]/20 bg-[var(--qm-surface)] px-4 py-4"
      data-testid="field-interview-workspace"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="font-display text-lg text-[var(--qm-ink)]">
            Entrevista orientada
          </h2>
          <p className="text-sm text-[var(--qm-muted)]">
            {iv?.title || iv?.process_name || "Entrevista"} ·{" "}
            {labelWorkflowStatus(status)}
            {iv?.mode ? ` · ${labelInterviewMode(iv.mode)}` : ""}
          </p>
        </div>
        <button type="button" className="qm-btn-secondary text-sm" onClick={onClose}>
          Voltar à central
        </button>
      </div>

      <dl className="grid gap-2 text-sm sm:grid-cols-2">
        <div>
          <dt className="font-semibold">Objetivo</dt>
          <dd className="text-[var(--qm-muted)]">{iv?.objective || "—"}</dd>
        </div>
        <div>
          <dt className="font-semibold">Processo</dt>
          <dd className="text-[var(--qm-muted)]">{iv?.process_name || "—"}</dd>
        </div>
        <div>
          <dt className="font-semibold">Contato</dt>
          <dd className="text-[var(--qm-muted)]">{iv?.org_contact_name || "—"}</dd>
        </div>
        <div>
          <dt className="font-semibold">Preparação</dt>
          <dd className="text-[var(--qm-muted)]">{iv?.preparation || "—"}</dd>
        </div>
      </dl>

      <p className="text-sm text-[var(--qm-muted)]">
        {(answers.data?.length ?? 0)} resposta(s)
        {recommendedQuestions.length > 0
          ? ` · ${recommendedQuestions.length} perguntas sugeridas`
          : ""}
      </p>

      {recommendedQuestions.length > 0 ? (
        <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--qm-muted)]">
          {recommendedQuestions.slice(0, 8).map((q) => (
            <li key={q.id}>{humanizeQuestionPrompt(q.code, q.prompt_text)}</li>
          ))}
        </ul>
      ) : null}

      <ul className="space-y-2 text-sm" data-testid="field-answer-list">
        {(answers.data ?? []).map((a) => (
          <li
            key={a.id}
            className="rounded border border-[var(--qm-line)] px-3 py-2"
          >
            {a.body}
          </li>
        ))}
        {(answers.data?.length ?? 0) === 0 ? (
          <li className="text-[var(--qm-muted)]">Nenhuma resposta ainda.</li>
        ) : null}
      </ul>

      <div className="flex flex-wrap gap-2">
        {canStart ? (
          <button
            type="button"
            className="qm-btn-primary"
            disabled={startIv.isPending}
            data-testid="field-interview-start"
            onClick={() => void startIv.mutateAsync(interviewId).catch(onError)}
          >
            Iniciar entrevista
          </button>
        ) : null}
        {canAnswer ? (
          <button
            type="button"
            className="qm-btn-secondary"
            disabled={complete.isPending}
            data-testid="field-interview-complete"
            onClick={() =>
              void complete.mutateAsync(interviewId).then(onClose).catch(onError)
            }
          >
            Concluir entrevista
          </button>
        ) : null}
      </div>

      {canAnswer ? (
        <form
          className="space-y-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            if (!body.trim() || createAnswer.isPending) return;
            void createAnswer
              .mutateAsync({
                body: body.trim(),
                question_id: questionId || undefined,
              })
              .then(() => setBody(""))
              .catch(onError);
          }}
        >
          {recommendedQuestions.length > 0 ? (
            <label className="block text-sm">
              <span className="font-semibold">Pergunta (opcional)</span>
              <select
                className="qm-field mt-1"
                value={questionId}
                onChange={(e) => setQuestionId(e.target.value)}
              >
                <option value="">Observação livre</option>
                {recommendedQuestions.map((q) => (
                  <option key={q.id} value={q.id}>
                    {humanizeQuestionPrompt(q.code, q.prompt_text).slice(0, 100)}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <textarea
            className="qm-field min-h-24"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Registrar resposta ou observação"
            required
            data-testid="field-answer-body"
          />
          <button
            type="submit"
            className="qm-btn-primary"
            disabled={!body.trim() || createAnswer.isPending}
            data-testid="field-answer-submit"
          >
            Registrar resposta
          </button>
        </form>
      ) : canStart ? (
        <p className="text-sm text-[var(--qm-muted)]">
          Inicie a entrevista para registrar respostas. O Assistente QMind explica o
          objetivo desta conversa.
        </p>
      ) : (
        <p className="text-sm text-[var(--qm-muted)]">
          Entrevista somente leitura neste estado.
        </p>
      )}
    </section>
  );
}

function EvidenceSection({
  assessmentId,
  model,
  canCollect,
  interviewId,
  highlighted,
  onError,
}: {
  assessmentId: string;
  model: FieldCentralModel;
  canCollect: boolean;
  interviewId: string | null;
  highlighted: boolean;
  onError: (e: unknown) => void;
}) {
  const evidences = useAssessmentEvidences(assessmentId);
  const upload = useUploadEvidence(assessmentId);
  const linkEv = useLinkEvidence(assessmentId);
  const preview = usePreviewEvidence();
  const fileRef = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<EvidenceUploadPhase>("idle");
  const [clientError, setClientError] = useState<string | null>(null);
  const [linkEarlyId, setLinkEarlyId] = useState("");
  const [linkOk, setLinkOk] = useState<string | null>(null);

  const earlyIds = model.evidenceBuckets.find((b) => b.key === "early")?.evidenceIds ?? [];

  return (
    <section
      className={`space-y-3 rounded-md border px-4 py-4 ${
        highlighted
          ? "border-[var(--qm-ink)]/40 bg-[var(--qm-surface-soft)]"
          : "border-[var(--qm-line)] bg-[var(--qm-surface)]"
      }`}
      data-testid="field-evidence"
    >
      <div>
        <h2 className="font-display text-lg text-[var(--qm-ink)]">Evidências</h2>
        <p className="text-sm text-[var(--qm-muted)]">
          Arquivo não é conformidade automática — só evidência aprovada conta.
        </p>
      </div>

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {model.evidenceBuckets.map((b) => (
          <div
            key={b.key}
            className="rounded border border-[var(--qm-line)] px-3 py-2 text-sm"
            data-testid={`field-evidence-bucket-${b.key}`}
          >
            <p className="font-semibold text-[var(--qm-ink)]">
              {b.label} ({b.count})
            </p>
            <p className="mt-1 text-xs text-[var(--qm-muted)]">{b.explanation}</p>
          </div>
        ))}
      </div>

      {canCollect ? (
        <form
          className="space-y-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            setClientError(null);
            const file = fileRef.current?.files?.[0];
            if (!file || upload.isPending) return;
            const v = validateEvidenceFile(file);
            if (v) {
              setClientError(v);
              return;
            }
            void upload
              .mutateAsync({
                file,
                link:
                  interviewId
                    ? { target_type: "interview", target_id: interviewId }
                    : undefined,
                onPhase: setPhase,
              })
              .then(() => {
                if (fileRef.current) fileRef.current.value = "";
                setPhase("idle");
              })
              .catch(onError);
          }}
        >
          <label className="block text-sm">
            <span className="font-semibold">Anexar evidência</span>
            <input
              ref={fileRef}
              type="file"
              className="mt-1 block w-full text-sm"
              data-testid="field-evidence-file"
            />
          </label>
          {clientError ? (
            <p className="text-sm text-qmind-semantic-danger">{clientError}</p>
          ) : null}
          {phase !== "idle" && phase !== "done" ? (
            <p className="text-sm text-[var(--qm-muted)]">Enviando… ({phase})</p>
          ) : null}
          <button
            type="submit"
            className="qm-btn-primary"
            disabled={upload.isPending}
            data-testid="field-evidence-upload"
          >
            Registrar evidência
          </button>
        </form>
      ) : null}

      {earlyIds.length > 0 && interviewId && canCollect ? (
        <div className="space-y-2 text-sm" data-testid="field-evidence-reuse">
          <p className="font-semibold">
            Reutilizar evidência antecipada (sem novo upload)
          </p>
          <p className="text-[var(--qm-muted)]">
            Vincule uma evidência já aprovada à entrevista em foco. Arquivo não
            vira conformidade automática.
          </p>
          <select
            className="qm-field"
            value={linkEarlyId}
            onChange={(e) => setLinkEarlyId(e.target.value)}
            data-testid="field-evidence-reuse-select"
          >
            <option value="">Escolher…</option>
            {earlyIds.map((id, idx) => (
              <option key={id} value={id}>
                Evidência antecipada {idx + 1}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="qm-btn-primary text-sm"
            disabled={!linkEarlyId || linkEv.isPending}
            data-testid="field-evidence-reuse-submit"
            onClick={() => {
              if (!linkEarlyId || !interviewId) return;
              setLinkOk(null);
              void linkEv
                .mutateAsync({
                  evidenceId: linkEarlyId,
                  target_type: "interview",
                  target_id: interviewId,
                })
                .then(() => {
                  setLinkOk("Evidência vinculada à entrevista.");
                  setLinkEarlyId("");
                })
                .catch(onError);
            }}
          >
            Vincular à entrevista
          </button>
          {linkOk ? (
            <p className="text-xs text-[var(--qm-muted)]" data-testid="field-evidence-reuse-ok">
              {linkOk}
            </p>
          ) : null}
        </div>
      ) : null}

      <ul className="space-y-1 text-sm">
        {(evidences.data ?? []).slice(0, 12).map((e, idx) => (
          <li
            key={e.id}
            className="flex flex-wrap items-center justify-between gap-2 rounded border border-[var(--qm-line)] px-2 py-1.5"
          >
            <span>
              Evidência {idx + 1} · {labelWorkflowStatus(e.status)}
            </span>
            <button
              type="button"
              className="qm-btn-secondary text-xs"
              onClick={() => void preview.mutateAsync(e.id).catch(onError)}
            >
              Abrir
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function PendenciesList({
  model,
  onLocal,
}: {
  model: FieldCentralModel;
  onLocal?: (a: FieldNextAction) => void;
}) {
  if (model.pendencies.length === 0) return null;
  return (
    <section
      className="space-y-2 rounded-md border border-amber-300/50 bg-amber-50/60 px-4 py-4"
      data-testid="field-pendencies"
    >
      <h2 className="font-display text-lg text-[var(--qm-ink)]">
        Pendências do campo
      </h2>
      <ul className="space-y-3">
        {model.pendencies.map((p) => (
          <li key={p.key} className="text-sm" data-testid={`field-pendency-${p.key}`}>
            <p className="font-semibold text-[var(--qm-ink)]">{p.problem}</p>
            <p className="text-[var(--qm-muted)]">Impacto: {p.impact}</p>
            {p.href && !p.localAction ? (
              <Link to={p.href} className="qm-btn-secondary mt-2 inline-flex text-sm">
                {p.actionLabel}
              </Link>
            ) : (
              <button
                type="button"
                className="qm-btn-secondary mt-2 text-sm"
                onClick={() =>
                  onLocal?.({
                    kind: "resolve_blocker",
                    label: p.actionLabel,
                    hint: p.impact,
                    href: p.href,
                    localAction: p.localAction,
                    interviewId: p.interviewId,
                  })
                }
              >
                {p.actionLabel}
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

function UnplannedActivity({
  assessmentId,
  highlighted,
  onCreated,
  onError,
}: {
  assessmentId: string;
  highlighted: boolean;
  onCreated: (interviewId: string) => void;
  onError: (e: unknown) => void;
}) {
  const createIv = useCreateInterview(assessmentId);
  const createMeeting = useCreateScheduleMeeting(assessmentId);
  const [kind, setKind] = useState<
    "interview" | "observation" | "visit" | "evidence_request" | "meeting"
  >("interview");
  const [title, setTitle] = useState("");
  const [reason, setReason] = useState("");
  const [processName, setProcessName] = useState("");

  return (
    <section
      className={`space-y-3 rounded-md border px-4 py-4 ${
        highlighted
          ? "border-[var(--qm-ink)]/40 bg-[var(--qm-surface-soft)]"
          : "border-[var(--qm-line)] bg-[var(--qm-surface)]"
      }`}
      data-testid="field-unplanned"
    >
      <div>
        <h2 className="font-display text-lg text-[var(--qm-ink)]">
          Atividade não planejada
        </h2>
        <p className="text-sm text-[var(--qm-muted)]">
          Exija motivo. Mantém rastreabilidade e sincroniza com a agenda quando
          houver horário.
        </p>
      </div>
      <label className="block text-sm">
        <span className="font-semibold">Tipo</span>
        <select
          className="qm-field mt-1"
          value={kind}
          onChange={(e) => setKind(e.target.value as typeof kind)}
        >
          <option value="interview">Entrevista adicional</option>
          <option value="observation">Observação</option>
          <option value="visit">Visita</option>
          <option value="evidence_request">Solicitação de evidência</option>
          <option value="meeting">Reunião adicional</option>
        </select>
      </label>
      <input
        className="qm-field"
        placeholder="Título"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        data-testid="field-unplanned-title"
      />
      {kind === "interview" ? (
        <input
          className="qm-field"
          placeholder="Processo (opcional)"
          value={processName}
          onChange={(e) => setProcessName(e.target.value)}
        />
      ) : null}
      <textarea
        className="qm-field min-h-20"
        placeholder="Motivo (obrigatório)"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        data-testid="field-unplanned-reason"
      />
      <button
        type="button"
        className="qm-btn-primary"
        disabled={
          reason.trim().length < 8 ||
          !title.trim() ||
          createIv.isPending ||
          createMeeting.isPending
        }
        data-testid="field-unplanned-submit"
        onClick={() => {
          const motive = reason.trim();
          if (kind === "meeting") {
            void createMeeting
              .mutateAsync({
                kind: "additional_meeting",
                title: title.trim(),
                objective: motive,
                starts_at: new Date().toISOString(),
                duration_minutes: 30,
                preparation: `Não planejada: ${motive}`,
                outside_period_justification: motive,
              })
              .catch(onError);
            return;
          }
          void createIv
            .mutateAsync({
              mode: "onsite",
              title: title.trim(),
              process_name: processName.trim() || undefined,
              objective:
                kind === "interview"
                  ? motive
                  : `${kind}: ${title.trim()} — ${motive}`,
              preparation: `Não planejada (${kind}): ${motive}`,
              outside_period_justification: motive,
              scheduled_at: new Date().toISOString(),
            })
            .then((row) => onCreated(row.id))
            .catch(onError);
        }}
      >
        Registrar atividade
      </button>
    </section>
  );
}

function ClosingPrepBlock({
  model,
  assessmentId,
}: {
  model: FieldCentralModel;
  assessmentId: string;
}) {
  const c = model.closingPrep;
  const navigate = useNavigate();
  const beginAnalysis = useBeginAssessmentAnalysis(assessmentId);
  const [error, setError] = useState<unknown>(null);
  const canAdvance = model.canMutate;

  return (
    <section
      className="space-y-3 rounded-md border border-[var(--qm-line)] bg-[var(--qm-surface)] px-4 py-4"
      data-testid="field-closing-prep"
    >
      <div>
        <h2 className="font-display text-lg text-[var(--qm-ink)]">
          Preparação do encerramento
        </h2>
        <p className="text-sm text-[var(--qm-muted)]">
          Revise a cobertura. Quando estiver pronto, avance para a análise —
          o sistema não muda de fase sozinho.
        </p>
      </div>
      {error ? <ApiErrorBanner error={error} /> : null}
      <ListBlock title="Coberto" items={c.covered} />
      <ListBlock title="Pendente" items={c.pending} />
      <ListBlock title="Evidências aguardadas" items={c.evidencesWaiting} />
      <ListBlock title="Entrevistas não realizadas" items={c.interviewsSkipped} />
      <ListBlock title="Pontos para aprofundar" items={c.deepen} />
      <p className="text-sm">
        Reunião de encerramento:{" "}
        <strong>
          {c.closingMeetingReady ? "Programada no plano" : "Ainda não preparada"}
        </strong>
      </p>
      <div className="flex flex-wrap gap-2">
        {canAdvance ? (
          <button
            type="button"
            className="qm-btn-primary text-sm"
            data-testid="field-begin-analysis"
            disabled={beginAnalysis.isPending}
            onClick={() =>
              void beginAnalysis
                .mutateAsync()
                .then(() => {
                  void navigate(`/assessments/${assessmentId}/advanced`);
                })
                .catch(setError)
            }
          >
            Encerrar campo e iniciar análise
          </button>
        ) : null}
        <Link
          to={`/assessments/${assessmentId}/advanced`}
          className="qm-btn-secondary inline-flex text-sm"
          data-testid="field-go-analysis-work"
        >
          Ir para constatações
        </Link>
        <Link
          to={`/assessments/${assessmentId}/audit-plan`}
          className="qm-btn-secondary inline-flex text-sm"
        >
          Abrir Plano da Auditoria
        </Link>
      </div>
    </section>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="text-sm">
      <p className="font-semibold">{title}</p>
      <ul className="mt-1 list-disc pl-5 text-[var(--qm-muted)]">
        {items.map((i) => (
          <li key={i}>{i}</li>
        ))}
      </ul>
    </div>
  );
}
