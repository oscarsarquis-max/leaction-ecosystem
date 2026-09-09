import { CAMPOABERTO_ARTICLE_URL } from "../urls.js";
import { SectionEyebrow, SectionHeading } from "../primitives.jsx";

export default function HeroChapter() {
  return (
    <section className="sx-chapter sx-chapter-hero" id="proposicao" data-testid="hub-hero">
      <div className="sx-container sx-grid">
        <div className="sx-span-5">
          <SectionEyebrow>01 — Proposição</SectionEyebrow>
          <p className="sx-label">Spider · Plataforma Contextual</p>
          <SectionHeading as="h1" testId="hub-headline">
            Transformamos objetivos
            <br />
            em <em>caminhos executáveis.</em>
          </SectionHeading>
          <p className="sx-lede" data-testid="hub-lead">
            O Spider conecta contexto, inteligência e sistemas para transformar necessidades de
            negócio em planos governados, capacidades reutilizáveis e execuções explicáveis.
          </p>
          <div className="sx-actions">
            <a className="sx-btn sx-btn-secondary" href="#como-funciona" data-testid="hub-cta-how">
              Ver como funciona
            </a>
            <a
              className="sx-btn sx-btn-primary"
              href={CAMPOABERTO_ARTICLE_URL}
              target="_blank"
              rel="noopener"
              data-testid="hub-cta-try"
            >
              Experimentar
            </a>
          </div>
        </div>
        <div className="sx-span-7 sx-hero-flow" aria-label="Contexto e objetivo produzem um caminho">
          <span className="sx-hero-node sx-hero-in">Contexto</span>
          <span className="sx-hero-plus">+</span>
          <span className="sx-hero-node sx-hero-in">Objetivo</span>
          <span className="sx-hero-join" aria-hidden="true" />
          <strong className="sx-hero-core">Spider</strong>
          <span className="sx-hero-out-line" aria-hidden="true" />
          <span className="sx-hero-node sx-hero-out">Caminho executável</span>
        </div>
      </div>
    </section>
  );
}
