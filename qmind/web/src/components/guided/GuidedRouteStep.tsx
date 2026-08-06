import { useEffect, useMemo, useState } from "react";
import {
  ANSWER_OPTIONS,
  type AnswerValue,
  type EvidenceMode,
  type GuidedAnswer,
  type GuidedAnswerUpsert,
  type GuidedQuestion,
} from "@/api/guidedTypes";
import { ContextualHelp } from "@/components/shared/ContextualHelp";
import { uploadEvidenceFile } from "@/lib/evidenceUpload";
import { getQmindClient, withTenantGeneration } from "@/api/qmindApi";

type SaveState = "idle" | "saving" | "saved" | "error";

type Props = {
  assessmentId: string;
  question: GuidedQuestion;
  questionIndex: number;
  questionTotal: number;
  answer: GuidedAnswer | undefined;
  readOnly?: boolean;
  saving?: boolean;
  saveState?: SaveState;
  onSave: (body: GuidedAnswerUpsert) => Promise<void>;
};

function AutosaveFeedback({ saveState, saving }: { saveState?: SaveState; saving?: boolean }) {
  const state: SaveState =
    saving || saveState === "saving"
      ? "saving"
      : saveState === "error"
        ? "error"
        : saveState === "saved"
          ? "saved"
          : "idle";

  if (state === "idle") return null;

  if (state === "saving") {
    return (
      <p className="text-sm text-qmind-text-muted" data-testid="save-state">
        Salvando rascunho...
      </p>
    );
  }
  if (state === "saved") {
    return (
      <p className="text-sm font-medium text-qmind-semantic-success" data-testid="save-state">
        ✓ Salvo
      </p>
    );
  }
  return (
    <p className="text-sm font-medium text-qmind-semantic-danger" data-testid="save-state">
      Erro ao salvar
    </p>
  );
}

