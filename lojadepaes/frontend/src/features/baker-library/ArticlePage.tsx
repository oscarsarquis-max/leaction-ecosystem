import { useEffect, useState } from "react";
import { ApiError } from "../../services/http";
import { ArticleBody } from "./ArticleBody";
import { DeepenPanel } from "./DeepenPanel";
import { fetchLibraryArticle, type LibraryArticle } from "./libraryApi";

type Props = { slug: string };

export function ArticlePage({ slug }: Props) {
  const [article, setArticle] = useState<LibraryArticle | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setArticle(null);
    setError(null);
    fetchLibraryArticle(slug)
      .then((data) => {
        if (!cancelled) setArticle(data);
      })
      .catch((reason: unknown) => {
        if (cancelled) return;
        if (reason instanceof ApiError && reason.status === 404) {
          setError("Este caderno não está na Biblioteca.");
          return;
        }
        setError("Não foi possível abrir o artigo agora.");
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (error) {
    return (
      <main className="library-page">
        <p role="alert">{error}</p>
        <a className="text-button" href="/#biblioteca">
          Voltar à Biblioteca
        </a>
      </main>
    );
  }
  if (!article) {
    return (
      <main className="library-page">
        <p>Abrindo o caderno…</p>
      </main>
    );
  }

  return (
    <main className="library-page">
      <p className="eyebrow">{article.kicker}</p>
      <h1>{article.title}</h1>
      <p className="library-summary">{article.summary}</p>
      <p className="library-meta">{article.reading_label}</p>
      {article.photo?.src ? (
        <img className="library-hero" src={article.photo.src} alt={article.photo.alt} />
      ) : null}
      {article.body_markdown ? <ArticleBody text={article.body_markdown} /> : null}
      {article.calculator_href && slug !== "a-mesa" ? (
        <p>
          <a className="primary library-inline-cta" href={article.calculator_href}>
            Abrir a calculadora
          </a>
        </p>
      ) : null}
      {article.sources?.length ? (
        <section className="library-sources">
          <h2>Fontes</h2>
          <ul>
            {article.sources.map((source) => (
              <li key={source.label}>
                <strong>{source.label}.</strong> {source.detail}{" "}
                {source.href ? (
                  <a href={source.href} target="_blank" rel="noopener noreferrer">
                    Abrir fonte
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <DeepenPanel
        articleId={article.slug}
        articleVersion={article.version}
        returnTo={article.href}
      />
    </main>
  );
}
