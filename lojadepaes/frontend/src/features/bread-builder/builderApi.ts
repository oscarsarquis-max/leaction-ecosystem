import { requestJson } from "../../services/http";

export type BuilderOption = {
  id: string;
  name: string;
  description: string;
  recipe_base_pending?: boolean;
  assistant_role?: "flour" | "inclusion";
  compatible_dough_ids?: string[];
  compatibility_pending?: boolean;
};

export type BuilderCatalog = {
  price_cents: number;
  weight_grams: number;
  currency: string;
  fulfillment: string;
  doughs: BuilderOption[];
  flours: BuilderOption[];
  ingredients: BuilderOption[];
  shapes: BuilderOption[];
};

export async function fetchBuilderCatalog(): Promise<BuilderCatalog> {
  const payload = await requestJson<BuilderCatalog>("/api/v1/catalog/bread-builder");
  return { ...payload, flours: payload.flours ?? [], ingredients: payload.ingredients ?? [] };
}
