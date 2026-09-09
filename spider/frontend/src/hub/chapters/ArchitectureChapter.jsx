import { useMemo, useState } from "react";
import { ARCH_LAYERS, ARCH_STATUS, INFOGRAPHIC_ALT, INFOGRAPHIC_SRC } from "../content.js";
import { SectionEyebrow, SectionHeading, StatusIndicator } from "../primitives.jsx";

export default function ArchitectureChapter({ onExpand }) {
  const [view, setView] = useState("all");
  const layers = useMemo(() => {
    if (view === "done") return ARCH_LAYERS.filter((item) => item.status === "done");
    if (view === "future") return ARCH_LAYERS.filter((item) => item.status !== "done");
    return ARCH_LAYERS;
  }, [view]);

  return (
    <section className="sx-chapter" id="arquitetura" data-testid="hub-architecture">
      <div className="sx-container">
        <div className="sx-grid">
          <div className="sx-span-4">
            <SectionEyebrow>09 — Arquitetura</SectionEyebrow>
            <SectionHeading>Como tudo isso se organiza.</SectionHeading>
            <p className="sx-copy">
              Fontes e canais originam contexto. O Spider compreende, planeja, governa e executa.
              Sistemas fornecem as capacidades concretas.
            </p>
          </div>
          <div className="sx-span-3">
            {ARCH_STATUS.map((item) => (
              <p key={item.id}>
                <StatusIndicator tone={item.tone}>{item.label}</StatusIndicator>
                <span className="sx-copy">{item.items}</span>
              </p>
            ))}
          </div>
          <div className="sx-span-5 sx-actions sx-arch-actions">
            <button type="button" className="sx-btn sx-btn-secondary" data-testid="hub-expand-architecture" onClick={onExpand}>
              Ampliar
            </button>
            <button
              type="button"
              className={`sx-btn sx-btn-secondary${view === "done" ? " is-on" : ""}`}
              aria-pressed={view === "done"}
              onClick={() => setView("done")}
            >
              Ver o que está implementado
            </button>
            <button
              type="button"
              className={`sx-btn sx-btn-secondary${view === "future" ? " is-on" : ""}`}
              aria-pressed={view === "future"}
              onClick={() => setView("future")}
            >
              Ver visão futura
            </button>
          </div>
        </div>
        <div className="sx-arch-map" data-testid="architecture-map">
          {layers.map((item) => (
            <article key={item.id} className={`sx-arch-cell sx-status-dot-${item.status}`}>
              <StatusIndicator tone={item.status === "done" ? "done" : item.status === "prepared" ? "prepared" : "future"}>
                {item.status === "done" ? "Implementado" : item.status === "prepared" ? "Preparado" : "Futuro"}
              </StatusIndicator>
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </article>
          ))}
        </div>
        <figure className="sx-infographic" data-testid="hub-infographic">
          <img src={INFOGRAPHIC_SRC} alt={INFOGRAPHIC_ALT} />
        </figure>
      </div>
    </section>
  );
}
