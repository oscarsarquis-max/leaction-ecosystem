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

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${apiBaseUrl()}${path}`;
  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers: { Accept: "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(0, "rede-indisponivel");
  }
  if (!response.ok) {
    throw new ApiError(response.status, "resposta-invalida");
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
