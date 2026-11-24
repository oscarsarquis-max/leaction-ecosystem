import { requestJson } from "../../services/http";

export type PublicPartnerBrand = {
  brand_name: string;
  brand_slug: string;
  highlight_hex: string;
  logo_url: string;
};

export type PublicDelivery = {
  cities: string[];
  districts: string[];
  days: number | null;
  freight_cents: number | null;
  perishable: boolean;
};

export type PublicPartnerProduct = {
  id: string;
  name: string;
  description: string;
  photos: string[];
  price_cents: number;
  category: string;
  why_pairs?: string;
  delivery: PublicDelivery;
  partner?: PublicPartnerBrand;
  pairings?: Array<{ house_product_slug: string; house_product_name: string | null; reason: string }>;
};

export type PublicCombo = {
  id: string;
  product_id: string;
  product_name: string;
  house_product_slug?: string;
  house_product_name?: string | null;
  reason: string;
  price_cents: number;
  freight_cents: number | null;
  /** Preço do pão nesta combo (acordo da Loja). Nulo = preço da vitrine. */
  house_unit_price_cents?: number | null;
  partner?: PublicPartnerBrand;
};

export type BreadPartners = {
  products: PublicPartnerProduct[];
  combos: PublicCombo[];
  covered_categories: string[];
};

export type PublicPartnerPage = {
  partner: PublicPartnerBrand & { photo_url: string; story: string; city: string; region: string };
  products: PublicPartnerProduct[];
  combos: PublicCombo[];
};

const BASE = "/api/v1/marketplace/public";

/** Parceiros que acompanham um pão. Com o marketplace desligado a rota responde 404 e a vitrine não muda. */
export function fetchBreadPartners(slug: string): Promise<BreadPartners> {
  return requestJson<BreadPartners>(`${BASE}/breads/${encodeURIComponent(slug)}`);
}

export function fetchPartnerPage(slug: string): Promise<PublicPartnerPage> {
  return requestJson<PublicPartnerPage>(`${BASE}/partners/${encodeURIComponent(slug)}`);
}

export function partnerHref(slug: string): string {
  return `/parceiros/${encodeURIComponent(slug)}`;
}

export function deliveryLine(delivery: PublicDelivery, freightLabel: (cents: number) => string): string {
  const where = [...delivery.cities, ...delivery.districts];
  const parts: string[] = [];
  if (where.length) parts.push(where.slice(0, 3).join(", ") + (where.length > 3 ? " e região" : ""));
  if (delivery.days !== null) parts.push(delivery.days === 0 ? "no mesmo dia" : `em até ${delivery.days} ${delivery.days === 1 ? "dia" : "dias"}`);
  if (delivery.freight_cents !== null) parts.push(delivery.freight_cents === 0 ? "frete grátis" : `frete ${freightLabel(delivery.freight_cents)}`);
  return parts.join(" · ");
}
