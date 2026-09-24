import type { PublicIngredient } from "./types";

const COMPACT_LIMIT = 4;
const PREVIEW_COUNT = 3;

export function ingredientNames(ingredients: PublicIngredient[] | undefined): string[] {
  return (ingredients ?? []).map((item) => item.name.trim()).filter(Boolean);
}

export function formatIngredientList(names: string[]): string {
  if (names.length === 0) {
    return "";
  }
  return `${names.join(", ")}.`;
}

export function ProductIngredients({
  ingredients,
  expandable = false,
}: {
  ingredients?: PublicIngredient[];
  expandable?: boolean;
}) {
  const names = ingredientNames(ingredients);
  if (names.length === 0) {
    return null;
  }
  const useDisclosure = expandable && names.length > COMPACT_LIMIT;
  if (!useDisclosure) {
    return (
      <div className="product-ingredients">
        <p>
          <span className="product-ingredients-label">Ingredientes </span>
          {formatIngredientList(names)}
        </p>
      </div>
    );
  }
  return (
    <details className="product-ingredients product-ingredients--expandable">
      <summary>
        <span className="product-ingredients-label">Ingredientes </span>
        {`${names.slice(0, PREVIEW_COUNT).join(", ")}…`}
        <span className="product-ingredients-toggle"> Ver ingredientes</span>
      </summary>
      <p>{formatIngredientList(names)}</p>
    </details>
  );
}
