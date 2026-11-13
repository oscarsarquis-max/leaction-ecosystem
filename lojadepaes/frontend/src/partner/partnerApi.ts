import type { Partner, PartnerProduct, ProductReview } from "../admin/marketplace/types";

export const PARTNER_API = "/api/v1/partner";

export type PartnerSession = {
  csrf_token: string;
  email: string;
  partner: Partner;
};

export type HouseBread = { slug: string; name: string };

export class PartnerApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "PartnerApiError";
    this.status = status;
  }
}

let csrf: string | null = null;

export function rememberCsrf(token: string | null): void {
  csrf = token;
}

function apiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL;
  return typeof configured === "string" ? configured.replace(/\/$/, "") : "";
}

function detailOf(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object" && "msg" in detail[0]) {
      return "Confira os campos preenchidos.";
    }
  }
  return fallback;
}

export async function partnerRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (init?.body) {
    headers["Content-Type"] = "application/json";
  }
  if (csrf && method !== "GET") {
    headers["X-CSRF-Token"] = csrf;
  }
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, { ...init, method, credentials: "include", headers });
  } catch {
    throw new PartnerApiError(0, "Sem conexão com a Loja de Pães. Tente de novo.");
  }
  if (response.status === 204) {
    return undefined as T;
  }
  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text) as unknown;
    } catch {
      payload = null;
    }
  }
  if (!response.ok) {
    throw new PartnerApiError(response.status, detailOf(payload, "Não foi possível concluir. Tente de novo."));
  }
  return payload as T;
}

export const partnerApi = {
  me: () => partnerRequest<PartnerSession>(`${PARTNER_API}/me`),
  login: (email: string, password: string) =>
    partnerRequest<PartnerSession>(`${PARTNER_API}/login`, { method: "POST", body: JSON.stringify({ email, password }) }),
  accept: (token: string, password: string) =>
    partnerRequest<PartnerSession>(`${PARTNER_API}/invite/accept`, {
      method: "POST",
      body: JSON.stringify({ token, password }),
    }),
  logout: () => partnerRequest<void>(`${PARTNER_API}/logout`, { method: "POST" }),
  profile: (body: Partial<Partner>) =>
    partnerRequest<Partner>(`${PARTNER_API}/profile`, { method: "PATCH", body: JSON.stringify(body) }),
  products: () => partnerRequest<PartnerProduct[]>(`${PARTNER_API}/products`),
  createProduct: (body: unknown) =>
    partnerRequest<PartnerProduct>(`${PARTNER_API}/products`, { method: "POST", body: JSON.stringify(body) }),
  updateProduct: (id: string, body: unknown) =>
    partnerRequest<PartnerProduct>(`${PARTNER_API}/products/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  submitProduct: (id: string) => partnerRequest<PartnerProduct>(`${PARTNER_API}/products/${id}/submit`, { method: "POST" }),
  reviews: (id: string) => partnerRequest<ProductReview[]>(`${PARTNER_API}/products/${id}/reviews`),
};

/** Pães publicados da casa, pela vitrine pública. Só leitura. */
export async function houseBreads(): Promise<HouseBread[]> {
  const breads: HouseBread[] = [];
  for (let page = 1; page <= 5; page += 1) {
    const list = await partnerRequest<{ items: HouseBread[]; total: number; page_size: number }>(
      `/api/v1/catalog/products?page=${page}&page_size=50`,
    );
    breads.push(...list.items.map((item) => ({ slug: item.slug, name: item.name })));
    if (page * list.page_size >= list.total) {
      break;
    }
  }
  return breads.sort((a, b) => a.name.localeCompare(b.name, "pt-BR"));
}
