import { CONSOLE_PATH } from "./urls.js";

export default function ExperienceFooter() {
  return (
    <footer className="sx-footer">
      <div className="sx-container sx-footer-grid">
        <p>
          <strong>SPIDER</strong>
          Plataforma Contextual
        </p>
        <nav>
          <a href="#proposicao">Produto</a>
          <a href="#experiencias">Experiências</a>
          <a href="#arquitetura">Arquitetura</a>
          <a href={CONSOLE_PATH}>Console técnico</a>
        </nav>
      </div>
      <div className="sx-container">
        <p className="sx-footnote">
          Ambiente de demonstração. Spider é a plataforma; SpiderBank é o satélite de domínio.
        </p>
      </div>
    </footer>
  );
}
