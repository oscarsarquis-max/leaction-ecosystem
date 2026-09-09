import { CAMPOABERTO_ARTICLE_URL } from "../urls.js";
import { SectionEyebrow, SectionHeading } from "../primitives.jsx";

export default function ContextModelChapter() {
  return (
    <section className="sx-chapter" id="modelo" data-testid="hub-context-model">
      <div className="sx-container">
        <SectionEyebrow>03 — Modelo contextual</SectionEyebrow>
        <SectionHeading>
          Contextual significa começar pelo momento e pelo pedido — não pelo produto.
        </SectionHeading>
        <div className="sx-context-funnel" aria-label="Contexto e objetivo convergem em entendimento">
          <div className="sx-funnel-top">
            <div className="sx-funnel-pole">
              <strong>Contexto</strong>
              <span>O momento</span>
            </div>
            <div className="sx-funnel-pole">
              <strong>Objetivo</strong>
              <span>A necessidade</span>
            </div>
          </div>
          <div className="sx-funnel-lines" aria-hidden="true" />
          <div className="sx-funnel-out">
            <strong>Entendimento</strong>
          </div>
        </div>
        <p className="sx-intro">
          Contexto ajuda a compreender. O objetivo continua pertencendo ao usuário.
        </p>
        <div className="sx-example-board" data-testid="hub-context-example">
          <p className="sx-label">Exemplo · CampoAberto</p>
          <div className="sx-example-grid">
            <article>
              <h3>Reportagem CampoAberto</h3>
              <p>
                Contexto detectado: <b>quebra de safra</b>
              </p>
            </article>
            <span className="sx-plus">+</span>
            <article>
              <h3>Objetivo</h3>
              <p>“Preciso manter minha produção”</p>
            </article>
            <span className="sx-down">↓</span>
            <article className="sx-span-like">
              <h3>Entendimento</h3>
              <p>Necessidade de continuidade financeira.</p>
            </article>
          </div>
          <a className="sx-btn sx-btn-secondary" href={CAMPOABERTO_ARTICLE_URL} target="_blank" rel="noopener">
            Ver experiência real
          </a>
        </div>
      </div>
    </section>
  );
}
