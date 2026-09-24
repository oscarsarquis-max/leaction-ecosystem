export type Money = {
  cents: number | null;
  currency: string;
};

export type PublicVariant = {
  id: string;
  display_name: string;
  presentation_type: "weight" | "pack" | string;
  net_weight_grams: number | null;
  units_per_pack: number | null;
  pack_label: string | null;
  price: Money;
};

export type PublicIngredient = {
  name: string;
};

export type PublicProduct = {
  name: string;
  slug: string;
  short_description: string;
  long_description?: string | null;
  image_url: string | null;
  image_alt: string;
  image_caption?: string;
  is_available: boolean;
  from_price: Money;
  price_is_from: boolean;
  variants: PublicVariant[];
  ingredients?: PublicIngredient[];
  allergen_note?: string;
};

export type PublicProductList = {
  items: PublicProduct[];
  page: number;
  page_size: number;
  total: number;
};

export type SelectionLine = {
  key: string;
  slug: string;
  variantId: string;
  quantity: number;
  adaptation?: AdaptationDraft | null;
};

export type AdaptationDraft = {
  text: string;
  reason: "" | "preference" | "dietary_restriction";
};

export type ResolvedLine = {
  key: string;
  slug: string;
  variantId: string;
  quantity: number;
  productName: string;
  variantName: string;
  packLabel: string | null;
  unitCents: number;
  lineCents: number;
  available: boolean;
  notice: string | null;
  adaptation?: AdaptationDraft | null;
};
