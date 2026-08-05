import { useRef, useState, type FormEvent } from "react";
import { getConfig } from "@/config/env";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import {
  useAbandonEvidence,
  useAssessmentEvidences,
  useAssessmentInterviews,
  useAssessmentQuestions,
  useCompleteInterview,
  useCreateAnswer,
  useCreateInterview,
  useInterviewAnswers,
  usePreviewEvidence,
  useSecurityFailEvidence,
  useSecurityPassEvidence,
  useUploadEvidence,
} from "@/hooks/useFieldExecution";
import type { EvidenceUploadPhase } from "@/lib/evidenceUpload";
import { validateEvidenceFile } from "@/lib/evidenceConstraints";
import {
  INTERVIEW_MODE_OPTIONS,
  labelInterviewMode,
  labelWorkflowStatus,
} from "@/lib/labels";

const STATUS_HINT: Record<string, string> = {
  upload_pending: "Em revisão de envio",
  quarantined: "Em verificação (quarentena)",
  approved: "Aprovada — disponível para constatação",
  rejected: "Rejeitada na verificação",
  disposed: "Descartada / expirada",
  superseded: "Substituída",
  pending_disposal: "Pendente de descarte",
};

function phaseLabel(phase: EvidenceUploadPhase): string {
  switch (phase) {
    case "authorizing":
      return "Autorizando…";
    case "uploading":
      return "Enviando evidência…";
    case "confirming":
      return "Confirmando recebimento…";
    case "done":
      return "Recebida (quarentena)";
    case "failed":
      return "Falha";
    default:
      return "";
  }
}

export function FieldExecutionPanel({
  assessmentId,
  canEditField,
  canCollectEvidence,
}: {
  assessmentId: string;
  canEditField: boolean;
  canCollectEvidence: boolean;
}) {
  const interviews = useAssessmentInterviews(assessmentId);
  const evidences = useAssessmentEvidences(assessmentId);
  const questions = useAssessmentQuestions(assessmentId);
  const [selectedInterviewId, setSelectedInterviewId] = useState<string | null>(null);

  return (
    <section className="space-y-6" data-testid="field-execution">
      <header>
        <h2 className="font-display text-2xl text-teal-950">Execução em campo</h2>
        <p className="mt-1 text-sm text-teal-950/70">
          Entrevistas, observações e evidências. Evidência só fica utilizável em constatação após{" "}
          <span className="font-semibold">approved</span>.
        </p>
      </header>

      <InterviewsBlock
        assessmentId={assessmentId}
        canEdit={canEditField}
        interviewsQuery={interviews}
        questions={questions.data ?? []}
        selectedInterviewId={selectedInterviewId}
        onSelectInterview={setSelectedInterviewId}
      />

      <EvidencesBlock
        assessmentId={assessmentId}
        canCollect={canCollectEvidence}
        evidencesQuery={evidences}
        interviewId={selectedInterviewId}
        questionId={questions.data?.[0]?.id ?? null}
      />
    </section>
  );
}

