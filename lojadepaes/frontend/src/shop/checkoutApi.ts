import { ApiError, requestJson } from "../services/http";

export type StorefrontAdaptation = {
  status: string;
  customer_text: string;
  reason: string | null;
  bakery_response: string;
  client_decision: string | null;
  applies_to_all_units_of_this_line: boolean;
};

export type StorefrontPayment = {
  financial_status: string | null;
  expected_cents: number | null;
  amount_paid_cents: number | null;
  external_reference: string | null;
  sanitized_error: string | null;
  method: string | null;
  pix: {
    qr_code: string | null;
    qr_code_base64: string | null;
    ticket_url: string | null;
    date_of_expiration: string | null;
    mp_payment_id: string | null;
  } | null;
};

export type StorefrontOrder = {
  public_reference: string;
  status: string;
  visitor_state: string;
  requested_date: string | null;
  proposed_date: string | null;
  confirmed: boolean;
  holds_capacity: boolean;
  financially_settled: boolean;
  customer_name: string | null;
  customer_email: string | null;
  delivery_address: {
    street: string;
    number: string | null;
    complement: string | null;
    district: string | null;
    city: string | null;
    state: string | null;
    postal_code: string | null;
  } | null;
  total_cents: number | null;
  currency: string;
  items: Array<{
    id?: string;
    product_name: string;
    variant_name: string;
    quantity: number;
    line_cents: number;
    adaptation?: StorefrontAdaptation | null;
  }>;
  payment: StorefrontPayment;
  notice: string;
  access_token?: string | null;
};

export type StorefrontQuote = {
  requested_date: string;
  currency: string;
  subtotal_cents: number;
  total_cents: number;
  date_label: string;
  occupies_capacity: boolean;
  items: Array<{
    product_id: string;
    variant_id: string;
    product_name: string;
    variant_name: string;
    quantity: number;
    unit_cents: number;
    line_cents: number;
  }>;
};

export type StorefrontCheckout = {
  checkout_url: string | null;
  external_reference: string | null;
  expected_cents: number;
  reused: boolean;
  method: string;
  pix: StorefrontPayment["pix"];
};

const TOKEN_PREFIX = "lojadepaes_order_token_";

export function saveOrderToken(reference: string, token: string): void {
  sessionStorage.setItem(`${TOKEN_PREFIX}${reference}`, token);
}

export function readOrderToken(reference: string): string | null {
  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("token");
  if (fromQuery) {
    sessionStorage.setItem(`${TOKEN_PREFIX}${reference}`, fromQuery);
    return fromQuery;
  }
  return sessionStorage.getItem(`${TOKEN_PREFIX}${reference}`);
}

function tokenHeaders(reference: string): HeadersInit {
  const token = readOrderToken(reference);
  return token ? { "X-Order-Token": token } : {};
}

export function checkoutErrorMessage(reason: unknown): string {
  if (reason instanceof ApiError && reason.message && reason.message !== "resposta-invalida") {
    return reason.message;
  }
  if (reason instanceof ApiError && reason.status === 0) {
    return "Não foi possível falar com a padaria agora.";
  }
  return "Não foi possível concluir esta etapa.";
}

export type StorefrontItemPayload = {
  variant_id: string;
  quantity: number;
  adaptation_text?: string;
  adaptation_reason?: "preference" | "dietary_restriction";
};

export function quoteOrder(payload: {
  requested_date: string;
  items: StorefrontItemPayload[];
}): Promise<StorefrontQuote> {
  return requestJson<StorefrontQuote>("/api/v1/storefront/quote", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function submitOrder(payload: {
  requested_date: string;
  items: StorefrontItemPayload[];
  quoted_cents: number;
  customer_name: string;
  customer_email: string;
  customer_phone?: string;
  customer_note?: string;
  delivery_street?: string;
  delivery_number?: string;
  delivery_complement?: string;
  delivery_district?: string;
  delivery_city?: string;
  delivery_state?: string;
  delivery_postal_code?: string;
  idempotency_key: string;
  id_sessao?: string;
}): Promise<StorefrontOrder> {
  return requestJson<StorefrontOrder>("/api/v1/storefront/orders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function fetchStorefrontOrder(reference: string): Promise<StorefrontOrder> {
  return requestJson<StorefrontOrder>(`/api/v1/storefront/orders/${encodeURIComponent(reference)}`, {
    headers: tokenHeaders(reference),
  });
}

export function startStorefrontCheckout(
  reference: string,
  method: "pix" | "card",
  replace = false,
): Promise<StorefrontCheckout> {
  return requestJson<StorefrontCheckout>(
    `/api/v1/storefront/orders/${encodeURIComponent(reference)}/checkout`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...tokenHeaders(reference) },
      body: JSON.stringify({ method, replace }),
    },
  );
}

export function reconcileStorefrontOrder(reference: string): Promise<StorefrontOrder> {
  return requestJson<StorefrontOrder>(
    `/api/v1/storefront/orders/${encodeURIComponent(reference)}/reconcile`,
    {
      method: "POST",
      headers: tokenHeaders(reference),
    },
  );
}

export function acceptProposedDate(reference: string): Promise<StorefrontOrder> {
  return requestJson<StorefrontOrder>(
    `/api/v1/storefront/orders/${encodeURIComponent(reference)}/accept-date`,
    {
      method: "POST",
      headers: tokenHeaders(reference),
    },
  );
}

export function saveDeliveryAddress(
  reference: string,
  address: {
    delivery_street: string;
    delivery_number: string;
    delivery_complement: string;
    delivery_district: string;
    delivery_city: string;
    delivery_state: string;
    delivery_postal_code: string;
  },
): Promise<StorefrontOrder> {
  return requestJson<StorefrontOrder>(
    `/api/v1/storefront/orders/${encodeURIComponent(reference)}/delivery-address`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...tokenHeaders(reference) },
      body: JSON.stringify(address),
    },
  );
}

export function respondAdaptation(
  reference: string,
  itemId: string,
  decision: "accept_alternative" | "decline",
): Promise<StorefrontOrder> {
  return requestJson<StorefrontOrder>(
    `/api/v1/storefront/orders/${encodeURIComponent(reference)}/items/${encodeURIComponent(itemId)}/adaptation`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...tokenHeaders(reference) },
      body: JSON.stringify({ decision }),
    },
  );
}

export function goStorefront(path: string): void {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}
