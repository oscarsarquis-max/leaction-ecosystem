import { useState } from "react";
import { CAMPOABERTO_PREVIEW, EXPERIENCE_WALK, SPIDERBANK_PREVIEW } from "../content.js";
import { CAMPOABERTO_ARTICLE_URL, SPIDERBANK_PATH } from "../urls.js";
import { ExpandableDetail, SectionEyebrow, SectionHeading } from "../primitives.jsx";

export default function LiveExperienceChapter() {
  const [walk, setWalk] = useState(false);
  const [stepId, setStepId] = useState(EXPERIENCE_WALK[0].id);
  const step = EXPERIENCE_WALK.find((item) => item.id === stepId) ?? EXPERIENCE_WALK[0];

  return (
    <section className="sx-chapter" id="experiencias" data-testid="hub-experiences">
      <div className="sx-container">
        <SectionEyebrow>07 — Experiência real</SectionEyebrow>
        <SectionHeading>Experiência — Banco Contextual</SectionHeading>
        <div className="sx-story-split">
          <figure>
            <img src={CAMPOABERTO_PREVIEW} alt="Reportagem CampoAberto com publicidade SpiderBank" />
            <figcaption>CampoAberto · reportagem externa</figcaption>
          </figure>
          <figure>
            <img src={SPIDERBANK_PREVIEW} alt="Primeira dobra do SpiderBank, Banco Contextual" />
            <figcaption>SpiderBank · Banco Contextual</figcaption>
          </figure>
        </div>
        <p className="sx-story-link" aria-hidden="true">
          LINK /go → contexto
        </p>
        <p className="sx-intro">
          O parceiro publica um link. O contexto é criado depois do clique.
        </p>
        <div className="sx-actions">
          <a
            className="sx-btn sx-btn-primary"
            href={CAMPOABERTO_ARTICLE_URL}
            target="_blank"
            rel="noopener"
            data-testid="open-partner"
          >
            Experimentar essa jornada
          </a>
          <a className="sx-btn sx-btn-secondary" href={SPIDERBANK_PATH} data-testid="open-spiderbank">
            Abrir SpiderBank
          </a>
        </div>
        <ExpandableDetail
          open={walk}
          onToggle={() => setWalk((value) => !value)}
          label="Ver como funciona"
          testId="experience-walkthrough"
        >
          <div className="sx-walk" data-testid="experience-walk-panel">
            {EXPERIENCE_WALK.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`sx-chip-btn${stepId === item.id ? " is-on" : ""}`}
                aria-selected={stepId === item.id}
                onClick={() => setStepId(item.id)}
              >
                {item.label}
              </button>
            ))}
            <p className="sx-copy">{step.body}</p>
          </div>
        </ExpandableDetail>
      </div>
    </section>
  );
}
