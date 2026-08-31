import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import logoCompleto from "../../images/aprovados/horizontal-claro.png";
import { useAuth } from "../auth/AuthContext";
import { config } from "../config";
import { formatGuideCount, integrationStateLabel } from "../demo/guideFallback";
import type { DemoGuidePayload } from "../demo/guideTypes";
import { loadDemoGuide } from "../demo/loadGuide";

const COUNT_LABELS: Array<{ key: keyof DemoGuidePayload["counts"]["totals"]; label: string }> = [
  { key: "produtos", label: "Produtos" },
  { key: "ingredientes", label: "Ingredientes" },
  { key: "receitas", label: "Receitas" },
  { key: "planos", label: "Planos" },
  { key: "ordens", label: "Ordens" },
  { key: "fornecedores", label: "Fornecedores" },
  { key: "lotes", label: "Lotes" },
  { key: "saldos", label: "Posições / saldos" },
  { key: "movimentos", label: "Movimentos" },
  { key: "entradas_fiscais", label: "Entradas fiscais" },
  { key: "perfis_disponiveis", label: "Perfis disponíveis" },
];

const SECTION_KEYS = [
  "what",
  "scenario",
  "counts",
  "profiles",
  "roadmap",
  "actions",
  "integrations",
  "limits",
  "version",
] as const;

