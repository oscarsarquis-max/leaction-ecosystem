import type { ProductCard, ProductRecipeItem, ProductRecipeProjection } from "../api/types";
import { productQuantityLabel, productSupplyModeLabel } from "../language/products";
import { recipeIdentityLabel, recipeVersionLabel } from "../language/recipes";

export const PRODUCT_STRUCTURE_ITEM_LIMIT = 8;

export type GraphItemKind = "ingredient" | "component";

export type ProductStructureView =
  | { kind: "purchased"; product: ProductCard }
  | { kind: "produced_gap"; product: ProductCard }
  | {
      kind: "produced_recipe";
      product: ProductCard;
      recipe: ProductRecipeProjection;
      visibleItems: ProductRecipeItem[];
      hiddenCount: number;
      missingPrep: boolean;
    };

export function graphItemKind(item: { role?: string | null }): GraphItemKind {
  const role = (item.role ?? "").trim().toLowerCase();
  if (
    role === "component" ||
    role === "intermediate" ||
    role === "subrecipe" ||
    role === "preparation" ||
    role === "prep"
  ) {
    return "component";
  }
  return "ingredient";
}

export function graphItemKindLabel(kind: GraphItemKind): "Ingrediente" | "Componente" {
  return kind === "component" ? "Componente" : "Ingrediente";
}

export function graphRecipeSituation(recipe: ProductRecipeProjection): string {
  const identity = recipeIdentityLabel(recipe.formulation_status);
  const version = recipeVersionLabel(recipe.version_status);
  if (identity === "—" && version === "—") return "Situação não informada";
  if (identity === "—") return version;
  if (version === "—") return identity;
  return `${identity} · ${version}`;
}

export function graphRecipeName(recipe: ProductRecipeProjection): string {
  const name = recipe.display_name?.trim();
  if (name) return name;
  const code = recipe.code?.trim();
  return code || "Receita técnica";
}

export function graphRecipeVersionLabel(versionNumber: number): string {
  return `Versão ${versionNumber}`;
}

export function graphItemQuantityLabel(item: ProductRecipeItem): string | null {
  if (item.quantity == null || item.quantity === "") return null;
  const label = productQuantityLabel(item.quantity, item.unit);
  return label === "—" ? null : label;
}

export function describeProductStructure(product: ProductCard): ProductStructureView {
  if (product.supply_mode === "purchased") {
    return { kind: "purchased", product };
  }
  const recipe = product.current_recipe ?? null;
  if (!recipe) {
    return { kind: "produced_gap", product };
  }
  const items = Array.isArray(recipe.items) ? recipe.items : [];
  const visibleItems = items.slice(0, PRODUCT_STRUCTURE_ITEM_LIMIT);
  const hiddenCount = Math.max(0, items.length - PRODUCT_STRUCTURE_ITEM_LIMIT);
  const missingPrep = (recipe.steps?.length ?? 0) === 0;
  return {
    kind: "produced_recipe",
    product,
    recipe,
    visibleItems,
    hiddenCount,
    missingPrep,
  };
}

export function graphProductMeta(product: ProductCard): string[] {
  const lines: string[] = [];
  if (product.code?.trim()) lines.push(product.code.trim());
  lines.push(productSupplyModeLabel(product.supply_mode));
  return lines;
}
