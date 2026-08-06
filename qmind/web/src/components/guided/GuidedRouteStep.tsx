import { useEffect, useMemo, useState } from "react";
import {
  ANSWER_OPTIONS,
  type AnswerValue,
  type GuidedAnswer,
  type GuidedAnswerUpsert,
  type GuidedQuestion,
} from "@/api/guidedTypes";
import { GuidedEvidencePanel } from "@/components/guided/GuidedEvidencePanel";

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
  onRefresh: () => Promise<void>;
  onLinkEvidence: (evidenceId: string) => Promise<void>;
  onUnlinkEvidence: (evidenceId: string) => Promise<void>;
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

function linkedIds(answer: GuidedAnswer | undefined): string[] {
  if (answer?.evidence_links?.length) {
    return answer.evidence_links.map((l) => l.evidence_id);
  }
  return answer?.evidence_ids ?? [];
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
  onRefresh,
  onLinkEvidence,
  onUnlinkEvidence,
}: Props) {
  const [value, setValue] = useState<AnswerValue | null>(
    answer?.answer_value ?? null,
  );
  const [description, setDescription] = useState(answer?.description ?? "");
  const [naJustification, setNaJustification] = useState(
    answer?.na_justification ?? "",
  );

  useEffect(() => {
    setValue(answer?.answer_value ?? null);
    setDescription(answer?.description ?? "");
    setNaJustification(answer?.na_justification ?? "");
  }, [question.id, answer]);

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
      evidence_mode: answer?.evidence_mode ?? "none",
      evidence_ids: linkedIds(answer),
      evidence_note: answer?.evidence_note ?? "",
      provide_later: answer?.provide_later ?? false,
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
                  let nextNaj = naJustification;
                  let nextMode = answer?.evidence_mode ?? "none";
                  let nextLater = answer?.provide_later ?? false;
                  if (nextVal === "unknown") {
                    nextMode = "none";
                    nextLater = false;
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
                      evidence_ids: linkedIds(answer),
                      evidence_note: answer?.evidence_note ?? "",
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
        <GuidedEvidencePanel
          assessmentId={assessmentId}
          questionId={question.id}
          evidenceExamples={question.evidence_examples}
          answer={answer}
          readOnly={readOnly}
          onRefresh={onRefresh}
          onProvideLater={() =>
            persist({
              evidence_mode: "provide_later",
              provide_later: true,
            })
          }
          onDescribe={(note) =>
            persist({
              evidence_mode: "describe",
              evidence_note: note,
              provide_later: false,
            })
          }
          onLinkExisting={onLinkEvidence}
          onUnlink={onUnlinkEvidence}
        />
      ) : null}

      {!canAdvance && value === "not_applicable" ? (
        <p className="text-sm text-qmind-semantic-warning">
          Informe a justificativa para “Não aplicável” antes de avançar.
        </p>
      ) : null}
    </div>
  );
}
