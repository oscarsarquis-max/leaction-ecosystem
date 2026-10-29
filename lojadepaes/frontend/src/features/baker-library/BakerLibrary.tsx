import { ARTICLES, PHOTOS } from "../bread-builder/catalog";

export function BakerLibrary() {
  return (
    <section id="biblioteca" className="library">
      <div className="library-heading">
        <p className="eyebrow">BIBLIOTECA DO PADEIRO</p>
        <h2>
          Um pouco de farinha.
          <br />
          <em>Um mundo para descobrir.</em>
        </h2>
        <p>Três cadernos abertos e uma calculadora de porcentagem de padeiro. O aprofundamento com o Gigio usa consultas de IA da assinatura; artigos e contas continuam livres.</p>
        <img className="library-banner" src={PHOTOS.workBench.src} alt={PHOTOS.workBench.alt} />
        <p className="library-calc-link">
          <a href="/biblioteca/calculadora">Abrir a calculadora de porcentagem de padeiro</a>
        </p>
      </div>
      <div className="articles">
        {ARTICLES.map((item) => (
          <a key={item.slug} href={item.href}>
            <span>{item.kicker}</span>
            <h3>{item.title}</h3>
            <span className="article-bottom">
              {item.readingLabel} <b>↗</b>
            </span>
          </a>
        ))}
      </div>
    </section>
  );
}
