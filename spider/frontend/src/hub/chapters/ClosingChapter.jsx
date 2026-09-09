import { CAMPOABERTO_ARTICLE_URL, CONSOLE_PATH } from "../urls.js";
import { SectionHeading } from "../primitives.jsx";

export default function ClosingChapter() {
  return (
    <section className="sx-chapter sx-close" id="proximo" data-testid="hub-closing">
      <div className="sx-container">
        <p className="sx-kicker">10 — Próximo passo</p>
        <SectionHeading>
          Comece pelo objetivo.
          <br />
          O Spider cuida do caminho.
        </SectionHeading>
        <div className="sx-actions">
          <a className="sx-btn sx-btn-primary" href={CAMPOABERTO_ARTICLE_URL} target="_blank" rel="noopener">
            Experimentar SpiderBank
          </a>
          <a className="sx-btn sx-btn-secondary" href="#arquitetura">
            Ver arquitetura
          </a>
          <a className="sx-btn sx-btn-secondary" href={CONSOLE_PATH} data-testid="open-console">
            Abrir console
          </a>
        </div>
      </div>
    </section>
  );
}
