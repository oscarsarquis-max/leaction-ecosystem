import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { SupplierCard } from "../api/types";
import { EmptyState, ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { useAsyncResource } from "../hooks/useAsyncResource";
import {
  activeItemsSummary,
  supplierStatusLabel,
  supplierStatusTone,
} from "../language/suppliers";
import { useCommand } from "../ops/useCommand";
import { useOrganization } from "../session/OrganizationContext";

export function SuppliersPage() {
  const { api, hasPermission, active } = useOrganization();
  const navigate = useNavigate();
  const command = useCommand();
  const orgId = active?.organization_id ?? null;
  const [code, setCode] = useState("");
  const [name, setName] = useState("");

  const { state, reload } = useAsyncResource<{ data: SupplierCard[] }>(
    () => api.listSuppliers(),
    [api, orgId],
    Boolean(orgId),
  );

  const items = state.kind === "ok" ? state.data.data : [];

  async function onCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (command.pending) return;
    const trimmedCode = code.trim();
    const trimmedName = name.trim();
    if (!trimmedCode || !trimmedName) return;
    try {
      await command.run(`supplier:${trimmedCode}:${trimmedName}`, (key) =>
        api.catalogCommand("/suppliers", {
          body: { code: trimmedCode, display_name: trimmedName },
          idempotencyKey: key,
        }),
      );
      setCode("");
      setName("");
      reload();
    } catch {
      /* erro em command.error */
    }
  }

  return (
    <div className="stage">
      <ListLive
        kind={state.kind}
        empty={state.kind === "ok" && items.length === 0}
        entityLabel={items[0]?.display_name ?? "fornecedor"}
        status={state.kind === "ok" ? `${items.length} fornecedores` : undefined}
      />
      <div>
        <h1>Fornecedores e itens</h1>
        <p className="lede">
          Cadastro de fornecedores e consulta dos itens comerciais. Os preços pertencem aos itens de
          cada fornecedor. O custeio seleciona o preço conforme a política vigente da organização.
        </p>
        <p className="meta">
          Estes valores apoiam custos operacionais; não representam valor contábil do estoque.
        </p>
        {hasPermission("supplier.manage") ? (
          <form className="panel" onSubmit={onCreate}>
            <h2>Novo fornecedor</h2>
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
                autoComplete="organization"
                disabled={command.pending}
              />
            </label>
            {command.error ? (
              <p className="error" role="alert">
                {command.error.message || "Não foi possível guardar o fornecedor."}
              </p>
            ) : null}
            <button type="submit" className="primary" disabled={command.pending}>
              {command.pending ? "A guardar…" : "Guardar fornecedor"}
            </button>
          </form>
        ) : null}
        {state.kind === "carregando" ? <LoadingState /> : null}
        {state.kind === "erro" ? <ErrorState error={state.error} /> : null}
        {state.kind === "ok" && items.length === 0 ? (
          <EmptyState>Nenhum fornecedor nesta organização.</EmptyState>
        ) : null}
        {state.kind === "ok" && items.length > 0 ? (
          <div className="table-wrap">
            <table>
              <caption>Fornecedores</caption>
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Código</th>
                  <th>Situação</th>
                  <th>Itens ativos</th>
                  <th>Ação</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <SupplierRow
                    key={item.id}
                    item={item}
                    onRowNavigate={(to) => navigate(to)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
      <aside className="panel">
        <h2>Regra</h2>
        <p>
          O valor observado pertence ao item comercial do fornecedor, não à identidade do
          ingrediente. Abrir o detalhe de um fornecedor mostra SKUs, embalagens e, com permissão, o
          histórico de preços.
        </p>
        <p className="meta">
          O registro de novos itens e preços ocorre na jornada do ingrediente ou nas compras — não
          nesta tela.
        </p>
      </aside>
    </div>
  );
}

function SupplierRow({
  item,
  onRowNavigate,
}: {
  item: SupplierCard;
  onRowNavigate: (to: string) => void;
}) {
  const detailTo = `/componentes/fornecedores/${item.id}`;
  const nameLabel = `Abrir detalhe de ${item.display_name}`;
  const codeLabel = `Abrir detalhe do código ${item.code}`;
  const detailActionLabel = `Detalhe de ${item.display_name}`;
  const count = item.active_item_count ?? 0;

  return (
    <tr
      onClick={(event) => {
        const target = event.target as HTMLElement;
        if (target.closest("a")) return;
        onRowNavigate(detailTo);
      }}
    >
      <td>
        <Link to={detailTo} aria-label={nameLabel}>
          {item.display_name}
        </Link>
      </td>
      <td>
        <Link to={detailTo} aria-label={codeLabel}>
          {item.code}
        </Link>
      </td>
      <td>
        <StatusBadge tone={supplierStatusTone(item.status)} label={supplierStatusLabel(item.status)} />
      </td>
      <td>{activeItemsSummary(count)}</td>
      <td>
        <Link to={detailTo} aria-label={detailActionLabel}>
          Detalhe
        </Link>
      </td>
    </tr>
  );
}
