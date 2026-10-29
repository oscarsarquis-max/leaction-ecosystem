import { requestJson } from "../../services/http";

export type LibraryPhoto = { src: string; alt: string };

export type LibrarySource = { label: string; detail: string; href?: string };

export type LibraryArticle = {
  slug: string;
  kicker: string;
  title: string;
  summary: string;
  reading_label: string;
  href: string;
  photo: LibraryPhoto;
  calculator_href: string;
  version: number;
  id?: string;
  body_markdown?: string;
  sources?: LibrarySource[];
};

export type LibraryOffer = {
  id?: string;
  sku?: string;
  name?: string;
  price?: number;
  currency?: string;
  period?: string;
  credits?: number;
  checkout_ready?: boolean;
  optional?: boolean;
  role?: string;
};

export type LibraryPlan = {
  configured: boolean;
  checkout_ready: boolean;
  source: string;
  sku?: string;
  name?: string;
  price?: number;
  currency?: string;
  period?: string;
  credits?: number;
  authorized_initial_brl?: number;
  authorized_complementary_brl?: number;
  authorized_pack_brl?: number;
  plans_href?: string;
  credit_cost?: number;
  accumulate?: boolean;
  message?: string;
  benefits?: string[];
  features?: string[];
  suggested_sku?: string;
  suggested_complementary_sku?: string;
  principal?: LibraryOffer;
  complementary?: LibraryOffer;
  pack?: LibraryOffer;
  cycle_rules?: { notes?: string[]; accumulate?: boolean };
};

export type LibraryAccess = {
  identified: boolean;
  authorized: boolean;
  reason?: string | null;
  message?: string;
  plan?: LibraryPlan;
  credits?: number | null;
  valid_until?: string | null;
  balance_source?: string | null;
  credit_cost?: number;
  complementary_active?: boolean;
  complementary_eligible?: boolean;
  subscription_status?: "active" | "pending" | "none" | "cancelled_with_access";
  ai_credits?: number | null;
  monthly_credits?: number | null;
  pack_credits?: number | null;
  pack_expires?: boolean;
  can_use_ai?: boolean;
  subscriber_discount?: boolean;
  plans_href?: string;
  exhausted?: boolean;
  subscriptions?: Array<{ sku?: string; status?: string; cancelable?: boolean }>;
  cancel_policy?: string;
};

export type CalculatorResult = {
  mode: string;
  flour_g: number;
  hydration_pct: number;
  salt_pct: number;
  preferment_flour_pct: number;
  levain_hydration_pct: number;
  levain_mode: string;
  final_mix: {
    flour_g: number;
    water_g: number;
    salt_g: number;
    levain_g: number;
    extras: Array<{ name: string; baker_pct: number; grams: number }>;
  };
  levain: { flour_g: number; water_g: number; weight_g: number };
  totals: { flour_g: number; water_g: number; salt_g: number; levain_g: number; dough_g: number };
  notes: string[];
  scale_factor?: number;
  target_dough_g?: number;
};

export function fetchLibraryArticles() {
  return requestJson<{ items: LibraryArticle[] }>("/api/v1/biblioteca/artigos");
}

export function fetchLibraryArticle(slug: string) {
  return requestJson<LibraryArticle>(`/api/v1/biblioteca/artigos/${encodeURIComponent(slug)}`);
}

export function computeFormula(body: Record<string, unknown>) {
  return requestJson<CalculatorResult>("/api/v1/biblioteca/calculadora", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchLibraryPlan() {
  return requestJson<LibraryPlan>("/api/v1/biblioteca/plano");
}

export function fetchLibraryAccess() {
  return requestJson<LibraryAccess>("/api/v1/biblioteca/acesso");
}

export function identifyLibrary(payload: { name?: string; email?: string; cpf?: string }) {
  return requestJson<{ ok: boolean; message?: string; email_masked?: string }>("/api/v1/biblioteca/identificar", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function verifyLibrary(payload: { email?: string; cpf?: string; code: string }) {
  return requestJson<LibraryAccess & { ok: boolean }>("/api/v1/biblioteca/verificar", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function startLibraryCheckout(returnTo: string, sku?: string) {
  return requestJson<{ checkout_url: string }>("/api/v1/biblioteca/assinatura", {
    method: "POST",
    body: JSON.stringify({ return_to: returnTo, sku: sku || "" }),
  });
}

export function cancelLibrarySubscription(sku?: string) {
  return requestJson<{ ok?: boolean; message?: string }>("/api/v1/biblioteca/assinatura/cancelar", {
    method: "POST",
    body: JSON.stringify({ sku: sku || "" }),
  });
}

export function moneyLabel(price?: number, currency = "BRL", period = "mês") {
  if (typeof price !== "number") {
    return "";
  }
  const prefix = currency === "BRL" ? "R$" : currency;
  return `${prefix} ${price.toFixed(2).replace(".", ",")} / ${period}`;
}
