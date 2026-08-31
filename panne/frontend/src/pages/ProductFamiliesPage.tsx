import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import type { ProductFamilyRow } from "../api/types";
import { EmptyState, ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { productStatusLabel, productStatusTone } from "../language/products";
import { useCommand } from "../ops/useCommand";
import { useOrganization } from "../session/OrganizationContext";

export function ProductFamiliesPage() {
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const command = useCommand();
  const [code, setCode] = useState("");
  const [name, setName] = useState("");

  const { state, reload } = useAsyncResource<{ items: ProductFamilyRow[] }>(
    () => api.listProductFamilies(),
    [api, orgId],
    Boolean(orgId),
  );

  const items = state.kind === "ok" ? state.data.items : [];

  async function onCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (command.pending) return;
    const trimmedCode = code.trim();
    const trimmedName = name.trim();
    if (!trimmedCode || !trimmedName) return;
    try {
      await command.run(`family:${trimmedCode}:${trimmedName}`, (key) =>
        api.createProductFamily({ code: trimmedCode, display_name: trimmedName }, key),
      );
      setCode("");
      setName("");
      reload();
    } catch {
      /* erro apresentado em command.error */
    }
  }

  return (
    <div className="stage">
      <ListLive
        kind={state.kind}
        empty={state.kind === "ok" && items.length === 0}
        entityLabel={items[0]?.display_name ?? "família"}
        status={state.kind === "ok" ? `${items.length} famílias` : undefined}
      />
      <div>
        <div className="page-head">
          <div>
            <h1>Famílias de produto</h1>
          </div>
        </div>
        <p className="lede">
          Agrupamento simples para organizar o catálogo. A família não muda regra de produção nem de
          venda.
        </p>
        {hasPermission("product.family.manage") ? (
          <form className="panel" onSubmit={onCreate}>
            <h2>Nova família</h2>
            <label>
              Código (obrigatório)
              <input
                value={code}
                onChange={(event) => setCode(event.target.value)}
                required
                autoComplete="off"
                disabled={command.pending}
              />
            </label>
            <label>
              Nome (obrigatório)
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
                autoComplete="off"
                disabled={command.pending}
              />
            </label>
            {command.error ? (
              <p className="error" role="alert">
                {command.error.message || "Não foi possível guardar a família."}
              </p>
            ) : null}
            <button type="submit" className="primary" disabled={command.pending}>
              {command.pending ? "A guardar…" : "Guardar família"}
            </button>
          </form>
        ) : null}
        {state.kind === "carregando" ? <LoadingState /> : null}
        {state.kind === "erro" ? <ErrorState error={state.error} onRetry={() => reload()} /> : null}
        {state.kind === "ok" && items.length === 0 ? (
          <EmptyState>Nenhuma família cadastrada nesta organização.</EmptyState>
        ) : null}
        {items.length > 0 ? (
          <div className="table-wrap">
            <table>
              <caption>Famílias da organização</caption>
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Código</th>
                  <th>Situação</th>
                </tr>
              </thead>
              <tbody>
                {items.map((family) => (
                  <tr key={family.id}>
                    <td>{family.display_name}</td>
                    <td>{family.code}</td>
                    <td>
                      <StatusBadge
                        tone={productStatusTone(family.status)}
                        label={productStatusLabel(family.status)}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        <p>
          <Link className="ghost" to="/produtos">
            Voltar aos produtos
          </Link>
        </p>
      </div>
      <aside className="panel">
        <h2>Para que serve</h2>
        <p>
          Famílias ajudam a achar o produto e a ler relatórios por grupo. Um produto pode ficar sem
          família sem prejuízo nenhum.
        </p>
      </aside>
    </div>
  );
}
