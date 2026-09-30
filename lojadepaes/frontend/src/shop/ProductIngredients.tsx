import { useState } from "react";
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

export function descriptionRepeatsIngredientList(description: string | undefined, names: string[]): boolean {
  const listed = formatIngredientList(names).replace(/\.$/, "").trim().toLowerCase();
  if (!listed) {
    return false;
  }
  const hay = (description ?? "").toLowerCase().replace(/\s+/g, " ");
  return hay.includes(listed);
}

export function ProductIngredients({
  ingredients,
  expandable = false,
}: {
  ingredients?: PublicIngredient[];
  expandable?: boolean;
}) {
  const names = ingredientNames(ingredients);
  const [open, setOpen] = useState(false);
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
    <details
      className="product-ingredients product-ingredients--expandable"
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary>
        <span className="product-ingredients-label">Ingredientes </span>
        {open ? null : <span className="product-ingredients-preview">{`${names.slice(0, PREVIEW_COUNT).join(", ")}…`}</span>}
        <span className="product-ingredients-toggle">{open ? " Ocultar ingredientes" : " Ver ingredientes"}</span>
      </summary>
      <p>{formatIngredientList(names)}</p>
    </details>
  );
}
