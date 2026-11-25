export type PartnerLink = {
  id: string;
  partner_id: string;
  category: string;
  link_type: string;
  starts_on: string;
  ends_on: string | null;
};

export type Partner = {
  id: string;
  partner_type: string;
  brand_name: string;
  brand_slug: string;
  logo_url: string;
  photo_url: string;
  story: string;
  city: string;
  region: string;
  highlight_hex: string;
  document: string;
  contact: string;
  status: string;
  fee_cents: number;
  email?: string;
  links?: PartnerLink[];
  /** Conta do Mercado Pago conectada para receber (null = recebimento ainda não disponível). */
  mp_connected?: boolean | null;
  mp_nickname?: string | null;
};

export type PartnerCreated = Partner & {
  invite_link: string;
  invite_expires_at: string;
};

export type Pairing = {
  id: string;
  house_product_slug: string;
  house_product_name?: string | null;
  reason: string;
};

export type PartnerProduct = {
  id: string;
  partner_id: string;
  category: string;
  name: string;
  description: string;
  photos: string[];
  price_cents: number;
  is_available: boolean;
  delivery_cities: string[];
  delivery_districts: string[];
  delivery_cep_prefixes: string[];
  delivery_days: number | null;
  freight_cents: number | null;
  perishable: boolean;
  status: string;
  updated_at?: string;
  pairings: Pairing[];
};

export type ProductCombo = {
  id: string;
  partner_id: string;
  partner_product_id: string;
  partner_product_name?: string | null;
  house_product_slug: string;
  house_product_name?: string | null;
  reason: string;
  status: string;
  /** Preço do pão nesta combo (acordo da Loja). Nulo = preço da vitrine. */
  house_unit_price_cents?: number | null;
  review_note?: string | null;
  reviewed_at?: string | null;
  updated_at?: string;
};

export type ProductReview = {
  id: string;
  quality: number;
  visual: number;
  complementarity: number;
  note: string | null;
  decision: string;
  reviewer_ref: string;
  reviewed_at: string;
};
