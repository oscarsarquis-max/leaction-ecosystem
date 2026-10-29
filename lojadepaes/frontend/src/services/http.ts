export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function apiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL;
  return typeof configured === "string" ? configured.replace(/\/$/, "") : "";
}

function detailMessage(detail: unknown): string | null {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object") {
    const first = detail[0] as { msg?: unknown };
    if (typeof first.msg === "string" && first.msg.trim()) {
      return first.msg;
    }
  }
  return null;
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${apiBaseUrl()}${path}`;
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body != null && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      credentials: "include",
      headers,
    });
  } catch {
    throw new ApiError(0, "rede-indisponivel");
  }
  if (!response.ok) {
    let message = "resposta-invalida";
    try {
      const body = (await response.json()) as { detail?: unknown };
      message = detailMessage(body.detail) || message;
    } catch {
      /* keep fallback */
    }
    throw new ApiError(response.status, message);
  }
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(response.status, "corpo-invalido");
  }
}

export type HealthPayload = {
  status: string;
  service: string;
};

export function getHealth(): Promise<HealthPayload> {
  return requestJson<HealthPayload>("/api/v1/health");
}
