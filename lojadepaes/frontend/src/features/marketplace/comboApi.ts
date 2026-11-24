import { requestJson } from "../../services/http";
import type { DeliveryAddressInput } from "../../shop/DeliveryAddressFields";
import type { PublicDelivery, PublicPartnerBrand } from "./publicApi";

/** Combo à venda (M8). Contrato no desenho técnico M8. */
export type ComboSummary = {
  id: string;
  reason: string;
  bread: {
    slug: string;
    name: string;
    variants: Array<{ id: string; name: string; price_cents: number }>;
  };
  product: {
    id: string;
    name: string;
    description: string;
    photos: string[];
    price_cents: number;
  };
  partner: PublicPartnerBrand;
  delivery: PublicDelivery;
  /** Preço do pão nesta combo (acordo da Loja), por pão, em qualquer apresentação. Nulo = preço da vitrine. */
  house_unit_price_cents?: number | null;
};

/** Até onde o cliente escolhe a quantidade de pães e de itens do parceiro numa combo. */
export const COMBO_MAX_QUANTITY = 10;

export type ComboOrderInput = DeliveryAddressInput & {
  variant_id: string;
  bread_quantity: number;
  item_quantity: number;
  requested_date: string;
  preferred_time: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  idempotency_key: string;
  /** Total que o cliente viu (preços de face). O servidor recusa se mudou. */
  quoted_cents: number;
};

export type ComboOrderCreated = { combo_ref: string; token: string };

export type PartnerOrderStatus = "submitted" | "accepted" | "refused" | "expired" | "cancelled" | "delivered";

export type ComboOrderView = {
  combo_ref: string;
  requested_date: string;
  total_cents: number;
  house: {
    public_reference: string;
    status: string;
    status_label: string;
    amount_cents: number;
    /** Link do acompanhamento do pedido da Loja (já com o token). */
    order_url: string;
  };
  partners: Array<{
    id: string;
    public_reference: string;
    brand: PublicPartnerBrand;
    product_name: string;
    status: PartnerOrderStatus;
    amount_cents: number;
    refuse_reason?: string | null;
    accept_deadline?: string | null;
  }>;
};

const COMBOS = "/api/v1/combos";

export function fetchCombo(id: string): Promise<ComboSummary> {
  return requestJson<ComboSummary>(`${COMBOS}/${encodeURIComponent(id)}`);
}

export function submitComboOrder(id: string, input: ComboOrderInput): Promise<ComboOrderCreated> {
  return requestJson<ComboOrderCreated>(`${COMBOS}/${encodeURIComponent(id)}/orders`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function fetchComboOrder(ref: string, token: string): Promise<ComboOrderView> {
  return requestJson<ComboOrderView>(
    `${COMBOS}/pedido/${encodeURIComponent(ref)}?t=${encodeURIComponent(token)}`,
  );
}

export function comboCheckoutHref(id: string): string {
  return `/combo/${encodeURIComponent(id)}`;
}

export function comboOrderHref(ref: string, token: string): string {
  return `/combo/pedido/${encodeURIComponent(ref)}?t=${encodeURIComponent(token)}`;
}

/** O parceiro entrega nesta cidade/bairro? Lista vazia = sem restrição informada. */
export function partnerDelivers(delivery: PublicDelivery, city: string, district: string): boolean {
  const norm = (value: string) =>
    value
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .trim()
      .toLowerCase();
  const cities = delivery.cities.map(norm);
  const districts = delivery.districts.map(norm);
  if (!cities.length && !districts.length) return true;
  return cities.includes(norm(city)) || (districts.length > 0 && districts.includes(norm(district)));
}

/** Data mínima pelo prazo do parceiro (dias corridos a partir de hoje, no fuso da Loja). */
export function partnerEarliestDate(delivery: PublicDelivery, todayIso: string): string {
  const days = delivery.days ?? 0;
  const [y, m, d] = todayIso.split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d + days));
  return date.toISOString().slice(0, 10);
}
