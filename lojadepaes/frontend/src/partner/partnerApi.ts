import type { Partner, PartnerProduct, ProductCombo, ProductReview } from "../admin/marketplace/types";

export const PARTNER_API = "/api/v1/partner";

export type PartnerSession = {
  csrf_token: string;
  email: string;
  partner: Partner;
};

export type HouseBread = { slug: string; name: string; price_cents: number | null };

export type UploadedPhoto = { id: string; url: string };

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
  if (init?.body && !(init.body instanceof FormData)) {
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

/** Pedido de combo do parceiro (M8): só a parte dele. */
export type PartnerOrder = {
  id: string;
  public_reference: string;
  combo_ref: string;
  product_name: string;
  house_product_name: string;
  requested_date: string;
  customer_name: string;
  address_line: string;
  /** Quantidade do seu produto neste pedido. */
  item_quantity: number;
  /** Valor total do seu produto (quantidade × preço), congelado no pedido. */
  item_cents: number;
  freight_cents: number | null;
  fee_cents: number;
  status: string;
  accept_deadline?: string | null;
  refuse_reason?: string | null;
};

export type PartnerMpStatus = {
  /** Recebimento pelo Mercado Pago ligado na Loja (chave do Pay). */
  available: boolean;
  connected: boolean;
  nickname?: string | null;
  connected_at?: string | null;
  /** connected · revoked · error · null */
  status?: string | null;
};

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
  combos: () => partnerRequest<ProductCombo[]>(`${PARTNER_API}/combos`),
  createCombo: (body: { partner_product_id: string; house_product_slug: string; reason: string }) =>
    partnerRequest<ProductCombo>(`${PARTNER_API}/combos`, { method: "POST", body: JSON.stringify(body) }),
  resubmitCombo: (id: string, body: { house_product_slug: string; reason: string }) =>
    partnerRequest<ProductCombo>(`${PARTNER_API}/combos/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  mpStatus: () => partnerRequest<PartnerMpStatus>(`${PARTNER_API}/mp`),
  mpConnect: () => partnerRequest<{ url: string }>(`${PARTNER_API}/mp/connect`, { method: "POST" }),
  mpDisconnect: () => partnerRequest<void>(`${PARTNER_API}/mp`, { method: "DELETE" }),
  orders: () => partnerRequest<PartnerOrder[]>(`${PARTNER_API}/orders`),
  acceptOrder: (id: string) => partnerRequest<PartnerOrder>(`${PARTNER_API}/orders/${id}/accept`, { method: "POST" }),
  refuseOrder: (id: string, reason: string) =>
    partnerRequest<PartnerOrder>(`${PARTNER_API}/orders/${id}/refuse`, { method: "POST", body: JSON.stringify({ reason }) }),
  deliveredOrder: (id: string) => partnerRequest<PartnerOrder>(`${PARTNER_API}/orders/${id}/delivered`, { method: "POST" }),
  uploadPhoto: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return partnerRequest<UploadedPhoto>(`${PARTNER_API}/media`, { method: "POST", body: form });
  },
};

/** Pães publicados da casa, pela vitrine pública. Só leitura. */
export async function houseBreads(): Promise<HouseBread[]> {
  const breads: HouseBread[] = [];
  for (let page = 1; page <= 5; page += 1) {
    const list = await partnerRequest<{
      items: Array<{ slug: string; name: string; from_price?: { cents: number | null } | null }>;
      total: number;
      page_size: number;
    }>(`/api/v1/catalog/products?page=${page}&page_size=50`);
    breads.push(
      ...list.items.map((item) => ({ slug: item.slug, name: item.name, price_cents: item.from_price?.cents ?? null })),
    );
    if (page * list.page_size >= list.total) {
      break;
    }
  }
  return breads.sort((a, b) => a.name.localeCompare(b.name, "pt-BR"));
}