export function GuidedRouteStep({
  assessmentId,
  question,
  questionIndex,
  questionTotal,
  answer,
  readOnly,
  saving,
  saveState,
  onSave,
}: Props) {
  const [value, setValue] = useState<AnswerValue | null>(
    answer?.answer_value ?? null,
  );
  const [description, setDescription] = useState(answer?.description ?? "");
  const [naJustification, setNaJustification] = useState(
    answer?.na_justification ?? "",
  );
  const [evidenceMode, setEvidenceMode] = useState<EvidenceMode>(
    answer?.evidence_mode ?? "none",
  );
  const [evidenceNote, setEvidenceNote] = useState(answer?.evidence_note ?? "");
  const [evidenceIds, setEvidenceIds] = useState<string[]>(
    answer?.evidence_ids ?? [],
  );
  const [provideLater, setProvideLater] = useState(
    answer?.provide_later ?? false,
  );
  const [existing, setExisting] = useState<{ id: string; title: string }[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    setValue(answer?.answer_value ?? null);
    setDescription(answer?.description ?? "");
    setNaJustification(answer?.na_justification ?? "");
    setEvidenceMode(answer?.evidence_mode ?? "none");
    setEvidenceNote(answer?.evidence_note ?? "");
    setEvidenceIds(answer?.evidence_ids ?? []);
    setProvideLater(answer?.provide_later ?? false);
    setUploadError(null);
  }, [question.id, answer]);

  useEffect(() => {
    if (!value || value === "unknown") return;
    let cancelled = false;
    void (async () => {
      try {
        const client = getQmindClient();
        const list = await withTenantGeneration(async () => {
          const res = await client.api.listAssessmentEvidences({
            path: { assessment_id: assessmentId },
          });
          return res.data ?? [];
        });
        if (cancelled) return;
        setExisting(
          list.map((e) => ({
            id: e.id,
            title: `${e.content_type || "evidência"} · ${e.id.slice(0, 8)}`,
          })),
        );
      } catch {
        if (!cancelled) setExisting([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [assessmentId, value, question.id]);

  const showEvidence = value !== null && value !== "unknown";
  const canAdvance = useMemo(() => {
    if (!value) return false;
    if (value === "not_applicable" && !naJustification.trim()) return false;
    return true;
  }, [value, naJustification]);

  async function persist(partial?: Partial<GuidedAnswerUpsert>) {
    if (readOnly) return;
    const body: GuidedAnswerUpsert = {
      question_version: question.version,
      answer_value: value,
      description,
      na_justification: naJustification,
      evidence_mode: evidenceMode,
      evidence_ids: evidenceIds,
      evidence_note: evidenceNote,
      provide_later: provideLater,
      ...partial,
    };
    await onSave(body);
  }

  return (
    <div className="relative space-y-6" data-testid="guided-question">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-qmind-text-muted">
            Pergunta {questionIndex + 1} de {questionTotal}
            <span className="mx-2 text-qmind-semantic-disabled">·</span>
            Cláusula {question.clause_ref}
          </p>
          <p className="mt-2 text-sm font-semibold text-qmind-main">
            {question.theme}
          </p>
          <p className="mt-1 text-xs text-qmind-text-muted">
            Referência interna de orientação — não é o texto da norma.
          </p>
        </div>
        <AutosaveFeedback saveState={saveState} saving={saving} />
      </div>

      <header>
        <h2 className="text-lg font-semibold text-qmind-main">{question.question}</h2>
        <p className="mt-3 text-base leading-relaxed text-qmind-text-muted">
          {question.explanation}
        </p>
      </header>

      <div>
        <p className="mb-2 text-sm font-semibold text-qmind-main">
          Exemplos de práticas
        </p>
        <ul className="list-disc space-y-1 pl-5 text-sm text-qmind-text-muted">
          {question.practice_examples.map((ex) => (
            <li key={ex}>{ex}</li>
          ))}
        </ul>
      </div>

      <fieldset disabled={readOnly || saving} className="space-y-3">
        <legend className="text-sm font-semibold text-qmind-main">
          Sua resposta
        </legend>
        <div className="grid gap-2 sm:grid-cols-2">
          {ANSWER_OPTIONS.map((opt) => {
            const active = value === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                data-testid={`answer-${opt.value}`}
                className={
                  active
                    ? "rounded-qmind-md border border-qmind-main bg-qmind-main px-3 py-2.5 text-left text-sm font-semibold text-white"
                    : "rounded-qmind-md border border-qmind-semantic-disabled bg-qmind-surface px-3 py-2.5 text-left text-sm font-semibold text-qmind-main hover:border-qmind-main"
                }
                onClick={() => {
                  const nextVal = opt.value;
                  setValue(nextVal);
                  let nextMode = evidenceMode;
                  let nextLater = provideLater;
                  let nextNaj = naJustification;
                  if (nextVal === "unknown") {
                    nextMode = "none";
                    nextLater = false;
                    setEvidenceMode("none");
                    setProvideLater(false);
                  }
                  if (nextVal !== "not_applicable") {
                    nextNaj = "";
                    setNaJustification("");
                  }
                  if (nextVal !== "not_applicable" || nextNaj.trim()) {
                    void onSave({
                      question_version: question.version,
                      answer_value: nextVal,
                      description,
                      na_justification: nextNaj,
                      evidence_mode: nextMode,
                      evidence_ids: evidenceIds,
                      evidence_note: evidenceNote,
                      provide_later: nextLater,
                    });
                  }
                }}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </fieldset>

      {value === "not_applicable" ? (
        <label className="block space-y-1.5">
          <span className="text-sm font-semibold text-qmind-main">
            Justificativa (obrigatória)
          </span>
          <textarea
            className="qm-field min-h-24"
            value={naJustification}
            disabled={readOnly}
            data-testid="na-justification"
            onChange={(e) => setNaJustification(e.target.value)}
            onBlur={() => void persist()}
          />
        </label>
      ) : null}

      <label className="block space-y-1.5">
        <span className="text-sm font-semibold text-qmind-main">
          Descreva a situação em linguagem livre
        </span>
        <textarea
          className="qm-field min-h-28"
          value={description}
          disabled={readOnly}
          data-testid="answer-description"
          onChange={(e) => setDescription(e.target.value)}
          onBlur={() => {
            if (value) void persist();
          }}
        />
      </label>

      {showEvidence ? (
        <div
          className="mt-4 space-y-4 border-l-4 border-qmind-semantic-warning bg-qmind-app p-4"
          data-testid="evidence-after-answer"
        >
          <div>
            <h3 className="inline-flex flex-wrap items-center gap-2 text-base font-semibold text-qmind-main">
              Evidência desta resposta
              <ContextualHelp text="A evidência é o documento ou registro que comprova esta constatação" />
            </h3>
            <p className="mt-1 text-sm text-qmind-text-muted">
              Só pedimos evidência depois da resposta. Você pode anexar, vincular,
              descrever ou deixar para depois.
            </p>
          </div>
          <div>
            <p className="mb-2 text-sm font-semibold text-qmind-main">
              Exemplos relacionados
            </p>
            <ul className="list-disc space-y-1 pl-5 text-sm text-qmind-text-muted">
              {question.evidence_examples.map((ex) => (
                <li key={ex}>{ex}</li>
              ))}
            </ul>
          </div>

          <div className="grid gap-2 sm:grid-cols-2">
            {(
              [
                ["attach", "Anexar evidência"],
                ["link_existing", "Vincular evidência existente"],
                ["describe", "Descrever evidência"],
                ["provide_later", "Fornecer depois"],
              ] as const
            ).map(([mode, label]) => (
              <button
                key={mode}
                type="button"
                disabled={readOnly}
                className={
                  evidenceMode === mode
                    ? "rounded-qmind-md border border-qmind-main bg-qmind-surface px-3 py-2 text-left text-sm font-semibold text-qmind-main"
                    : "rounded-qmind-md border border-qmind-semantic-future bg-qmind-surface/70 px-3 py-2 text-left text-sm text-qmind-text-muted hover:border-qmind-main"
                }
                onClick={() => {
                  setEvidenceMode(mode);
                  setProvideLater(mode === "provide_later");
                }}
              >
                {label}
              </button>
            ))}
          </div>

          {evidenceMode === "attach" ? (
            <div>
              <input
                type="file"
                disabled={readOnly || uploading}
                className="text-sm"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  setUploading(true);
                  setUploadError(null);
                  void uploadEvidenceFile({
                    assessmentId,
                    file,
                  })
                    .then(async (r) => {
                      const ids = [...new Set([...evidenceIds, r.evidenceId])];
                      setEvidenceIds(ids);
                      await persist({
                        evidence_mode: "attach",
                        evidence_ids: ids,
                        provide_later: false,
                      });
                    })
                    .catch((err: unknown) => {
                      setUploadError(
                        err instanceof Error
                          ? err.message
                          : "Falha ao anexar evidência",
                      );
                    })
                    .finally(() => setUploading(false));
                }}
              />
              {uploading ? (
                <p className="mt-2 text-sm text-qmind-text-muted">Enviando…</p>
              ) : null}
              {uploadError ? (
                <p className="mt-2 text-sm text-qmind-semantic-danger">{uploadError}</p>
              ) : null}
              {evidenceIds.length > 0 ? (
                <p className="mt-2 text-sm text-qmind-main">
                  {evidenceIds.length} evidência(s) vinculada(s)
                </p>
              ) : null}
            </div>
          ) : null}

          {evidenceMode === "link_existing" ? (
            <div className="space-y-2">
              {existing.length === 0 ? (
                <p className="text-sm text-qmind-text-muted">
                  Ainda não há evidências nesta avaliação. Você pode anexar ou
                  descrever.
                </p>
              ) : (
                existing.map((ev) => {
                  const checked = evidenceIds.includes(ev.id);
                  return (
                    <label
                      key={ev.id}
                      className="flex items-center gap-2 text-sm text-qmind-main"
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={readOnly}
                        onChange={(e) => {
                          const next = e.target.checked
                            ? [...evidenceIds, ev.id]
                            : evidenceIds.filter((id) => id !== ev.id);
                          setEvidenceIds(next);
                          void persist({
                            evidence_mode: "link_existing",
                            evidence_ids: next,
                            provide_later: false,
                          });
                        }}
                      />
                      {ev.title}
                    </label>
                  );
                })
              )}
            </div>
          ) : null}

          {evidenceMode === "describe" ? (
            <textarea
              className="qm-field min-h-24"
              placeholder="Descreva a evidência existente (onde está, quem mantém, o que mostra)."
              value={evidenceNote}
              disabled={readOnly}
              onChange={(e) => setEvidenceNote(e.target.value)}
              onBlur={() =>
                void persist({
                  evidence_mode: "describe",
                  evidence_note: evidenceNote,
                  provide_later: false,
                })
              }
            />
          ) : null}

          {evidenceMode === "provide_later" ? (
            <p className="text-sm text-qmind-text-muted">
              Marcado para fornecer depois. Nenhuma evidência inventada — apenas
              o compromisso de anexar mais adiante.
            </p>
          ) : null}
        </div>
      ) : null}

      {!canAdvance && value === "not_applicable" ? (
        <p className="text-sm text-qmind-semantic-warning">
          Informe a justificativa para “Não aplicável” antes de avançar.
        </p>
      ) : null}
    </div>
  );
}
