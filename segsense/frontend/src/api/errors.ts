export const AUTHENTICATION_REQUIRED = 'AUTHENTICATION_REQUIRED';
export const ACCESS_DENIED = 'ACCESS_DENIED';

export type SecurityErrorCode = typeof AUTHENTICATION_REQUIRED | typeof ACCESS_DENIED;

export class ApiClientError extends Error {
  readonly status: number;
  readonly code: string;
  readonly correlationId?: string;

  constructor(status: number, code: string, message: string, correlationId?: string) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.code = code;
    this.correlationId = correlationId;
  }

  get authenticationRequired(): boolean {
    return this.status === 401 || this.code === AUTHENTICATION_REQUIRED;
  }

  get accessDenied(): boolean {
    return this.status === 403 || this.code === ACCESS_DENIED;
  }
}

export function parseApiError(status: number, payload: unknown): ApiClientError {
  if (payload !== null && typeof payload === 'object') {
    const record = payload as Record<string, unknown>;
    const code = record['code'];
    const message = record['message'];
    const correlationId = record['correlationId'];
    if (typeof code === 'string' && typeof message === 'string') {
      return new ApiClientError(
        status,
        code,
        message,
        typeof correlationId === 'string' ? correlationId : undefined,
      );
    }
  }
  return new ApiClientError(status, 'HTTP_ERROR', `HTTP ${String(status)}`);
}

export async function readApiError(response: Response): Promise<ApiClientError> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = undefined;
  }
  return parseApiError(response.status, payload);
}
