import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/errors";
import type { RecipeAiProposal } from "../api/types";
import { EmptyState, ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { useOrganization } from "../session/OrganizationContext";

export function RecipeAiHistoryPage() {
  const { api, active } = useOrganization();
  const [state, setState] = useState<
    | { kind: "carregando" }
    | { kind: "ok"; items: RecipeAiProposal[] }
    | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });

  useEffect(() => {
    if (!active) return;
    let alive = true;
    api
      .listRecipeAiProposals()
      .then((page) => {
        if (alive) setState({ kind: "ok", items: page.items });
      })
      .catch((error) => {
        if (alive) setState({ kind: "erro", error });
      });
    return () => {
      alive = false;
    };
  }, [api, active]);

  return (
    <div className="stage">
      <ListLive
        kind={state.kind}
        empty={state.kind === "ok" && state.items.length === 0}
        entityLabel="proposta"
        status={state.kind === "ok" ? `${state.items.length} itens` : undefined}
      />
      <div>
        <h1>Histórico de propostas</h1>
        <p className="lede">
          <span className="badge">Assistido por IA</span> Cada geração é imutável. Uma nova tentativa
          cria outra proposta.
        </p>
        {state.kind === "carregando" ? <LoadingState /> : null}
        {state.kind === "erro" ? (
          <ErrorState
            error={state.error instanceof ApiError ? state.error : new Error("Falha ao listar")}
          />
        ) : null}
        {state.kind === "ok" && state.items.length === 0 ? (
          <EmptyState>Nenhuma proposta nesta organização.</EmptyState>
        ) : null}
        {state.kind === "ok" && state.items.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>Título</th>
                <th>Situação</th>
                <th>Intenção</th>
              </tr>
            </thead>
            <tbody>
              {state.items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <Link to={`/receitas/assistente/${item.id}`}>{item.title}</Link>
                  </td>
                  <td>
                    <StatusBadge tone="atencao" label={item.status_label} />
                  </td>
                  <td>{item.intent === "adapt_recipe" ? "adaptar" : "criar"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </div>
    </div>
  );
}
