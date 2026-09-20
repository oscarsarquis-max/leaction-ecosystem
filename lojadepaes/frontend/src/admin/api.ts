const CSRF_KEY = "lojadepaes_admin_csrf";
const TZ_KEY = "lojadepaes_bakery_tz";

export class AdminApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "AdminApiError";
    this.status = status;
  }
}

function apiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL;
  return typeof configured === "string" ? configured.replace(/\/$/, "") : "";
}

export function bakeryTimeZone(): string {
  return sessionStorage.getItem(TZ_KEY) || "America/Sao_Paulo";
}

export function storedCsrf(): string | null {
  return sessionStorage.getItem(CSRF_KEY);
}

export function rememberSession(csrf: string, timezone: string): void {
  sessionStorage.setItem(CSRF_KEY, csrf);
  sessionStorage.setItem(TZ_KEY, timezone);
}

export function clearSession(): void {
  sessionStorage.removeItem(CSRF_KEY);
  sessionStorage.removeItem(TZ_KEY);
}

function detailMessage(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
  }
  return fallback;
}

export async function adminRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  const method = (init?.method ?? "GET").toUpperCase();
  if (method !== "GET" && method !== "HEAD") {
    const csrf = storedCsrf();
    if (csrf) {
      headers["X-CSRF-Token"] = csrf;
    }
    if (init?.body && !(init.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
  }
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      method,
      credentials: "include",
      headers,
    });
  } catch {
    throw new AdminApiError(0, "Não foi possível falar com a API.");
  }
  if (response.status === 204) {
    return undefined as T;
  }
  let payload: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      payload = JSON.parse(text) as unknown;
    } catch {
      payload = null;
    }
  }
  if (!response.ok) {
    throw new AdminApiError(response.status, detailMessage(payload, "Não foi possível concluir a ação."));
  }
  return payload as T;
}
