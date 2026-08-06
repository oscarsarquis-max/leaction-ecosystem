import { useEffect, useState } from "react";
import type { EvidenceMode, GuidedAnswer, GuidedEvidenceLink } from "@/api/guidedTypes";
import { ContextualHelp } from "@/components/shared/ContextualHelp";
import { uploadEvidenceFile } from "@/lib/evidenceUpload";
import {
  formatByteSize,
  formatEvidenceDate,
  publicEvidenceSituation,
} from "@/lib/evidencePublicStatus";
import { getQmindClient, withTenantGeneration } from "@/api/qmindApi";

type Props = {
  assessmentId: string;
  questionId: string;
  evidenceExamples?: string[];
  answer: GuidedAnswer | undefined;
  readOnly?: boolean;
  onRefresh: () => Promise<void>;
  onProvideLater: () => Promise<void>;
  onDescribe: (note: string) => Promise<void>;
  onLinkExisting: (evidenceId: string) => Promise<void>;
  onUnlink: (evidenceId: string) => Promise<void>;
};

function evidenceList(answer: GuidedAnswer | undefined): GuidedEvidenceLink[] {
  if (answer?.evidence_links?.length) return answer.evidence_links;
  return [];
}

export function GuidedEvidencePanel({
  assessmentId,
  questionId,
  evidenceExamples = [],
  answer,
  readOnly,
  onRefresh,
  onProvideLater,
  onDescribe,
  onLinkExisting,
  onUnlink,
}: Props) {
  const links = evidenceList(answer);
  const linkedKey = links.map((l) => l.evidence_id).join(",");
  const [evidenceMode, setEvidenceMode] = useState<EvidenceMode>(
    answer?.evidence_mode ?? "none",
  );
  const [evidenceNote, setEvidenceNote] = useState(answer?.evidence_note ?? "");
  const [existing, setExisting] = useState<
    { id: string; title: string; linked: boolean }[]
  >([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    setEvidenceMode(answer?.evidence_mode ?? "none");
    setEvidenceNote(answer?.evidence_note ?? "");
    setUploadError(null);
  }, [questionId, answer]);

  useEffect(() => {
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
        const linked = new Set(linkedKey ? linkedKey.split(",") : []);
        setExisting(
          list.map((e) => ({
            id: e.id,
            title: `${e.content_type || "evidência"} · ${e.id.slice(0, 8)}`,
            linked: linked.has(e.id),
          })),
        );
      } catch {
        if (!cancelled) setExisting([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [assessmentId, questionId, linkedKey]);

  return (
    <div
      className="mt-4 space-y-4 border-l-4 border-qmind-semantic-warning bg-qmind-app p-4"
      data-testid="evidence-after-answer"
    >
      <div>
        <h3 className="inline-flex flex-wrap items-center gap-2 text-base font-semibold text-qmind-main">
          Evidência desta resposta
          <ContextualHelp text="A evidência é o documento ou registro que ilustra esta resposta. Arquivo anexado não é, por si só, prova de conformidade." />
        </h3>
        <p className="mt-1 text-sm text-qmind-text-muted">
          Só pedimos evidência depois da resposta. Você pode anexar, vincular,
          descrever ou deixar para depois.
        </p>
      </div>

      {evidenceExamples.length > 0 ? (
        <div>
          <p className="mb-2 text-sm font-semibold text-qmind-main">
            Exemplos relacionados
          </p>
          <ul className="list-disc space-y-1 pl-5 text-sm text-qmind-text-muted">
            {evidenceExamples.map((ex) => (
              <li key={ex}>{ex}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {links.length > 0 ? (
        <ul className="space-y-2" data-testid="guided-evidence-list">
          {links.map((link) => {
            const situation = publicEvidenceSituation(
              link.evidence_status,
              link.situation,
            );
            return (
              <li
                key={link.id}
                className="rounded-md border border-qmind-semantic-future bg-qmind-surface px-3 py-2 text-sm"
                data-testid={`guided-evidence-${link.evidence_id}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="font-semibold text-qmind-main">
                      {link.file_name || link.content_type || "Evidência"}
                    </p>
                    <p className="text-qmind-text-muted">
                      {link.content_type || "—"} ·{" "}
                      {formatByteSize(link.byte_size)} · {situation} ·{" "}
                      {formatEvidenceDate(
                        link.evidence_updated_at ?? link.created_at,
                      )}
                    </p>
                  </div>
                  {!readOnly ? (
                    <button
                      type="button"
                      className="text-xs font-semibold text-qmind-semantic-danger hover:underline"
                      disabled={busyId === link.evidence_id}
                      onClick={() => {
                        setBusyId(link.evidence_id);
                        void onUnlink(link.evidence_id).finally(() =>
                          setBusyId(null),
                        );
                      }}
                    >
                      Remover vínculo
                    </button>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      ) : null}

      <div className="grid gap-2 sm:grid-cols-2">
        {(
          [
            ["attach", "Anexar nova evidência"],
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
              if (mode === "provide_later") void onProvideLater();
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
            data-testid="guided-evidence-file"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              setUploading(true);
              setUploadError(null);
              void uploadEvidenceFile({
                assessmentId,
                file,
                guidedQuestionId: questionId,
              })
                .then(() => onRefresh())
                .catch((err: unknown) => {
                  setUploadError(
                    err instanceof Error
                      ? err.message
                      : "Falha ao anexar evidência",
                  );
                })
                .finally(() => setUploading(false));
              e.target.value = "";
            }}
          />
          {uploading ? (
            <p className="mt-2 text-sm text-qmind-text-muted">Enviando…</p>
          ) : null}
          {uploadError ? (
            <p className="mt-2 text-sm text-qmind-semantic-danger">{uploadError}</p>
          ) : null}
        </div>
      ) : null}

      {evidenceMode === "link_existing" ? (
        <div className="space-y-2" data-testid="guided-link-existing">
          {existing.length === 0 ? (
            <p className="text-sm text-qmind-text-muted">
              Ainda não há evidências nesta avaliação. Você pode anexar ou
              descrever.
            </p>
          ) : (
            existing.map((ev) => (
              <label
                key={ev.id}
                className="flex items-center gap-2 text-sm text-qmind-main"
              >
                <input
                  type="checkbox"
                  checked={ev.linked}
                  disabled={readOnly || busyId === ev.id}
                  onChange={(e) => {
                    setBusyId(ev.id);
                    const op = e.target.checked
                      ? onLinkExisting(ev.id)
                      : onUnlink(ev.id);
                    void op.finally(() => setBusyId(null));
                  }}
                />
                {ev.title}
              </label>
            ))
          )}
        </div>
      ) : null}

      {evidenceMode === "describe" ? (
        <textarea
          className="qm-field min-h-24"
          placeholder="Descreva a evidência existente (onde está, quem mantém, o que mostra)."
          value={evidenceNote}
          disabled={readOnly}
          data-testid="guided-evidence-describe"
          onChange={(e) => setEvidenceNote(e.target.value)}
          onBlur={() => void onDescribe(evidenceNote)}
        />
      ) : null}

      {evidenceMode === "provide_later" ? (
        <p className="text-sm text-qmind-text-muted">
          Marcado para fornecer depois. Nenhuma evidência inventada — apenas o
          compromisso de anexar mais adiante.
        </p>
      ) : null}
    </div>
  );
}
