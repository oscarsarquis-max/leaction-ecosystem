import { Link } from "react-router-dom";
import { useOrganization } from "../session/OrganizationContext";

export function RecipeAiHubPage() {
  const { hasPermission } = useOrganization();
  return (
    <div className="stage">
      <div>
        <h1>Assistente de receitas</h1>
        <p className="lede">
          <span className="badge">Assistido por IA</span> Fluxo guiado para criar ou adaptar uma
          receita. A IA não publica, não aprova, não cria ingrediente e não declara conformidade.
        </p>
        <div className="cards">
          {hasPermission("recipe.ai.propose") ? (
            <>
              <article className="card">
                <h2>Criar com assistência</h2>
                <p>Objetivo, restrições e fontes antes de qualquer geração.</p>
                <Link className="primary" to="/receitas/assistente/criar">
                  Criar com assistência
                </Link>
              </article>
              <article className="card">
                <h2>Adaptar receita</h2>
                <p>Congela a versão-base e gera uma nova proposta em rascunho.</p>
                <Link className="primary" to="/receitas/assistente/adaptar">
                  Adaptar receita
                </Link>
              </article>
            </>
          ) : (
            <p>Este papel não gera propostas.</p>
          )}
          <article className="card">
            <h2>Histórico de propostas</h2>
            <p>Consulta, grounding, comparação e revisão humana.</p>
            <Link to="/receitas/assistente/historico">Abrir histórico</Link>
          </article>
        </div>
      </div>
    </div>
  );
}
