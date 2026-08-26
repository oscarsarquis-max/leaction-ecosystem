import { useEffect, useState } from "react";
import type { SupplierCard } from "../api/types";
import { EmptyState, ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { useCommand } from "../ops/useCommand";
import { useOrganization } from "../session/OrganizationContext";

export function SuppliersPage() {
  const { api, hasPermission, active } = useOrganization();
  const command = useCommand();
  const [state, setState] = useState<
    { kind: "carregando" } | { kind: "ok"; items: SupplierCard[] } | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });
  const [code, setCode] = useState("");
  const [name, setName] = useState("");

  const load = () =>
    api
      .listSuppliers()
      .then((page) => setState({ kind: "ok", items: page.data }))
      .catch((error) => setState({ kind: "erro", error }));

  useEffect(() => {
    if (!active) return;
    void api
      .listSuppliers()
      .then((page) => setState({ kind: "ok", items: page.data }))
      .catch((error) => setState({ kind: "erro", error }));
  }, [api, active]);

  return (
    <div className="stage">
      <ListLive
        kind={state.kind}
        empty={state.kind === "ok" && state.items.length === 0}
        entityLabel={state.kind === "ok" && state.items[0] ? state.items[0].display_name : "fornecedor"}
        status={state.kind === "ok" ? `${state.items.length} itens` : undefined}
      />
      <div>
        <h1>Fornecedores e itens</h1>
        <p className="lede">
          Histórico de compra é append-only. Não há custo de receita, markup nem valor de venda.
        </p>
        {hasPermission("supplier.manage") ? (
          <form
            className="panel"
            onSubmit={(event) => {
              event.preventDefault();
              void command
                .run("supplier", (key) =>
                  api.catalogCommand("/suppliers", {
                    body: { code, display_name: name },
                    idempotencyKey: key,
                  }),
                )
                .then(() => {
                  setCode("");
                  setName("");
                  return load();
                });
            }}
          >
            <h2>Novo fornecedor</h2>
            <label>
              Código
              <input value={code} onChange={(event) => setCode(event.target.value)} />
            </label>
            <label>
              Nome
              <input value={name} onChange={(event) => setName(event.target.value)} />
            </label>
            <button type="submit" className="primary">
              Guardar fornecedor
            </button>
          </form>
        ) : null}
        {state.kind === "carregando" ? <LoadingState /> : null}
        {state.kind === "erro" ? <ErrorState error={state.error} /> : null}
        {state.kind === "ok" && state.items.length === 0 ? (
          <EmptyState>Nenhum fornecedor nesta organização.</EmptyState>
        ) : null}
        {state.kind === "ok" && state.items.length > 0 ? (
          <div className="table-wrap">
            <table>
              <caption>Fornecedores</caption>
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Código</th>
                  <th>Situação</th>
                </tr>
              </thead>
              <tbody>
                {state.items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.display_name}</td>
                    <td>{item.code}</td>
                    <td>
                      <StatusBadge
                        tone={item.status === "active" ? "sucesso" : "neutro"}
                        label={item.status === "active" ? "ativo" : "inativo"}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
      <aside className="panel">
        <h2>Regra</h2>
        <p>O valor observado pertence ao item, não à identidade do ingrediente.</p>
      </aside>
    </div>
  );
}
