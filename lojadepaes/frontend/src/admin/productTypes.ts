import type { Money } from "./types";

export type AdminProductListItem = {
  id: string;
  name: string;
  slug: string;
  editorial_status: string;
  is_available: boolean;
  updated_at: string;
  thumbnail_url: string | null;
  from_price: Money;
};

export type AdminProductList = {
  items: AdminProductListItem[];
  page: number;
  page_size: number;
  total: number;
};

export type AdminIngredient = {
  id: string;
  name: string;
  sort_order: number;
  catalog_ingredient_id: string | null;
};

export type AdminVariant = {
  id: string;
  display_name: string;
  presentation_type: string;
  net_weight_grams: number | null;
  units_per_pack: number | null;
  price: Money;
  is_active: boolean;
  sort_order: number;
};

export type AdminMedia = {
  id: string;
  content_type: string;
  width: number;
  height: number;
  url: string;
  public_url: string;
};

export type AdminProductDetail = {
  id: string;
  name: string;
  slug: string;
  short_description: string;
  long_description: string | null;
  featured_image: AdminMedia | null;
  featured_image_alt: string;
  editorial_status: string;
  is_available: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
  published_at: string | null;
  ingredients: AdminIngredient[];
  variants: AdminVariant[];
  publication_gaps: string[];
  from_price: Money;
};

export type VariantDraft = {
  key: string;
  id?: string;
  display_name: string;
  presentation_type: "weight" | "pack";
  net_weight_grams: string;
  units_per_pack: string;
  price_text: string;
  is_active: boolean;
};

export type ProductDraft = {
  name: string;
  slug: string;
  short_description: string;
  long_description: string;
  featured_image_alt: string;
  is_available: boolean;
  sort_order: string;
  ingredients: string[];
  variants: VariantDraft[];
};
