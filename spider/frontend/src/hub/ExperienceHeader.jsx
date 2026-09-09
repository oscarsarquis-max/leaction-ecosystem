import { CAMPOABERTO_ARTICLE_URL } from "./urls.js";
import { NAV } from "./content.js";

export default function ExperienceHeader({ activeId }) {
  return (
    <header className="sx-nav">
      <div className="sx-container sx-nav-inner">
        <a className="sx-brand" href="/" data-testid="hub-brand">
          <strong>SPIDER</strong>
          <span>Plataforma Contextual</span>
        </a>
        <nav className="sx-nav-links" aria-label="Produto">
          {NAV.map((item) => (
            <a
              key={item.id}
              href={item.href}
              aria-current={activeId === item.id ? "location" : undefined}
            >
              {item.label}
            </a>
          ))}
        </nav>
        <a
          className="sx-btn sx-btn-primary"
          href={CAMPOABERTO_ARTICLE_URL}
          target="_blank"
          rel="noopener"
        >
          Experimentar
        </a>
      </div>
    </header>
  );
}
