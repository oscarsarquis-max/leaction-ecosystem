import { Link } from "react-router-dom";
import { StatusBadge } from "../components/Feedback";
import { useOrganization } from "../session/OrganizationContext";

export function HomePage() {
  const { hasPermission, active } = useOrganization();
  return (
    <div className="stage">
      <div>
        <div className="page-head">
          <div>
            <h1>Início</h1>
            <p className="lede">
              A marca permanece no cabeçalho. Organização ativa: <strong>{active?.display_name}</strong>.
            </p>
          </div>
        </div>
        <div className="cards">
          {hasPermission("production.board.read") ? (
            <article className="card">
              <h2>Produção</h2>
              <p>Quadro do turno e execução.</p>
              <Link className="primary" to="/producao">
                Abrir quadro
              </Link>
            </article>
          ) : null}
          {hasPermission("ingredient.read") ? (
            <article className="card">
              <h2>Componentes</h2>
              <p>Ingredientes e bases — não “Cadastros”.</p>
              <Link className="primary" to="/componentes/ingredientes">
                Abrir ingredientes
              </Link>
            </article>
          ) : null}
          {hasPermission("recipe.read") ? (
            <article className="card">
              <h2>Receitas</h2>
              <p>Fichas técnicas derivadas da versão da receita.</p>
              <Link className="primary" to="/receitas">
                Abrir receitas
              </Link>
            </article>
          ) : null}
          {hasPermission("labeling.read") ? (
            <article className="card">
              <h2>Conformidade</h2>
              <p>Dossiês e candidatos de rotulagem para revisão humana.</p>
              <Link className="primary" to="/conformidade">
                Abrir conformidade
              </Link>
            </article>
          ) : null}
          {hasPermission("reporting.production.read") || hasPermission("reporting.dashboard.read") ? (
            <article className="card">
              <h2>Relatórios e painéis</h2>
              <p>Indicadores com cobertura. Ausência não é zero. Sem faturamento inventado.</p>
              <Link className="primary" to="/gestao/relatorios">
                Abrir relatórios
              </Link>
            </article>
          ) : null}
          {hasPermission("inventory.read") ? (
            <article className="card">
              <h2>Estoque</h2>
              <p>Posição, lotes, reservas e movimentações. Sem valor contábil.</p>
              <Link className="primary" to="/componentes/estoque">
                Abrir estoque
              </Link>
            </article>
          ) : null}
          {hasPermission("procurement.read") ? (
            <article className="card">
              <h2>Compras</h2>
              <p>Necessidades, requisições e pedidos internos. Sem envio automático.</p>
              <Link className="primary" to="/gestao/compras/necessidades">
                Abrir compras
              </Link>
            </article>
          ) : null}
          {hasPermission("costing.read") ? (
            <article className="card">
              <h2>Custos e preços</h2>
              <p>Custeio versionado e formação de preços sob Gestão. Sem publicação automática.</p>
              <Link className="primary" to="/gestao/custos">
                Abrir custos e preços
              </Link>
            </article>
          ) : null}
        </div>
      </div>
      <aside className="panel">
        <h2>Neste turno</h2>
        <p>
          <StatusBadge tone="info" label="produção disponível" />
        </p>
      </aside>
    </div>
  );
}
