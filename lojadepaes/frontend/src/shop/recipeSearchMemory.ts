const KEY = "lojadepaes_recipe_search";

export type RecipeSearchMemory = {
  q: string;
  page: number;
  from: "home" | "archive";
};

export function rememberRecipeSearch(state: RecipeSearchMemory): void {
  sessionStorage.setItem(KEY, JSON.stringify(state));
}

export function readRecipeSearch(): RecipeSearchMemory | null {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as RecipeSearchMemory;
    if (parsed.from !== "home" && parsed.from !== "archive") {
      return null;
    }
    return {
      q: String(parsed.q || ""),
      page: Number(parsed.page) > 0 ? Number(parsed.page) : 1,
      from: parsed.from,
    };
  } catch {
    return null;
  }
}

export function recipeBackLink(): { href: string; label: string } {
  const stored = readRecipeSearch();
  if (stored?.from === "archive") {
    const params = new URLSearchParams();
    if (stored.q) {
      params.set("q", stored.q);
    }
    if (stored.page > 1) {
      params.set("page", String(stored.page));
    }
    const query = params.toString();
    return {
      href: query ? `/receitas?${query}` : "/receitas",
      label: "Voltar aos resultados",
    };
  }
  if (stored?.from === "home" && stored.q.trim()) {
    return { href: "/#paes", label: "Voltar aos resultados" };
  }
  return { href: "/#paes", label: "Voltar à vitrine" };
}
