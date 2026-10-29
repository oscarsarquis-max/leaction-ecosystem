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

export type BuilderProposal = {
  token_ok: boolean;
  flour_id: string;
  flour_name: string;
  dough_id: string;
  dough_name: string;
  ingredient_ids: string[];
  ingredient_names: string[];
  shape_id: string;
  shape_name: string;
  free_text: string;
  needs_choice: string[];
  dropped: { slug: string; reason?: string }[];
  notice: string;
  source: string;
  price_cents?: number;
  weight_grams?: number;
};

export type BuilderTipChange = { field: string; from: string; to: string };

export type BuilderTip = {
  ok: boolean;
  observation: string;
  serving: string;
  composition: {
    flour: string;
    preparation: string;
    inclusions: string[];
    shape: string;
    note: string;
  };
  suggestion: {
    label: string;
    changes: BuilderTipChange[];
    patch: {
      flour_id?: string;
      flour_name?: string;
      dough_id?: string;
      dough_name?: string;
      ingredient_ids?: string[];
      ingredient_names?: string[];
      shape_id?: string;
      shape_name?: string;
    };
  } | null;
  cta: { href: string; label: string; kind?: string } | null;
  notice: string;
};

export async function fetchBuilderProposal(token: string): Promise<BuilderProposal> {
  const query = new URLSearchParams({ token });
  return requestJson<BuilderProposal>(`/api/v1/catalog/bread-builder/proposal?${query}`);
}

export async function fetchBuilderTip(payload: {
  flour_id: string;
  dough_id: string;
  ingredient_ids: string[];
  shape_id: string;
  free_text: string;
  occasion?: string;
  context_text?: string;
}): Promise<BuilderTip> {
  return requestJson<BuilderTip>("/api/v1/gigio/builder-tip", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
