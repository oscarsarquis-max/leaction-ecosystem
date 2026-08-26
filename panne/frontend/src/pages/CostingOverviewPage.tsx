import { Link } from "react-router-dom";
import { CostingMentor } from "../components/CostingMentor";
import { useOrganization } from "../session/OrganizationContext";

export function CostingOverviewPage() {
  const { hasPermission } = useOrganization();
  return (
    <div className="stage">
      <div>
        <div className="page-head">
          <div>
            <h1>Custos e preços</h1>
            <p className="lede">
              Custo previsto, padrão e realizado são memórias versionadas. O preço sugerido não é
              publicado automaticamente. Markup não é margem bruta; margem bruta não é margem de
              contribuição.
            </p>
          </div>
        </div>
        <div className="cards">
          <article className="card">
            <h2>Políticas</h2>
            <p>Premissas, categorias e critério de preço vigente.</p>
            <Link className="primary" to="/gestao/custos/politicas">
              Abrir políticas
            </Link>
          </article>
          <article className="card">
            <h2>Custos previstos</h2>
            <p>Projeção antes da execução, com snapshots.</p>
            <Link className="primary" to="/gestao/custos/previstos">
              Ver previstos
            </Link>
          </article>
          <article className="card">
            <h2>Custos realizados</h2>
            <p>Consumo, desperdício e rendimento persistidos.</p>
            <Link className="primary" to="/gestao/custos/realizados">
              Ver realizados
            </Link>
          </article>
          {hasPermission("pricing.simulation.manage") ? (
            <article className="card">
              <h2>Simulações</h2>
              <p>Markup, margem bruta e margem de contribuição.</p>
              <Link className="primary" to="/gestao/custos/simulacoes">
                Abrir simulador
              </Link>
            </article>
          ) : null}
          {hasPermission("pricing.review") ? (
            <article className="card">
              <h2>Preços praticados</h2>
              <p>Decisão humana com vigência e canal.</p>
              <Link className="primary" to="/gestao/custos/precos">
                Abrir preços
              </Link>
            </article>
          ) : null}
        </div>
      </div>
      <CostingMentor step={0} pending={["escolher produto ou ordem"]} />
    </div>
  );
}
