import { useEffect, useId, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { writeReturnUrl } from "@/lib/returnUrl";
import {
  ILLUSTRATIVE_EXAMPLE,
  ILLUSTRATIVE_EXAMPLE_BADGE,
  JOURNEY_V2_CHAPTERS,
  PRODUCT_CAPABILITIES,
  guidedTourPathForChapter,
  type JourneyChapterId,
} from "@/journeyV2";
import { HotpageIcon } from "./HotpageIcons";
import {
  EVIDENCE_POINTS,
  HERO_COPY,
  HERO_PROMISE,
  OUTCOMES,
  PRINCIPLES,
  QUALITY_CONTROL_POINTS,
} from "./hotpageContent";
import "./hotpage.css";

const META_DESCRIPTION =
  "QMind — qualidade, execução e aprendizado: avaliar, reconhecer problemas, executar ações, medir, interpretar e decidir com fatos rastreáveis.";

function cycleId<T extends string>(ids: readonly T[], current: T, delta: number): T {
  const idx = ids.indexOf(current);
  const next = (idx + delta + ids.length) % ids.length;
  return ids[next]!;
}

export function Hotpage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const authenticated = auth.status === "authenticated";
  const [featureId, setFeatureId] = useState(PRODUCT_CAPABILITIES[0]!.id);
  const [journeyId, setJourneyId] = useState<JourneyChapterId>(
    JOURNEY_V2_CHAPTERS[0]!.id,
  );
  const [exampleId, setExampleId] = useState<string>(
    ILLUSTRATIVE_EXAMPLE.steps[0]!.id,
  );
  const feature =
    PRODUCT_CAPABILITIES.find((d) => d.id === featureId) ?? PRODUCT_CAPABILITIES[0]!;
  const journey =
    JOURNEY_V2_CHAPTERS.find((s) => s.id === journeyId) ?? JOURNEY_V2_CHAPTERS[0]!;
  const example =
    ILLUSTRATIVE_EXAMPLE.steps.find((s) => s.id === exampleId) ??
    ILLUSTRATIVE_EXAMPLE.steps[0]!;
  const tabPrefix = useId();
  const journeyIds = JOURNEY_V2_CHAPTERS.map((c) => c.id);
  const exampleIds = ILLUSTRATIVE_EXAMPLE.steps.map((s) => s.id);

  useEffect(() => {
    const prevTitle = document.title;
    document.title =
      "QMind — Quality Mind · Da compreensão à decisão";
    let meta = document.querySelector('meta[name="description"]');
    const created = !meta;
    if (!meta) {
      meta = document.createElement("meta");
      meta.setAttribute("name", "description");
      document.head.appendChild(meta);
    }
    const prev = meta.getAttribute("content");
    meta.setAttribute("content", META_DESCRIPTION);
    return () => {
      document.title = prevTitle;
      if (created) meta?.remove();
      else if (prev != null) meta?.setAttribute("content", prev);
    };
  }, []);

  const goLogin = (returnPath: string) => {
    writeReturnUrl(returnPath);
    void navigate(`/login?return=${encodeURIComponent(returnPath)}`);
  };

  const goGuided = (chapter?: JourneyChapterId) => {
    const path = guidedTourPathForChapter(chapter);
    if (authenticated) {
      void navigate(path);
      return;
    }
    goLogin(path);
  };

  const goApp = () => {
    if (authenticated) {
      void navigate("/assessments");
      return;
    }
    goLogin("/assessments");
  };

  return (
    <div className="qm-hotpage" data-testid="qmind-hotpage">
      <a
        href="#qm-conteudo"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2"
      >
        Ir para o conteúdo
      </a>

      <nav className="qm-hotpage__nav" aria-label="Navegação pública">
        <Link to="/" className="qm-hotpage__brand">
          <img
            src="/qmind-logo-light.png"
            alt=""
            width={144}
            height={36}
            decoding="async"
          />
          <span>QMind</span>
        </Link>
        <div className="qm-hotpage__navlinks">
          <a href="#qm-principios">Princípios</a>
          <a href="#qm-metodo">Jornada</a>
          <a href="#qm-exemplo">Exemplo</a>
          <a href="#qm-capacidades">Capacidades</a>
          {authenticated ? (
            <>
              <Link to="/guided-tour" className="qm-hotpage__ghost">
                Continuar apresentação
              </Link>
              <Link to="/assessments" className="qm-hotpage__enter">
                Abrir meu QMind
              </Link>
            </>
          ) : (
            <button
              type="button"
              className="qm-hotpage__enter"
              onClick={() => goLogin("/assessments")}
            >
              Entrar no QMind
            </button>
          )}
        </div>
      </nav>

      <main id="qm-conteudo">
        <section className="qm-hotpage__hero" aria-labelledby="qm-hero-title">
          <div>
            <p className="qm-hotpage__kicker">Quality Mind · Qualidade com método</p>
            <h1 id="qm-hero-title">{HERO_COPY.title}</h1>
            <p className="qm-hotpage__hero-copy">{HERO_COPY.copy}</p>
            <p className="qm-hotpage__human-note">{HERO_COPY.humanDecision}</p>
            <div className="qm-hotpage__actions">
              <a className="qm-hotpage__primary" href="#qm-metodo">
                Conhecer a jornada <HotpageIcon name="arrowDown" />
              </a>
              {authenticated ? (
                <>
                  <Link className="qm-hotpage__ghost" to="/assessments">
                    Entrar no QMind
                  </Link>
                  <Link className="qm-hotpage__ghost" to="/guided-tour">
                    Continuar apresentação
                  </Link>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    className="qm-hotpage__ghost"
                    onClick={() => goLogin("/assessments")}
                  >
                    Entrar no QMind
                  </button>
                  <button
                    type="button"
                    className="qm-hotpage__ghost"
                    onClick={() => goGuided()}
                    data-testid="hotpage-start-tour"
                  >
                    Iniciar apresentação guiada
                  </button>
                </>
              )}
            </div>
          </div>

          <aside className="qm-hotpage__promise" aria-label="Declaração de princípios">
            <h2>O que o produto faz — e o que não promete.</h2>
            <ul>
              {HERO_PROMISE.map((item) => (
                <li key={item.title}>
                  <HotpageIcon name="check" />
                  <span>
                    <strong>{item.title}</strong>
                    <br />
                    {item.body}
                  </span>
                </li>
              ))}
            </ul>
          </aside>
        </section>

        <section
          className="qm-hotpage__section"
          id="qm-principios"
          aria-labelledby="qm-principios-title"
        >
          <div className="qm-hotpage__section-head">
            <p className="qm-hotpage__kicker">Princípios</p>
            <h2 id="qm-principios-title">Verdade do produto</h2>
            <p>
              Descrevemos apenas capacidades verificáveis. Exemplos públicos são
              fictícios. Dados reais só após autenticação e organização selecionada.
            </p>
          </div>
          <div className="qm-hotpage__principles">
            {PRINCIPLES.map((p) => (
              <article className="qm-hotpage__principle" key={p.title}>
                <strong>{p.title}</strong>
                <p>{p.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section
          className="qm-hotpage__section"
          id="qm-metodo"
          aria-labelledby="qm-metodo-title"
        >
          <div className="qm-hotpage__section-head">
            <p className="qm-hotpage__kicker">Jornada V2</p>
            <h2 id="qm-metodo-title">
              Do problema ao aprendizado — com fatos, execução e revisão humana
            </h2>
            <p>
              Selecione um capítulo. Teclado: setas esquerda/direita no foco da
              lista.
            </p>
          </div>
          <div
            className="qm-hotpage__flow"
            role="tablist"
            aria-label="Capítulos da Jornada V2"
            onKeyDown={(e) => {
              if (e.key === "ArrowRight") {
                e.preventDefault();
                setJourneyId((cur) => cycleId(journeyIds, cur, 1));
              } else if (e.key === "ArrowLeft") {
                e.preventDefault();
                setJourneyId((cur) => cycleId(journeyIds, cur, -1));
              }
            }}
          >
            {JOURNEY_V2_CHAPTERS.map((step) => {
              const selected = step.id === journey.id;
              return (
                <button
                  key={step.id}
                  type="button"
                  role="tab"
                  className="qm-hotpage__flow-step"
                  aria-selected={selected}
                  tabIndex={selected ? 0 : -1}
                  id={`${tabPrefix}-journey-${step.id}`}
                  aria-controls={`${tabPrefix}-journey-panel`}
                  onClick={() => setJourneyId(step.id)}
                  data-testid={`journey-tab-${step.id}`}
                >
                  <HotpageIcon name={step.icon} />
                  <span>{step.label}</span>
                </button>
              );
            })}
          </div>
          <div
            className="qm-hotpage__flow-detail"
            role="tabpanel"
            id={`${tabPrefix}-journey-panel`}
            aria-labelledby={`${tabPrefix}-journey-${journey.id}`}
            data-testid="journey-panel"
          >
            <h3>{journey.title}</h3>
            <p>
              <strong>Situação:</strong> {journey.situation}
            </p>
            <p>
              <strong>O QMind organiza ou interpreta:</strong> {journey.organizes}
            </p>
            <p>
              <strong>Evidência / fato:</strong> {journey.evidence}
            </p>
            <p>
              <strong>Ação humana:</strong> {journey.humanAction}
            </p>
            <p>
              <strong>Resultado observável:</strong> {journey.observableResult}
            </p>
          </div>
        </section>

        <section
          className="qm-hotpage__section"
          id="qm-exemplo"
          aria-labelledby="qm-exemplo-title"
        >
          <div className="qm-hotpage__section-head">
            <p className="qm-hotpage__kicker">
              <span className="qm-hotpage__badge">{ILLUSTRATIVE_EXAMPLE_BADGE}</span>
            </p>
            <h2 id="qm-exemplo-title">{ILLUSTRATIVE_EXAMPLE.title}</h2>
            <p>{ILLUSTRATIVE_EXAMPLE.subtitle}</p>
          </div>
          <div
            className="qm-hotpage__flow"
            role="tablist"
            aria-label="Passos do exemplo ilustrativo"
            data-testid="illustrative-example"
            onKeyDown={(e) => {
              if (e.key === "ArrowRight") {
                e.preventDefault();
                setExampleId((cur) => cycleId(exampleIds, cur, 1));
              } else if (e.key === "ArrowLeft") {
                e.preventDefault();
                setExampleId((cur) => cycleId(exampleIds, cur, -1));
              }
            }}
          >
            {ILLUSTRATIVE_EXAMPLE.steps.map((step) => {
              const selected = step.id === example.id;
              return (
                <button
                  key={step.id}
                  type="button"
                  role="tab"
                  className="qm-hotpage__flow-step"
                  aria-selected={selected}
                  tabIndex={selected ? 0 : -1}
                  id={`${tabPrefix}-ex-${step.id}`}
                  aria-controls={`${tabPrefix}-ex-panel`}
                  onClick={() => setExampleId(step.id)}
                >
                  <span>{step.label}</span>
                </button>
              );
            })}
          </div>
          <div
            className="qm-hotpage__flow-detail"
            role="tabpanel"
            id={`${tabPrefix}-ex-panel`}
            aria-labelledby={`${tabPrefix}-ex-${example.id}`}
          >
            <p className="qm-hotpage__badge" aria-hidden="true">
              {ILLUSTRATIVE_EXAMPLE_BADGE}
            </p>
            <h3>{example.label}</h3>
            <p>{example.detail}</p>
          </div>
        </section>

        <section
          className="qm-hotpage__section"
          id="qm-capacidades"
          aria-labelledby="qm-capacidades-title"
        >
          <div className="qm-hotpage__section-head">
            <p className="qm-hotpage__kicker">Capacidades atuais</p>
            <h2 id="qm-capacidades-title">
              O que o produto entrega hoje — com limites explícitos
            </h2>
            <p>
              Cada capacidade aponta o capítulo correspondente da apresentação
              guiada autenticada.
            </p>
          </div>
          <div className="qm-hotpage__showcase">
            <div
              className="qm-hotpage__feature-list"
              role="tablist"
              aria-label="Capacidades QMind"
            >
              {PRODUCT_CAPABILITIES.map((d) => {
                const selected = d.id === feature.id;
                return (
                  <button
                    key={d.id}
                    type="button"
                    role="tab"
                    className="qm-hotpage__feature-btn"
                    aria-selected={selected}
                    id={`${tabPrefix}-feat-${d.id}`}
                    aria-controls={`${tabPrefix}-feat-panel`}
                    onClick={() => setFeatureId(d.id)}
                  >
                    <HotpageIcon name={d.icon} />
                    <span>{d.name}</span>
                  </button>
                );
              })}
            </div>
            <article
              className="qm-hotpage__feature-detail"
              role="tabpanel"
              id={`${tabPrefix}-feat-panel`}
              aria-labelledby={`${tabPrefix}-feat-${feature.id}`}
              aria-live="polite"
            >
              <div className="qm-hotpage__feature-icon">
                <HotpageIcon name={feature.icon} />
              </div>
              <h3>{feature.name}</h3>
              <p>
                <strong>Problema:</strong> {feature.problem}
              </p>
              <p className="qm-hotpage__benefit">
                <strong>Evidência no produto:</strong> {feature.productEvidence}
              </p>
              <p className="qm-hotpage__benefit">
                <strong>Limite / decisão humana:</strong> {feature.humanLimit}
              </p>
              <p className="qm-hotpage__benefit">
                <strong>Na apresentação:</strong>{" "}
                {JOURNEY_V2_CHAPTERS.find((c) => c.id === feature.chapterId)?.title}
              </p>
              <button
                type="button"
                className="qm-hotpage__route"
                onClick={() => goGuided(feature.chapterId)}
              >
                Ver na apresentação guiada <HotpageIcon name="arrowRight" />
              </button>
            </article>
          </div>
        </section>

        <section
          className="qm-hotpage__section"
          id="qm-ganhos"
          aria-labelledby="qm-ganhos-title"
        >
          <div className="qm-hotpage__section-head">
            <p className="qm-hotpage__kicker">Resultados observáveis</p>
            <h2 id="qm-ganhos-title">
              Ganhos de clareza e rastreabilidade — sem percentuais inventados
            </h2>
          </div>
          <div className="qm-hotpage__outcomes">
            {OUTCOMES.map((o) => (
              <article className="qm-hotpage__outcome" key={o.title}>
                <HotpageIcon name={o.icon} />
                <strong>{o.title}</strong>
                <p>{o.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section
          className="qm-hotpage__section"
          id="qm-evidencias"
          aria-labelledby="qm-evidencias-title"
        >
          <div className="qm-hotpage__section-head">
            <p className="qm-hotpage__kicker">Evidências</p>
            <h2 id="qm-evidencias-title">
              Evidência contextual, ligada ao fato certo
            </h2>
          </div>
          <ul className="qm-hotpage__list-grid">
            {EVIDENCE_POINTS.map((item) => (
              <li key={item}>
                <HotpageIcon name="check" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </section>

        <section
          className="qm-hotpage__section"
          id="qm-quality-control"
          aria-labelledby="qm-qc-title"
        >
          <div className="qm-hotpage__section-head">
            <p className="qm-hotpage__kicker">Rastreabilidade</p>
            <h2 id="qm-qc-title">
              Cada informação tem origem. Cada decisão deixa rastro.
            </h2>
          </div>
          <ul className="qm-hotpage__list-grid">
            {QUALITY_CONTROL_POINTS.map((item) => (
              <li key={item}>
                <HotpageIcon name="shield" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </section>

        <section
          className="qm-hotpage__section"
          id="qm-oi-contrato"
          aria-labelledby="qm-oi-title"
        >
          <div className="qm-hotpage__section-head">
            <p className="qm-hotpage__kicker">Core ↔ QMind OI</p>
            <h2 id="qm-oi-title">Interpretação sem misturar fronteiras</h2>
          </div>
          <div className="qm-hotpage__callout">
            <p>
              Core conserva fatos e decisões → contrato HTTP versionado → OI
              interpreta sem ler o banco do Core → resultado explicável → Core
              persiste histórico, fatos de suporte e limitações. O OI não é um
              chatbot genérico nesta jornada.
            </p>
          </div>
        </section>

        <footer className="qm-hotpage__final">
          <div>
            <h2>Apresente o ciclo completo — com dados reais só no tour autenticado.</h2>
            <p>
              A página pública ilustra. A apresentação guiada demonstra fatos da
              organização autorizada, sem mutações.
            </p>
          </div>
          <div className="qm-hotpage__final-actions">
            {authenticated ? (
              <>
                <Link className="qm-hotpage__primary" to="/assessments">
                  Abrir meu QMind <HotpageIcon name="arrowRight" />
                </Link>
                <Link className="qm-hotpage__ghost" to="/guided-tour">
                  Continuar apresentação
                </Link>
              </>
            ) : (
              <>
                <button
                  type="button"
                  className="qm-hotpage__primary"
                  onClick={goApp}
                >
                  Entrar no QMind <HotpageIcon name="arrowRight" />
                </button>
                <button
                  type="button"
                  className="qm-hotpage__ghost"
                  onClick={() => goGuided()}
                >
                  Iniciar apresentação guiada
                </button>
              </>
            )}
          </div>
        </footer>
      </main>
    </div>
  );
}
