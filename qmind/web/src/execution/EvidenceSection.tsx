import { useState } from "react";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import {
  useEvidenceAttachments,
  useUploadActionEvidence,
} from "@/execution/hooks";
import { formatShortDate } from "@/execution/labels";
import {
  EVIDENCE_STATUS_LABELS,
  evidenceTypeLabel,
  formatByteSize,
} from "@/execution/measurementLabels";
import type { EvidenceAttachment } from "@/execution/api";
import type { EvidenceUploadPhase } from "@/lib/evidenceUpload";

const PHASE_MESSAGES: Record<EvidenceUploadPhase, string> = {
  idle: "",
  authorizing: "Preparando o envio…",
  uploading: "Enviando o arquivo…",
  confirming: "Confirmando o recebimento…",
  done: "Evidência anexada.",
  failed: "",
};

/**
 * A person reads what the evidence *is*, not where it is stored: type,
 * situation, date and size. Identifiers and storage keys never reach the
 * screen, even though the payload carries them.
 */
function describeAttachment(attachment: EvidenceAttachment): string {
  const evidence = attachment.evidence;
  if (!evidence) return "Evidência indisponível para leitura";
  const parts = [
    evidenceTypeLabel(evidence.content_type),
    EVIDENCE_STATUS_LABELS[evidence.status] ?? "Situação desconhecida",
    `Anexada em ${formatShortDate(attachment.link.created_at)}`,
  ];
  const size = formatByteSize(evidence.byte_size);
  if (size) parts.push(size);
  return parts.join(" · ");
}

export function EvidenceSection({
  actionItemId,
  canMutate,
}: {
  actionItemId: string;
  canMutate: boolean;
}) {
  const query = useEvidenceAttachments("action_item", actionItemId);
  const upload = useUploadActionEvidence(actionItemId);

  const [phase, setPhase] = useState<EvidenceUploadPhase>("idle");
  const [error, setError] = useState<unknown>(null);

  const attachments = query.data ?? [];

  async function submitFile(file: File | undefined) {
    if (!file) return;
    setError(null);
    try {
      await upload.mutateAsync({ file, onPhase: setPhase });
    } catch (err) {
      setPhase("failed");
      setError(err);
    }
  }

  return (
    <section className="qm-panel px-6 py-5" data-testid="execution-evidence-section">
      <h3 className="font-semibold text-[var(--qm-ink)]">Evidências</h3>
      <p className="mt-1 text-sm text-[var(--qm-muted)]">
        Anexe o que comprova o que foi feito nesta ação — um registro, uma foto,
        um relatório. A evidência fica ligada à ação e ao caso de origem.
      </p>

      {error ? (
        <div className="mt-3">
          <ApiErrorBanner error={error} title="Não foi possível anexar a evidência" />
        </div>
      ) : null}

      {canMutate ? (
        <div className="mt-4 space-y-2" data-testid="execution-evidence-upload">
          <label className="block text-sm font-semibold">
            Anexar evidência desta ação
            <input
              className="qm-field mt-1"
              type="file"
              disabled={upload.isPending}
              onChange={(e) => {
                const file = e.target.files?.[0];
                e.target.value = "";
                void submitFile(file);
              }}
            />
          </label>
          <p className="text-xs text-[var(--qm-muted)]">
            Exemplo: procedimento revisado, ata da reunião de padronização ou foto
            do posto de trabalho após a mudança.
          </p>
          {PHASE_MESSAGES[phase] ? (
            <p className="text-xs text-[var(--qm-muted)]" role="status">
              {PHASE_MESSAGES[phase]}
            </p>
          ) : null}
        </div>
      ) : (
        <p className="mt-3 text-sm text-[var(--qm-muted)]">
          Seu perfil é somente leitura — peça a alguém com permissão de execução
          para anexar evidências.
        </p>
      )}

      <ul className="mt-4 space-y-2 text-sm" data-testid="execution-evidence-list">
        {attachments.length === 0 ? (
          <li className="text-[var(--qm-muted)]">
            Nenhuma evidência anexada a esta ação ainda. Sem evidência, a
            validação depende apenas da palavra de quem executou.
          </li>
        ) : (
          attachments.map((attachment) => (
            <li
              key={attachment.link.id}
              className="border-b border-[var(--qm-line)] pb-2"
            >
              {describeAttachment(attachment)}
            </li>
          ))
        )}
      </ul>
    </section>
  );
}
