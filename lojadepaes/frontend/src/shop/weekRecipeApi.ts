import { requestJson } from "../services/http";
import type { RecipeSearchPage, WeekRecipePublic } from "./weekRecipe";

export function fetchFeaturedWeekRecipe(): Promise<{ recipe: WeekRecipePublic | null }> {
  return requestJson("/api/v1/catalog/week-recipe");
}

export function fetchWeekRecipe(slug: string): Promise<WeekRecipePublic> {
  return requestJson(`/api/v1/catalog/week-recipes/${encodeURIComponent(slug)}`);
}

export function fetchRecipeSearch(q: string, page = 1, pageSize = 5): Promise<RecipeSearchPage> {
  const params = new URLSearchParams();
  if (q.trim()) {
    params.set("q", q.trim());
  }
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  return requestJson(`/api/v1/catalog/week-recipes?${params.toString()}`);
}