function InterviewsBlock({
  assessmentId,
  canEdit,
  interviewsQuery,
  questions,
  selectedInterviewId,
  onSelectInterview,
}: {
  assessmentId: string;
  canEdit: boolean;
  interviewsQuery: ReturnType<typeof useAssessmentInterviews>;
  questions: { id: string; code: string; prompt_text: string }[];
  selectedInterviewId: string | null;
  onSelectInterview: (id: string) => void;
}) {
  const createInterview = useCreateInterview(assessmentId);
  const [mode, setMode] = useState<"onsite" | "remote" | "hybrid">("onsite");

  async function onCreate() {
    if (!canEdit || createInterview.isPending) return;
    try {
      const row = await createInterview.mutateAsync(mode);
      onSelectInterview(row.id);
    } catch {
      // banner
    }
  }

  return (
    <section className="rounded-lg border border-teal-900/10 bg-white/70 p-4">
      <h3 className="font-display text-xl text-teal-950">Entrevistas</h3>
      <p className="mt-1 text-sm text-teal-950/70">
        Respostas editáveis apenas com entrevista planejada e avaliação em execução.
      </p>

      {canEdit ? (
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <label className="text-sm text-teal-950">
            Modo
            <select
              className="field mt-1 block"
              value={mode}
              onChange={(e) => setMode(e.target.value as typeof mode)}
              data-testid="interview-mode"
            >
              {INTERVIEW_MODE_OPTIONS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            disabled={createInterview.isPending}
            onClick={() => void onCreate()}
            className="rounded-md bg-teal-900 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
            data-testid="interview-create"
          >
            Nova entrevista
          </button>
        </div>
      ) : null}

      {createInterview.isError ? (
        <div className="mt-2">
          <ApiErrorBanner title="Falha ao criar entrevista" error={createInterview.error} />
        </div>
      ) : null}

      {interviewsQuery.isLoading ? (
        <p className="mt-3 text-sm text-teal-950/60">Carregando…</p>
      ) : interviewsQuery.isError ? (
        <div className="mt-3">
          <ApiErrorBanner
            title="Erro ao listar entrevistas"
            error={interviewsQuery.error}
            onRetry={() => void interviewsQuery.refetch()}
          />
        </div>
      ) : (interviewsQuery.data?.length ?? 0) === 0 ? (
        <p className="mt-3 text-sm text-teal-950/60" data-testid="interviews-empty">
          Nenhuma entrevista.
        </p>
      ) : (
        <ul className="mt-3 divide-y divide-teal-900/10" data-testid="interview-list">
          {interviewsQuery.data!.map((i) => (
            <li key={i.id} className="py-2">
              <button
                type="button"
                onClick={() => onSelectInterview(i.id)}
                className={`w-full text-left text-sm ${
                  selectedInterviewId === i.id ? "font-semibold text-teal-900" : "text-teal-950"
                }`}
                data-testid={`interview-select-${i.id}`}
              >
                <span className="font-mono text-xs">{i.id.slice(0, 8)}…</span>
                {" · "}
                <span className="tracking-wide">
                  {labelWorkflowStatus(i.status)}
                  {i.mode ? ` · ${labelInterviewMode(i.mode)}` : ""}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {selectedInterviewId ? (
        <InterviewDetail
          assessmentId={assessmentId}
          interviewId={selectedInterviewId}
          canEdit={canEdit}
          interviewStatus={
            interviewsQuery.data?.find((i) => i.id === selectedInterviewId)?.status
          }
          questions={questions}
        />
      ) : null}
    </section>
  );
}

function InterviewDetail({
  assessmentId,
  interviewId,
  canEdit,
  interviewStatus,
  questions,
}: {
  assessmentId: string;
  interviewId: string;
  canEdit: boolean;
  interviewStatus?: string;
  questions: { id: string; code: string; prompt_text: string }[];
}) {
  const answers = useInterviewAnswers(interviewId);
  const createAnswer = useCreateAnswer(assessmentId, interviewId);
  const complete = useCompleteInterview(assessmentId);
  const [body, setBody] = useState("");
  const [questionId, setQuestionId] = useState("");
  const editable = canEdit && interviewStatus === "planned";

  async function onAddAnswer(e: FormEvent) {
    e.preventDefault();
    if (!editable || createAnswer.isPending || !body.trim()) return;
    try {
      await createAnswer.mutateAsync({
        body: body.trim(),
        question_id: questionId || undefined,
      });
      setBody("");
    } catch {
      // banner
    }
  }

  return (
    <div className="mt-4 rounded-md border border-teal-900/10 bg-teal-50/40 p-3" data-testid="interview-detail">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-sm font-semibold text-teal-950">Respostas / observações</h4>
        {editable ? (
          <button
            type="button"
            disabled={complete.isPending}
            onClick={() => void complete.mutateAsync(interviewId)}
            className="rounded-md border border-teal-900/20 bg-white px-2 py-1 text-xs font-semibold text-teal-950"
            data-testid="interview-complete"
          >
            Concluir entrevista
          </button>
        ) : null}
      </div>

      {answers.isLoading ? (
        <p className="mt-2 text-sm text-teal-950/60">Carregando respostas…</p>
      ) : answers.isError ? (
        <div className="mt-2">
          <ApiErrorBanner title="Erro nas respostas" error={answers.error} />
        </div>
      ) : (
        <ul className="mt-2 space-y-2" data-testid="answer-list">
          {(answers.data ?? []).map((a) => (
            <li key={a.id} className="text-sm text-teal-950/90">
              <p>{a.body}</p>
              <p className="font-mono text-[11px] text-teal-950/50">{a.id}</p>
            </li>
          ))}
          {(answers.data?.length ?? 0) === 0 ? (
            <li className="text-sm text-teal-950/60">Sem respostas ainda.</li>
          ) : null}
        </ul>
      )}

      {editable ? (
        <form className="mt-3 space-y-2" onSubmit={(e) => void onAddAnswer(e)}>
          {questions.length > 0 ? (
            <label className="block text-sm text-teal-950">
              Pergunta (opcional)
              <select
                className="field mt-1 w-full"
                value={questionId}
                onChange={(e) => setQuestionId(e.target.value)}
                data-testid="answer-question"
              >
                <option value="">— observação livre —</option>
                {questions.map((q) => (
                  <option key={q.id} value={q.id}>
                    {q.code}: {q.prompt_text.slice(0, 80)}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <textarea
            className="field w-full"
            rows={3}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Resposta ou observação"
            required
            data-testid="answer-body"
          />
          <button
            type="submit"
            disabled={createAnswer.isPending || !body.trim()}
            className="rounded-md bg-teal-900 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
            data-testid="answer-submit"
          >
            Registrar resposta
          </button>
        </form>
      ) : (
        <p className="mt-2 text-xs text-amber-900" data-testid="interview-locked-notice">
          Entrevista não editável neste estado.
        </p>
      )}

      {createAnswer.isError ? (
        <div className="mt-2">
          <ApiErrorBanner title="Falha ao registrar resposta" error={createAnswer.error} />
        </div>
      ) : null}
      {complete.isError ? (
        <div className="mt-2">
          <ApiErrorBanner title="Falha ao concluir entrevista" error={complete.error} />
        </div>
      ) : null}
    </div>
  );
}

function EvidencesBlock({
  assessmentId,
  canCollect,
  evidencesQuery,
  interviewId,
  questionId,
}: {
  assessmentId: string;
  canCollect: boolean;
  evidencesQuery: ReturnType<typeof useAssessmentEvidences>;
  interviewId: string | null;
  questionId: string | null;
}) {
  const upload = useUploadEvidence(assessmentId);
  const pass = useSecurityPassEvidence(assessmentId);
  const fail = useSecurityFailEvidence(assessmentId);
  const abandon = useAbandonEvidence(assessmentId);
  const preview = usePreviewEvidence();
  const [phase, setPhase] = useState<EvidenceUploadPhase>("idle");
  const [clientError, setClientError] = useState<string | null>(null);
  const [linkKind, setLinkKind] = useState<"none" | "interview" | "question">("none");
  const fileRef = useRef<HTMLInputElement>(null);
  const allowSimulatedPass = getConfig().environment !== "prod";

  async function onUpload(e: FormEvent) {
    e.preventDefault();
    setClientError(null);
    const file = fileRef.current?.files?.[0];
    if (!file || !canCollect || upload.isPending) return;
    const v = validateEvidenceFile(file);
    if (v) {
      setClientError(v);
      return;
    }
    const link =
      linkKind === "interview" && interviewId
        ? { target_type: "interview" as const, target_id: interviewId }
        : linkKind === "question" && questionId
          ? { target_type: "question" as const, target_id: questionId }
          : undefined;
    try {
      await upload.mutateAsync({ file, link, onPhase: setPhase });
      if (fileRef.current) fileRef.current.value = "";
      setPhase("idle");
    } catch {
      // banner via upload.error
    }
  }

  return (
    <section className="rounded-lg border border-teal-900/10 bg-white/70 p-4">
      <h3 className="font-display text-xl text-teal-950">Evidências</h3>
      <p className="mt-1 text-sm text-teal-950/70">
        Fluxo: authorize → PUT → receive → quarantined → approved|rejected. URL assinada nunca é
        persistida; upload só é concluído após receive.
      </p>

      {canCollect ? (
        <form className="mt-3 space-y-2" onSubmit={(e) => void onUpload(e)} data-testid="evidence-upload-form">
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.txt,.docx,application/pdf,image/png,image/jpeg,text/plain"
            className="block w-full text-sm"
            data-testid="evidence-file"
          />
          <label className="block text-sm text-teal-950">
            Vincular a
            <select
              className="field mt-1 block"
              value={linkKind}
              onChange={(e) => setLinkKind(e.target.value as typeof linkKind)}
              data-testid="evidence-link-kind"
            >
              <option value="none">— sem vínculo imediato —</option>
              <option value="interview" disabled={!interviewId}>
                entrevista selecionada
              </option>
              <option value="question" disabled={!questionId}>
                primeira pergunta do modelo
              </option>
            </select>
          </label>
          <button
            type="submit"
            disabled={upload.isPending}
            className="rounded-md bg-teal-900 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
            data-testid="evidence-upload"
          >
            {upload.isPending ? phaseLabel(phase) || "Enviando…" : "Enviar evidência"}
          </button>
          {phase !== "idle" && upload.isPending ? (
            <p className="text-xs text-teal-950/60" data-testid="evidence-phase">
              {phaseLabel(phase)}
            </p>
          ) : null}
        </form>
      ) : (
        <p className="mt-3 text-sm text-teal-950/60">Upload bloqueado neste estado/papel.</p>
      )}

      {clientError ? (
        <p className="mt-2 text-sm text-amber-900" data-testid="evidence-client-error">
          {clientError}
        </p>
      ) : null}
      {upload.isError ? (
        <div className="mt-2">
          <ApiErrorBanner title="Falha no upload" error={upload.error} />
        </div>
      ) : null}

      {evidencesQuery.isLoading ? (
        <p className="mt-3 text-sm text-teal-950/60">Carregando evidências…</p>
      ) : evidencesQuery.isError ? (
        <div className="mt-3">
          <ApiErrorBanner
            title="Erro ao listar evidências"
            error={evidencesQuery.error}
            onRetry={() => void evidencesQuery.refetch()}
          />
        </div>
      ) : (evidencesQuery.data?.length ?? 0) === 0 ? (
        <p className="mt-3 text-sm text-teal-950/60" data-testid="evidences-empty">
          Nenhuma evidência.
        </p>
      ) : (
        <ul className="mt-3 divide-y divide-teal-900/10" data-testid="evidence-list">
          {evidencesQuery.data!.map((ev) => (
            <li key={ev.id} className="flex flex-wrap items-start justify-between gap-2 py-3 text-sm">
              <div>
                <p className="font-mono text-xs">{ev.id}</p>
                <p className="mt-0.5">
                  <span
                    className="rounded bg-teal-900/10 px-1.5 py-0.5 text-xs font-semibold tracking-wide text-teal-900"
                    data-testid={`evidence-status-${ev.id}`}
                  >
                    {labelWorkflowStatus(ev.status)}
                  </span>
                  <span className="ml-2 text-teal-950/60">
                    {STATUS_HINT[ev.status] ?? labelWorkflowStatus(ev.status)}
                  </span>
                </p>
                <p className="mt-1 text-xs text-teal-950/50">
                  {ev.content_type ?? "—"} · {ev.byte_size ?? "?"} bytes
                  {ev.upload_expires_at ? ` · expira ${ev.upload_expires_at}` : ""}
                </p>
              </div>
              <div className="flex flex-wrap gap-1">
                {(ev.status === "approved" || ev.status === "quarantined") && canCollect ? (
                  <button
                    type="button"
                    className="rounded border border-teal-900/20 bg-white px-2 py-1 text-xs font-semibold"
                    onClick={() => void preview.mutateAsync(ev.id)}
                    data-testid={`evidence-preview-${ev.id}`}
                  >
                    Visualizar
                  </button>
                ) : null}
                {ev.status === "upload_pending" && canCollect ? (
                  <button
                    type="button"
                    className="rounded border border-amber-400/50 bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-950"
                    onClick={() => void abandon.mutateAsync(ev.id)}
                    data-testid={`evidence-abandon-${ev.id}`}
                  >
                    Abandonar
                  </button>
                ) : null}
                {ev.status === "quarantined" && canCollect && allowSimulatedPass ? (
                  <>
                    <button
                      type="button"
                      className="rounded bg-teal-900 px-2 py-1 text-xs font-semibold text-white"
                      onClick={() => void pass.mutateAsync(ev.id)}
                      data-testid={`evidence-pass-${ev.id}`}
                    >
                      Aprovar (simulado)
                    </button>
                    <button
                      type="button"
                      className="rounded border border-qmind-semantic-danger/30 bg-qmind-semantic-future px-2 py-1 text-xs font-semibold text-qmind-semantic-danger"
                      onClick={() => void fail.mutateAsync(ev.id)}
                      data-testid={`evidence-fail-${ev.id}`}
                    >
                      Rejeitar
                    </button>
                  </>
                ) : null}
                {ev.status === "quarantined" && canCollect && !allowSimulatedPass ? (
                  <span className="text-xs text-amber-900">
                    Aprovação simulada indisponível em produção
                  </span>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}

      {preview.isError ? (
        <div className="mt-2">
          <ApiErrorBanner title="Falha no preview" error={preview.error} />
        </div>
      ) : null}
      {pass.isError ? (
        <div className="mt-2">
          <ApiErrorBanner title="Falha na aprovação" error={pass.error} />
        </div>
      ) : null}
    </section>
  );
}
