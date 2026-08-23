import { Link } from "react-router-dom";
import { StatusBadge } from "../components/Feedback";
import { useOrganization } from "../session/OrganizationContext";

export function HomePage() {
  const { hasPermission, active } = useOrganization();
  return (
    <div className="stage">
      <div>
        <h1>Início</h1>
        <p className="lede">
          A marca permanece no cabeçalho. Organização ativa: <strong>{active?.display_name}</strong>.
        </p>
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
