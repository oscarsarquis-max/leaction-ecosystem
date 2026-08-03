/**
 * Central API error handling — mirrors backend ErrorBody (ADR-003).
 * Never treat opaque HTTP bodies as success.
 */

export type FieldError = {
  field: string;
  code: string;
  message: string;
};

export type ErrorBody = {
  code: string;
  message: string;
  correlation_id: string;
  field_errors?: FieldError[] | null;
};

export class QmindApiError extends Error {
  readonly code: string;
  readonly correlationId: string;
  readonly status: number;
  readonly fieldErrors: FieldError[];

  constructor(status: number, body: ErrorBody) {
    super(body.message || `Request failed (${status})`);
    this.name = "QmindApiError";
    this.status = status;
    this.code = body.code || "http_error";
    this.correlationId = body.correlation_id || "";
    this.fieldErrors = body.field_errors ?? [];
  }
}

export function isErrorBody(value: unknown): value is ErrorBody {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return typeof v.code === "string" && typeof v.message === "string";
}

export async function parseErrorResponse(response: Response): Promise<QmindApiError> {
  let body: ErrorBody = {
    code: "http_error",
    message: response.statusText || "Request failed",
    correlation_id: "",
  };
  try {
    const json: unknown = await response.json();
    if (isErrorBody(json)) {
      body = {
        code: json.code,
        message: json.message,
        correlation_id: typeof json.correlation_id === "string" ? json.correlation_id : "",
        field_errors: Array.isArray(json.field_errors) ? json.field_errors : null,
      };
    }
  } catch {
    // non-JSON error body — keep defaults (never leak raw HTML/stack)
  }
  return new QmindApiError(response.status, body);
}
