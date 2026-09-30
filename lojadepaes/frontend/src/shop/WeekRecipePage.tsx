import { useEffect, useState } from "react";
import { ApiError } from "../services/http";
import { recipeBackLink } from "./recipeSearchMemory";
import { fetchWeekRecipe } from "./weekRecipeApi";
import type { WeekRecipePublic } from "./weekRecipe";

type Props = { slug: string };

export function WeekRecipePage({ slug }: Props) {
  const [recipe, setRecipe] = useState<WeekRecipePublic | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setRecipe(null);
    setError(null);
    fetchWeekRecipe(slug)
      .then((data) => {
        if (!cancelled) {
          setRecipe(data);
        }
      })
      .catch((reason: unknown) => {
        if (cancelled) {
          return;
        }
        if (reason instanceof ApiError && reason.status === 404) {
          setError("Esta receita não está disponível.");
          return;
        }
        setError("Não foi possível abrir a receita agora.");
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (error) {
    return (
      <main className="week-recipe-page">
        <p role="alert">{error}</p>
        <a className="text-button" href={recipeBackLink().href}>
          {recipeBackLink().label}
        </a>
      </main>
    );
  }
  if (!recipe) {
    return (
      <main className="week-recipe-page">
        <p>Carregando a receita…</p>
      </main>
    );
  }

  return (
    <main className="week-recipe-page">
      <p className="week-recipe-seal">Receita em destaque</p>
      <h1>{recipe.title}</h1>
      {recipe.image_url ? (
        <figure className="week-recipe-figure">
          <div className="week-recipe-hero">
            <img src={recipe.image_url} alt={recipe.image_alt || recipe.title} />
          </div>
          {recipe.image_caption && recipe.image_caption !== recipe.image_alt ? (
            <figcaption className="week-recipe-caption">{recipe.image_caption}</figcaption>
          ) : null}
        </figure>
      ) : null}
      <p className="week-recipe-summary">{recipe.summary}</p>
      {recipe.prep_time || recipe.yield_text ? (
        <p className="week-recipe-meta">
          {recipe.prep_time ? <span>Tempo: {recipe.prep_time}</span> : null}
          {recipe.yield_text ? <span>Rendimento: {recipe.yield_text}</span> : null}
        </p>
      ) : null}
      {recipe.breads.length > 0 ? (
        <section>
          <h2>Pães desta receita</h2>
          <ul className="week-recipe-breads">
            {recipe.breads.map((bread) => (
              <li key={`${bread.name}-${bread.slug ?? "off"}`}>
                {bread.href ? <a href={bread.href}>{bread.name}</a> : bread.name}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <section>
        <h2>Ingredientes</h2>
        <ul>
          {recipe.ingredients.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
      <section>
        <h2>Modo de preparo</h2>
        <div className="week-recipe-method">
          {(recipe.method_text || recipe.steps.join("\n\n")).trim() || "Preparo ainda não informado."}
        </div>
      </section>
      <p className="week-recipe-note">Sugestão de uso culinário dos pães da casa. Não substitui a ficha técnica do pão.</p>
      <a className="text-button" href={recipeBackLink().href}>
        {recipeBackLink().label}
      </a>
    </main>
  );
}
