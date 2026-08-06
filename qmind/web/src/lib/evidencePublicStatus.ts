/** Vocabulário público de situação/origem de evidência (Wizard). Sem enums técnicos. */

const SITUATION: Record<string, string> = {
  upload_pending: "Aguardando envio",
  quarantined: "Em verificação",
  rejected: "Rejeitada",
  approved: "Aprovada",
  superseded: "Substituída",
  pending_disposal: "Aguardando revisão",
  disposed: "Substituída",
};

const ORIGIN: Record<string, string> = {
  preparation: "Disponível antecipadamente",
  planning: "Disponível antecipadamente",
  field: "Coletada em campo",
  analysis: "Complementação da análise",
};

export function publicEvidenceSituation(
  status: string | null | undefined,
  situationFromApi?: string | null,
): string {
  if (situationFromApi?.trim()) return situationFromApi.trim();
  if (!status) return "Aguardando revisão";
  return SITUATION[status] ?? "Aguardando revisão";
}

export function publicCollectionOrigin(
  phase: string | null | undefined,
  originFromApi?: string | null,
): string | null {
  if (originFromApi?.trim()) return originFromApi.trim();
  if (!phase || phase === "unknown_legacy") return null;
  return ORIGIN[phase] ?? null;
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