export function DemoGuidePage() {
  const { session } = useAuth();
  const signedIn = Boolean(session);
  const [guide, setGuide] = useState<DemoGuidePayload | null>(null);
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    what: true,
    scenario: true,
    counts: true,
    profiles: false,
    roadmap: true,
    actions: false,
    integrations: false,
    limits: true,
    version: false,
  });

  useEffect(() => {
    void loadDemoGuide().then(setGuide);
  }, []);

  if (!config.demoMode) {
    return (
      <main className="demo-guide">
        <p role="status">Este guia existe apenas no ambiente de demonstração.</p>
        <p>
          <Link to="/entrar">Voltar ao acesso</Link>
        </p>
      </main>
    );
  }

  if (!guide) {
    return (
      <main className="demo-guide">
        <p className="meta">Carregando o guia da demonstração…</p>
      </main>
    );
  }

  function toggle(id: string) {
    setOpenSections((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  function handlePrint() {
    setOpenSections(Object.fromEntries(SECTION_KEYS.map((key) => [key, true])));
    window.setTimeout(() => window.print(), 50);
  }

  return (
    <main className="demo-guide">
      <header className="demo-guide__hero no-print">
        <img src={logoCompleto} alt="Panne" className="demo-guide__brand" />
        <div>
          <p className="demo-banner">Ambiente de demonstração</p>
          <h1>{guide.title}</h1>
          <p>
            Roteiro seguro para homologadores. O login continua no centro de{" "}
            <Link to="/entrar">/entrar</Link>
            {signedIn ? (
              <>
                {" "}
                · <Link to="/fluxo">Ir ao fluxo</Link>
              </>
            ) : null}
            .
          </p>
          <p className="meta">
            Fonte: {guide.source === "live" ? "atualizada pela API" : "fallback versionado"}
            {guide.generated_at ? ` · gerado em ${guide.generated_at}` : ""}
          </p>
          <p>
            <button type="button" className="ghost" onClick={handlePrint}>
              Versão para impressão
            </button>
          </p>
        </div>
      </header>

      <header className="demo-guide__print-only print-only">
        <img src={logoCompleto} alt="Panne" />
        <h1>{guide.title}</h1>
        <p>
          {guide.version.label} · referência {guide.scenario.anchor_date_label}
        </p>
      </header>

      <nav className="demo-guide__toc no-print" aria-label="Índice do guia">
        {(
          [
            ["what", "O que é"],
            ["scenario", "Cenário"],
            ["counts", "Dados"],
            ["profiles", "Perfis"],
            ["roadmap", "Roteiro"],
            ["actions", "Ações"],
            ["integrations", "Integrações"],
            ["limits", "Limitações"],
            ["version", "Versão"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className="ghost"
            onClick={() => {
              setOpenSections((prev) => ({ ...prev, [id]: true }));
              document.getElementById(`demo-guide-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
          >
            {label}
          </button>
        ))}
      </nav>

      <section id="demo-guide-what" className="demo-guide__section">
        <h2>
          <button type="button" className="demo-guide__toggle" onClick={() => toggle("what")}>
            O que é esta demonstração
          </button>
        </h2>
        {openSections.what ? (
          <div>
            <p>{guide.what_is.purpose}</p>
            <p>{guide.what_is.flow}</p>
            <p>{guide.what_is.data_nature}</p>
            <p>{guide.what_is.shared}</p>
            <p>{guide.what_is.not_production}</p>
          </div>
        ) : null}
      </section>

      <section id="demo-guide-scenario" className="demo-guide__section">
        <h2>
          <button type="button" className="demo-guide__toggle" onClick={() => toggle("scenario")}>
            Cenário demonstrativo
          </button>
        </h2>
        {openSections.scenario ? (
          <ul className="list">
            <li>Data de referência: {guide.scenario.anchor_date_label}</li>
            <li>Organização principal: {guide.scenario.primary_organization}</li>
            <li>Organização de isolamento: {guide.scenario.isolation_organization}</li>
            <li>{guide.scenario.establishment_hint}</li>
            <li>{guide.scenario.shift_hint}</li>
            <li>Áreas com dados: {guide.scenario.areas_with_data.join("; ")}</li>
          </ul>
        ) : null}
      </section>

      <section id="demo-guide-counts" className="demo-guide__section">
        <h2>
          <button type="button" className="demo-guide__toggle" onClick={() => toggle("counts")}>
            Dados disponíveis
          </button>
        </h2>
        {openSections.counts ? (
          <div>
            <p className="meta">
              Totais do ambiente
              {guide.counts.updated_at ? ` · atualizado ${guide.counts.updated_at}` : ""}
              {guide.counts.note ? ` · ${guide.counts.note}` : ""}
            </p>
            <ul className="demo-guide__counts">
              {COUNT_LABELS.map((row) => (
                <li key={row.key}>
                  <span>{row.label}</span>
                  <strong>{formatGuideCount(guide.counts.totals[row.key])}</strong>
                </li>
              ))}
            </ul>
            {guide.counts.totals.produtos_ativos != null || guide.counts.totals.produtos_inativos != null ? (
              <p className="meta">
                Produtos ativos: {formatGuideCount(guide.counts.totals.produtos_ativos)} · inativos:{" "}
                {formatGuideCount(guide.counts.totals.produtos_inativos)}
              </p>
            ) : null}
            {guide.counts.organizations.map((org) => (
              <div key={org.slug} className="demo-guide__org">
                <h3>
                  {org.display_name}
                  <span className="meta"> · {org.role === "principal" ? "principal" : "isolamento"}</span>
                </h3>
                <ul className="demo-guide__counts compact">
                  {COUNT_LABELS.map((row) => (
                    <li key={`${org.slug}-${row.key}`}>
                      <span>{row.label}</span>
                      <strong>{formatGuideCount(org.counts[row.key])}</strong>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        ) : null}
      </section>

      <section id="demo-guide-profiles" className="demo-guide__section">
        <h2>
          <button type="button" className="demo-guide__toggle" onClick={() => toggle("profiles")}>
            Perfis
          </button>
        </h2>
        {openSections.profiles ? (
          <div className="demo-guide__profiles">
            {guide.profiles.map((profile) => (
              <article key={profile.id}>
                <h3>{profile.label}</h3>
                <p>{profile.purpose}</p>
                <p className="meta">Áreas: {profile.areas}</p>
                <p className="meta">Ações: {profile.actions}</p>
                <p className="meta">Limites: {profile.limits}</p>
              </article>
            ))}
          </div>
        ) : null}
      </section>

      <section id="demo-guide-roadmap" className="demo-guide__section">
        <h2>
          <button type="button" className="demo-guide__toggle" onClick={() => toggle("roadmap")}>
            Roteiro recomendado
          </button>
        </h2>
        {openSections.roadmap ? (
          <>
            {!signedIn ? (
              <p className="meta">
                Antes do login os passos aparecem sem atalho de sessão. Entre para abrir as rotas reais.
              </p>
            ) : null}
            <ol className="demo-guide__roadmap">
              {guide.roadmap.map((step) => {
                const canLink = !step.requires_session || signedIn;
                return (
                  <li key={step.step}>
                    {canLink ? (
                      <Link to={step.path}>
                        {step.step}. {step.title}
                      </Link>
                    ) : (
                      <>
                        <span>
                          {step.step}. {step.title}
                        </span>
                        <span className="meta"> — disponível após entrar</span>
                      </>
                    )}
                  </li>
                );
              })}
            </ol>
          </>
        ) : null}
      </section>

      <section id="demo-guide-actions" className="demo-guide__section">
        <h2>
          <button type="button" className="demo-guide__toggle" onClick={() => toggle("actions")}>
            Ações seguras e alterações
          </button>
        </h2>
        {openSections.actions ? (
          <div className="demo-guide__actions">
            <div>
              <h3>Pode consultar livremente</h3>
              <ul className="list">
                {guide.safe_actions.consult.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3>Altera os dados compartilhados da demo</h3>
              <ul className="list">
                {guide.safe_actions.mutates_shared.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <p role="note">{guide.safe_actions.shared_notice}</p>
            </div>
          </div>
        ) : null}
      </section>

      <section id="demo-guide-integrations" className="demo-guide__section">
        <h2>
          <button type="button" className="demo-guide__toggle" onClick={() => toggle("integrations")}>
            Integrações e simulações
          </button>
        </h2>
        {openSections.integrations ? (
          <div className="demo-guide__table-wrap">
            <table className="demo-guide__table">
              <thead>
                <tr>
                  <th scope="col">Integração</th>
                  <th scope="col">Estado</th>
                  <th scope="col">Detalhe</th>
                </tr>
              </thead>
              <tbody>
                {guide.integrations.map((row) => (
                  <tr key={row.name}>
                    <td>{row.name}</td>
                    <td>{integrationStateLabel(row.state)}</td>
                    <td>{row.detail || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section id="demo-guide-limits" className="demo-guide__section">
        <h2>
          <button type="button" className="demo-guide__toggle" onClick={() => toggle("limits")}>
            Limitações conhecidas
          </button>
        </h2>
        {openSections.limits ? (
          <ul className="list">
            {guide.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : null}
      </section>

      <section id="demo-guide-version" className="demo-guide__section">
        <h2>
          <button type="button" className="demo-guide__toggle" onClick={() => toggle("version")}>
            Versão e estado
          </button>
        </h2>
        {openSections.version ? (
          <ul className="list">
            <li>{guide.version.label}</li>
            <li>Ambiente: {guide.version.environment}</li>
            <li>Data âncora: {guide.version.anchor_date_label || guide.scenario.anchor_date_label}</li>
            {guide.version.migration_head_human ? <li>{guide.version.migration_head_human}</li> : null}
            {guide.version.api_version ? (
              <li className="meta">Detalhe técnico recolhido: API {guide.version.api_version}</li>
            ) : null}
            <li>API e serviços: use o indicador de saúde da demonstração; falhas não bloqueiam este guia.</li>
          </ul>
        ) : null}
      </section>
    </main>
  );
}
