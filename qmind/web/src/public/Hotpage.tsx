import { useEffect, useId, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { writeReturnUrl } from "@/lib/returnUrl";
import { HotpageIcon } from "./HotpageIcons";
import {
  DIFFERENTIALS,
  EVIDENCE_POINTS,
  HERO_PROMISE,
  JOURNEY_STEPS,
  OUTCOMES,
  PRINCIPLES,
  QUALITY_CONTROL_POINTS,
} from "./hotpageContent";
import "./hotpage.css";

const META_DESCRIPTION =
  "QMind — plataforma de autoavaliação assistida, preparação para auditorias, organização de evidências e evolução empresarial.";

export function Hotpage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const authenticated = auth.status === "authenticated";
  const [featureId, setFeatureId] = useState(DIFFERENTIALS[0]!.id);
  const [journeyId, setJourneyId] = useState(JOURNEY_STEPS[0]!.id);
  const feature = DIFFERENTIALS.find((d) => d.id === featureId) ?? DIFFERENTIALS[0]!;
  const journey = JOURNEY_STEPS.find((s) => s.id === journeyId) ?? JOURNEY_STEPS[0]!;
  const tabPrefix = useId();

  useEffect(() => {
    const prevTitle = document.title;
    document.title = "QMind — Quality Mind · Qualidade com método";
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

  const goGuided = () => {
    if (authenticated) {
      void navigate("/guided-tour");
      return;
    }
    goLogin("/guided-tour");
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
      <a href="#qm-conteudo" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2">
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
          <a href="#qm-metodo">Método</a>
          <a href="#qm-diferenciais">Diferenciais</a>
          <a href="#qm-evidencias">Evidências</a>
          {authenticated ? (
            <>
              <Link to="/guided-tour" className="qm-hotpage__ghost">
                Continuar apresentação guiada
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
            <h1 id="qm-hero-title">
              Prepare a organização{" "}
              <span className="qm-hotpage__quality">antes</span> que a auditoria
              comece.
            </h1>
            <p className="qm-hotpage__hero-copy">
              O QMind conduz a autoavaliação, organiza evidências e transforma cada
              etapa em aprendizado prático — reduzindo improviso, tempo de preparação
              e dependência de horas externas.
            </p>
            <div className="qm-hotpage__actions">
              <a className="qm-hotpage__primary" href="#qm-metodo">
                Conheça o percurso <HotpageIcon name="arrowDown" />
              </a>
              <a className="qm-hotpage__ghost" href="#qm-diferenciais">
                Ver os diferenciais
              </a>
              {authenticated ? (
                <>
                  <Link className="qm-hotpage__ghost" to="/assessments">
                    Abrir meu QMind
                  </Link>
                  <Link className="qm-hotpage__ghost" to="/guided-tour">
                    Continuar apresentação guiada
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
                    onClick={goGuided}
                  >
                    Iniciar apresentação guiada
                  </button>
                </>
              )}
            </div>
          </div>

          <aside className="qm-hotpage__promise" aria-label="Declaração de princípios">
            <h2>A qualidade começa por dentro.</h2>
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
            <p className="qm-hotpage__kicker">Declaração de princípios</p>
            <h2 id="qm-principios-title">A qualidade começa por dentro.</h2>
            <p>
              A auditoria formal não deveria começar pela organização de arquivos
              dispersos. O QMind prepara contexto, pessoas, evidências e prioridades
              para que o tempo especializado seja utilizado onde gera mais valor.
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
            <p className="qm-hotpage__kicker">Percurso QMind</p>
            <h2 id="qm-metodo-title">
              Compreender → Planejar → Entrevistar → Evidenciar → Analisar → Evoluir
              → Demonstrar
            </h2>
            <p>
              Sem telas concorrentes, sem jargão na frente e sem perder a origem de
              cada informação.
            </p>
          </div>
          <div
            className="qm-hotpage__flow"
            role="tablist"
            aria-label="Etapas do percurso QMind"
          >
            {JOURNEY_STEPS.map((step) => {
              const selected = step.id === journey.id;
              return (
                <button
                  key={step.id}
                  type="button"
                  role="tab"
                  className="qm-hotpage__flow-step"
                  aria-selected={selected}
                  id={`${tabPrefix}-journey-${step.id}`}
                  aria-controls={`${tabPrefix}-journey-panel`}
                  onClick={() => setJourneyId(step.id)}
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
          >
            <p>
              <strong>Definição:</strong> {journey.definition}
            </p>
            <p>
              <strong>Resultado:</strong> {journey.result}
            </p>
          </div>
        </section>

        <section
          className="qm-hotpage__section"
          id="qm-diferenciais"
          aria-labelledby="qm-diferenciais-title"
        >
          <div className="qm-hotpage__section-head">
            <p className="qm-hotpage__kicker">Diferenciação fundamental</p>
            <h2 id="qm-diferenciais-title">
              Mais que um checklist. Um sistema de preparação guiada.
            </h2>
            <p>
              Selecione um diferencial para ver definição, benefício e ponto da
              apresentação guiada.
            </p>
          </div>
          <div className="qm-hotpage__showcase">
            <div
              className="qm-hotpage__feature-list"
              role="tablist"
              aria-label="Diferenciais QMind"
            >
              {DIFFERENTIALS.map((d) => {
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
              <p>{feature.definition}</p>
              <p className="qm-hotpage__benefit">
                <strong>Ganho:</strong> {feature.benefit}
              </p>
              <p className="qm-hotpage__benefit">
                <strong>Na apresentação:</strong> {feature.tourPoint}
              </p>
              <button
                type="button"
                className="qm-hotpage__route"
                onClick={goGuided}
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
            <p className="qm-hotpage__kicker">Ganhos antes da auditoria formal</p>
            <h2 id="qm-ganhos-title">
              A organização chega mais preparada — e já começa a melhorar.
            </h2>
            <p>
              Linguagem responsável: o QMind ajuda a reduzir improviso e pode
              contribuir para melhor preparação — sem garantir certificação ou
              percentuais de economia.
            </p>
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
              A evidência certa, ligada à pergunta certa, no momento certo.
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
            <p className="qm-hotpage__kicker">Quality Control</p>
            <h2 id="qm-qc-title">
              Cada informação tem origem. Cada decisão deixa um rastro.
            </h2>
            <p>
              O quality control ocorre durante todo o percurso, não somente no
              final.
            </p>
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
          id="qm-evolucao"
          aria-labelledby="qm-evolucao-title"
        >
          <div className="qm-hotpage__section-head">
            <p className="qm-hotpage__kicker">Mapa de Evolução</p>
            <h2 id="qm-evolucao-title">
              A avaliação termina com próximos passos, não apenas com um
              diagnóstico.
            </h2>
          </div>
          <div className="qm-hotpage__callout">
            <p>
              Respostas e evidências alimentam sugestões rastreáveis, agrupadas por
              tema empresarial. A prioridade considera impacto, urgência, esforço e
              confiança. A revisão humana é obrigatória; sugestões aceitas podem
              virar ações e entrar no relatório. O sistema não cria conformidade
              automaticamente.
            </p>
          </div>
        </section>

        <footer className="qm-hotpage__final">
          <div>
            <h2>Quality Mind: pensar qualidade antes de provar qualidade.</h2>
            <p>
              Comece pela autoavaliação. Chegue à auditoria com contexto, evidências
              e prioridades claras.
            </p>
          </div>
          <div className="qm-hotpage__final-actions">
            {authenticated ? (
              <>
                <Link className="qm-hotpage__primary" to="/assessments">
                  Abrir meu QMind <HotpageIcon name="arrowRight" />
                </Link>
                <Link className="qm-hotpage__ghost" to="/guided-tour">
                  Continuar apresentação guiada
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
                  onClick={goGuided}
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
