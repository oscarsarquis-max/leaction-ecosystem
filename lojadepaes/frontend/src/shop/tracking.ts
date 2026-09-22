/**
 * Sensor da vitrine → POST /api/tracking/enviar.
 * O navegador nunca vê o segredo do Hub. A sessão fica 30 dias no localStorage.
 */

const STORAGE_KEY = "lojadepaes_crm_session";
const TTL_MS = 30 * 24 * 60 * 60 * 1000;
const ENDPOINT = "/api/tracking/enviar";

function uuidv4(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function readStore(): { id: string; expiresAt: number } | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as { id?: string; expiresAt?: number };
    if (!parsed?.id || !parsed?.expiresAt || Date.now() > Number(parsed.expiresAt)) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return { id: parsed.id, expiresAt: Number(parsed.expiresAt) };
  } catch {
    return null;
  }
}

function writeStore(id: string): string {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ id, expiresAt: Date.now() + TTL_MS }));
  } catch {
    /* modo privado */
  }
  return id;
}

export function getTrackingSessionId(): string {
  const existing = readStore();
  if (existing) {
    return writeStore(existing.id);
  }
  return writeStore(uuidv4());
}

export function trackEvent(
  tipoEvento: string,
  options: { url?: string; idUsuario?: string | null; dados?: Record<string, unknown> } = {},
): void {
  const body: Record<string, unknown> = {
    id_sessao: getTrackingSessionId(),
    tipo_evento: tipoEvento,
    url_pagina: options.url || (typeof window !== "undefined" ? window.location.pathname : "/"),
  };
  if (options.idUsuario) {
    body.id_usuario = options.idUsuario;
  }
  if (options.dados && typeof options.dados === "object" && !Array.isArray(options.dados)) {
    body.dados = options.dados;
  }
  try {
    void fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      keepalive: true,
    }).catch(() => undefined);
  } catch {
    /* a vitrine não depende do rastro */
  }
}

function paginaPublica(path: string): string {
  if (path.startsWith("/pedido/") && path !== "/pedido/novo") {
    return "/pedido";
  }
  return path;
}

export function trackPageview(path: string): void {
  if (path.startsWith("/admin") || path.startsWith("/ativar")) {
    return;
  }
  const pagina = paginaPublica(path);
  trackEvent("pageview", { url: pagina, dados: { pagina } });
}
