const CSRF_KEY = "lojadepaes_admin_csrf";
const TZ_KEY = "lojadepaes_bakery_tz";

export class AdminApiError extends Error {
  readonly status: number;
  readonly code: string | null;

  constructor(status: number, message: string, code: string | null = null) {
    super(message);
    this.name = "AdminApiError";
    this.status = status;
    this.code = code;
  }
}

function apiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL;
  return typeof configured === "string" ? configured.replace(/\/$/, "") : "";
}

export function bakeryTimeZone(): string {
  return localStorage.getItem(TZ_KEY) || sessionStorage.getItem(TZ_KEY) || "America/Sao_Paulo";
}

export function storedCsrf(): string | null {
  return localStorage.getItem(CSRF_KEY) || sessionStorage.getItem(CSRF_KEY);
}

function sessionApiPath(path: string): boolean {
  return path.split("?")[0] === "/api/v1/admin/session";
}

export function rememberSession(csrf: string, timezone: string): void {
  if (!csrf) {
    return;
  }
  localStorage.setItem(CSRF_KEY, csrf);
  localStorage.setItem(TZ_KEY, timezone);
  sessionStorage.removeItem(CSRF_KEY);
  sessionStorage.removeItem(TZ_KEY);
}

export function clearSession(): void {
  localStorage.removeItem(CSRF_KEY);
  localStorage.removeItem(TZ_KEY);
  sessionStorage.removeItem(CSRF_KEY);
  sessionStorage.removeItem(TZ_KEY);
  sessionStorage.removeItem("lojadepaes_week_recipe_unsaved");
}

function fieldLabel(path: unknown): string {
  if (!Array.isArray(path) || path.length === 0) {
    return "campo";
  }
  const last = path[path.length - 1];
  return typeof last === "string" ? last : "campo";
}

function detailMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object" || !("detail" in payload)) {
    return fallback;
  }
  const detail = (payload as { detail: unknown }).detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          const msg = String((item as { msg: unknown }).msg);
          const loc = "loc" in item ? fieldLabel((item as { loc: unknown }).loc) : "";
          return loc ? `${loc}: ${msg}` : msg;
        }
        return "";
      })
      .filter(Boolean);
    if (parts.length) {
      return parts.join("; ");
    }
  }
  return fallback;
}

function payloadCode(payload: unknown): string | null {
  if (payload && typeof payload === "object" && "code" in payload) {
    const code = (payload as { code: unknown }).code;
    if (typeof code === "string") {
      return code;
    }
  }
  return null;
}

export function actionErrorMessage(error: unknown, fallback: string): string {
  if (!(error instanceof AdminApiError)) {
    return fallback;
  }
  if (error.status === 401) {
    return "Sessão encerrada. Entre de novo; o texto desta receita ficou guardado neste navegador.";
  }
  if (error.status === 403 && error.message === "requisição recusada") {
    return "A sessão de segurança foi renovada (outra aba da loja costuma causar isso). O texto foi mantido. Tente salvar de novo.";
  }
  if (error.status === 403 && error.message === "origem não permitida") {
    return "Este endereço não está autorizado a gravar. Abra a loja pelo site oficial e tente de novo.";
  }
  if (error.status === 0) {
    return "Não foi possível falar com a API. O texto preenchido foi mantido.";
  }
  return error.message || fallback;
}

type RequestOptions = {
  skipRetry?: boolean;
};

export async function adminRequest<T>(path: string, init?: RequestInit, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  const method = (init?.method ?? "GET").toUpperCase();
  const csrf = storedCsrf();
  if (csrf) {
    headers["X-CSRF-Token"] = csrf;
  }
  if (method !== "GET" && method !== "HEAD" && init?.body && !(init.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
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
  if (
    !response.ok &&
    !options.skipRetry &&
    response.status === 403 &&
    detailMessage(payload, "") === "requisição recusada" &&
    !sessionApiPath(path)
  ) {
    const refreshed = await adminRequest<{ csrf_token: string; bakery_timezone: string }>(
      "/api/v1/admin/session?rotate=1",
      { method: "GET" },
      { skipRetry: true },
    );
    rememberSession(refreshed.csrf_token, refreshed.bakery_timezone);
    return adminRequest<T>(path, init, { skipRetry: true });
  }
  if (!response.ok) {
    throw new AdminApiError(response.status, detailMessage(payload, "Não foi possível concluir a ação."), payloadCode(payload));
  }
  return payload as T;
}
