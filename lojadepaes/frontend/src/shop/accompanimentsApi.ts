import { requestJson } from "../services/http";

export type AccompanimentBread = {
  slug: string;
  name: string;
  href: string;
};

export type AccompanimentRecipe = {
  slug: string;
  title: string;
  href: string;
};

export type AccompanimentCard = {
  id: string;
  name: string;
  description: string;
  image_url: string | null;
  occasion: string;
  story_title: string;
  story_lead: string;
  why_pairs: string;
  serving_tip: string;
  price_label: string | null;
  price_fresh: boolean;
  price_as_of: string | null;
  outbound_href: string | null;
  outbound_label?: string | null;
  marketplace?: string | null;
  vendor?: string;
  external_notice?: string;
  demo?: boolean;
  commercial_enabled?: boolean;
  story_href: string;
  category?: string;
  hub_offer_id?: string;
  related_product_slugs: string[];
  related_breads: AccompanimentBread[];
  related_recipes: AccompanimentRecipe[];
};

export type AccompanimentStory = {
  occasion: string;
  title: string;
  lead: string;
  items: AccompanimentCard[];
};

export type AccompanimentsCatalog = {
  enabled: boolean;
  title: string;
  intro: string;
  source_status: string;
  preview?: boolean;
  demo_notice?: string | null;
  commission_note: string | null;
  external_notice: string | null;
  delivery_help: { mode: string; text: string; client_note?: string };
  attribution_ready: boolean;
  stories: AccompanimentStory[];
  items: AccompanimentCard[];
  context?: {
    active: boolean;
    empty: boolean;
    title: string | null;
    summary?: string | null;
    filters: { key: string; label: string }[];
    clear_href: string;
    href?: string;
    bread_name?: string | null;
  };
};

export function fetchAccompaniments(): Promise<AccompanimentsCatalog> {
  const incoming = new URLSearchParams(window.location.search);
  const qs = new URLSearchParams();
  for (const key of ["cats", "tipo", "pao", "ids", "mesa", "cerveja", "forma"]) {
    const value = incoming.get(key);
    if (value) {
      qs.set(key, value);
    }
  }
  const suffix = qs.toString() ? `?${qs}` : "";
  return requestJson<AccompanimentsCatalog>(`/api/v1/accompaniments${suffix}`);
}

export function fetchProductAccompaniments(slug: string): Promise<{
  enabled: boolean;
  commission_note: string | null;
  external_notice: string | null;
  items: AccompanimentCard[];
}> {
  return requestJson(`/api/v1/accompaniments/for-product/${encodeURIComponent(slug)}`);
}
