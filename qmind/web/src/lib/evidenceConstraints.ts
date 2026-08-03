/** Client-side mirrors of backend evidence authorize guards. */

export const EVIDENCE_MAX_BYTES = 25_000_000;

export const EVIDENCE_ALLOWED_CONTENT_TYPES = new Set([
  "application/pdf",
  "image/png",
  "image/jpeg",
  "text/plain",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]);

export function validateEvidenceFile(file: File): string | null {
  const ctype = (file.type || "").split(";")[0].trim().toLowerCase();
  if (!ctype || !EVIDENCE_ALLOWED_CONTENT_TYPES.has(ctype)) {
    return `Tipo não permitido: ${ctype || "(vazio)"}`;
  }
  if (file.size < 1) {
    return "Arquivo vazio";
  }
  if (file.size > EVIDENCE_MAX_BYTES) {
    return `Arquivo excede o limite de ${EVIDENCE_MAX_BYTES} bytes`;
  }
  return null;
}
