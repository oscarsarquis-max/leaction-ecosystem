export type ApiErrorCode =
  | "nao_autenticado"
  | "nao_autorizado"
  | "nao_encontrado"
  | "conflito"
  | "regra_dominio"
  | "contrato_invalido"
  | "indisponivel"
  | "rede"
  | "cancelado";

export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly status: number;

  constructor(code: ApiErrorCode, message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

const STATUS_CODE: Record<number, ApiErrorCode> = {
  400: "contrato_invalido",
  401: "nao_autenticado",
  403: "nao_autorizado",
  404: "nao_encontrado",
  409: "conflito",
  422: "regra_dominio",
  503: "indisponivel",
};

const FALLBACK_MESSAGE: Record<ApiErrorCode, string> = {
  nao_autenticado: "Sessão expirada ou não autenticada.",
  nao_autorizado: "Você não tem permissão para este recurso.",
  nao_encontrado: "Recurso inexistente ou invisível.",
  conflito: "O estado mudou. Atualize e tente de novo.",
  regra_dominio: "A operação viola uma regra de domínio.",
  contrato_invalido: "Os dados enviados são inválidos.",
  indisponivel: "A API está temporariamente indisponível.",
  rede: "Não foi possível contactar a API.",
  cancelado: "A consulta anterior foi substituída.",
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" ? (value as Record<string, unknown>) : null;
}

export function errorFromResponse(status: number, body: unknown): ApiError {
  const record = asRecord(body);
  const detailRecord = asRecord(record?.detail);
  const rawCode =
    (typeof record?.code === "string" && record.code) ||
    (typeof detailRecord?.code === "string" && detailRecord.code) ||
    "";
  const detail = typeof record?.detail === "string" ? record.detail : "";
  const message =
    (typeof record?.message === "string" && record.message) ||
    (typeof detailRecord?.message === "string" && detailRecord.message) ||
    detail ||
    FALLBACK_MESSAGE[STATUS_CODE[status] ?? "rede"];
  const code = (STATUS_CODE[status] ??
    (rawCode === "nao_autenticado" ? "nao_autenticado" : "rede")) as ApiErrorCode;
  return new ApiError(code, message, status);
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error && error.name === "AbortError") return FALLBACK_MESSAGE.cancelado;
  return FALLBACK_MESSAGE.rede;
}

/** Cancelamento/substituição de consulta — não é erro apresentável na UI. */
export function isCancelledError(error: unknown): boolean {
  if (error instanceof ApiError && error.code === "cancelado") return true;
  if (error instanceof DOMException && error.name === "AbortError") return true;
  if (error instanceof Error && error.name === "AbortError") return true;
  return false;
}

/**
 * Aplica erro de carga somente se a geração ainda for a atual, o componente
 * estiver montado e o erro não for cancelamento.
 */
export function reportLoadError(
  error: unknown,
  setError: (error: unknown) => void,
  options: { alive?: boolean; generation?: number; expectedGeneration?: number } = {},
): void {
  if (options.alive === false) return;
  if (
    options.generation != null &&
    options.expectedGeneration != null &&
    options.generation !== options.expectedGeneration
  ) {
    return;
  }
  if (isCancelledError(error)) return;
  setError(error);
}

export { FALLBACK_MESSAGE };
