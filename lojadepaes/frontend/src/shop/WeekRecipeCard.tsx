import { RecipeSearch } from "./RecipeSearch";
import { rememberRecipeSearch, readRecipeSearch } from "./recipeSearchMemory";
import type { WeekRecipePublic } from "./weekRecipe";

type Props = {
  recipe: WeekRecipePublic | null;
};

export function WeekRecipeCard({ recipe }: Props) {
  return (
    <article className="week-recipe" aria-labelledby={recipe ? `week-recipe-${recipe.slug}` : "recipe-search-title"}>
      {recipe ? (
        <>
          <p className="week-recipe-seal">Receita em destaque</p>
          <div className="week-recipe-body">
            {recipe.image_url ? (
              <figure className="week-recipe-figure">
                <div className="week-recipe-media">
                  <img src={recipe.image_url} alt={recipe.image_alt || recipe.title} />
                </div>
                {recipe.image_caption && recipe.image_caption !== recipe.image_alt ? (
                  <figcaption className="week-recipe-caption">{recipe.image_caption}</figcaption>
                ) : null}
              </figure>
            ) : null}
            <div className="week-recipe-copy">
              <h3 id={`week-recipe-${recipe.slug}`}>{recipe.title}</h3>
              {recipe.summary ? <p className="week-recipe-summary">{recipe.summary}</p> : null}
              {recipe.prep_time || recipe.yield_text ? (
                <p className="week-recipe-meta">
                  {recipe.prep_time ? <span>Tempo: {recipe.prep_time}</span> : null}
                  {recipe.yield_text ? <span>Rendimento: {recipe.yield_text}</span> : null}
                </p>
              ) : null}
              <a
                className="week-recipe-link"
                href={recipe.href}
                onClick={() => {
                  if (!readRecipeSearch()?.q.trim()) {
                    rememberRecipeSearch({ q: "", page: 1, from: "home" });
                  }
                }}
              >
                Ver receita
              </a>
            </div>
          </div>
        </>
      ) : null}
      <RecipeSearch compact />
    </article>
  );
}
