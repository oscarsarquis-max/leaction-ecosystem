/** Vocabulário público de situação de evidência (Wizard). Sem enums técnicos. */

const MAP: Record<string, string> = {
  upload_pending: "Aguardando envio",
  quarantined: "Em verificação",
  rejected: "Rejeitada na verificação",
  approved: "Aprovada",
  superseded: "Substituída",
  pending_disposal: "Aguardando revisão",
  disposed: "Substituída",
};

/** “Disponível” = aprovada e utilizável no contexto consultivo (não é certificação). */
export function publicEvidenceSituation(
  status: string | null | undefined,
  situationFromApi?: string | null,
): string {
  if (situationFromApi?.trim()) return situationFromApi.trim();
  if (!status) return "Aguardando revisão";
  if (status === "approved") return "Aprovada";
  return MAP[status] ?? "Aguardando revisão";
}

export function formatByteSize(bytes: number | null | undefined): string {
  if (bytes == null || Number.isNaN(bytes)) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatEvidenceDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return "—";
  }
}
