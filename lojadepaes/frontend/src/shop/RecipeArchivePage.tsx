import { RecipeSearch } from "./RecipeSearch";

function initialSearch(): { q: string; page: number } {
  const params = new URLSearchParams(window.location.search);
  const page = Number(params.get("page") || "1");
  return {
    q: params.get("q") || "",
    page: Number.isFinite(page) && page > 0 ? page : 1,
  };
}

export function RecipeArchivePage() {
  const start = initialSearch();
  return (
    <main className="recipe-archive-page">
      <h1>Receitas</h1>
      <p className="recipe-archive-lead">Sugestões culinárias com os pães da casa. Não é vitrine de produtos.</p>
      <RecipeSearch initialQ={start.q} initialPage={start.page} />
    </main>
  );
}
