import { useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import type { ProductCard, ProductPage } from "../api/types";
import { EmptyState, ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { useAsyncResource } from "../hooks/useAsyncResource";
import {
  productFamilyLabel,
  productPurposeLabel,
  productRecipeStatusLabel,
  productRecipeTone,
  productStatusLabel,
  productStatusTone,
  productSupplyModeLabel,
} from "../language/products";
import { useOrganization } from "../session/OrganizationContext";

export function ProductsPage() {
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const query = useMemo(
    () => ({
      q: params.get("q") || undefined,
      status: params.get("status") || undefined,
      purpose: params.get("purpose") || undefined,
      supply_mode: params.get("supply_mode") || undefined,
      limit: params.get("limit") || "20",
      offset: params.get("offset") || "0",
    }),
    [params],
  );

  const { state } = useAsyncResource<ProductPage>(
    () => api.listProducts(query),
    [api, query, orgId],
    Boolean(orgId),
  );

  const offset = Number(query.offset ?? 0);
  const limit = Number(query.limit ?? 20);
  const total = state.kind === "ok" ? state.data.total : 0;
  const items = state.kind === "ok" ? state.data.items : [];

  function applyFilters(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setParams({
      q: String(data.get("q") ?? ""),
      status: String(data.get("status") ?? ""),
      purpose: String(data.get("purpose") ?? ""),
      supply_mode: String(data.get("supply_mode") ?? ""),
      offset: "0",
    });
  }

  return (
    <div className="stage">
      <ListLive
        kind={state.kind}
        empty={state.kind === "ok" && items.length === 0}
        entityLabel={items[0]?.display_name ?? "produto"}
        status={state.kind === "ok" ? `${total} itens` : undefined}
      />
      <div>
        <div className="page-head">
          <div>
            <h1>Produtos</h1>
          </div>
        </div>
        <p className="lede">
          O que a casa vende, estoca ou produz. Um produto existe por si; a receita é opcional e
          entra quando a produção precisar dela.
        </p>
        <p>
          {hasPermission("product.create") ? (
            <Link className="primary" to="/produtos/novo">
              Novo produto
            </Link>
          ) : (
            "Criação oculta neste papel."
          )}{" "}
          <Link className="ghost" to="/produtos/familias">
            Famílias
          </Link>
        </p>
        <form className="filters" onSubmit={applyFilters}>
          <label>
            Pesquisa
            <input name="q" defaultValue={query.q ?? ""} />
          </label>
          <label>
            Situação
            <select name="status" defaultValue={query.status ?? ""}>
              <option value="">Todas</option>
              <option value="active">Ativo</option>
              <option value="inactive">Inativo</option>
            </select>
          </label>
          <label>
            Finalidade
            <select name="purpose" defaultValue={query.purpose ?? ""}>
              <option value="">Todas</option>
              <option value="final">Produto final</option>
              <option value="intermediate">Preparo intermediário</option>
            </select>
          </label>
          <label>
            Abastecimento
            <select name="supply_mode" defaultValue={query.supply_mode ?? ""}>
              <option value="">Todos</option>
              <option value="produced">Produzido na casa</option>
              <option value="purchased">Comprado pronto</option>
              <option value="mixed">Produzido e comprado (em preparação)</option>
              <option value="combo">Combo de produtos (em preparação)</option>
            </select>
          </label>
          <button type="submit" className="primary">
            Filtrar
          </button>
        </form>
        {state.kind === "carregando" ? <LoadingState /> : null}
        {state.kind === "erro" ? <ErrorState error={state.error} /> : null}
        {state.kind === "ok" && items.length === 0 ? (
          <EmptyState>Não há produtos neste recorte.</EmptyState>
        ) : null}
        {items.length > 0 ? (
          <div className="table-wrap">
            <table>
              <caption>Produtos da organização</caption>
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Código</th>
                  <th>Família</th>
                  <th>Finalidade</th>
                  <th>Abastecimento</th>
                  <th>Receita</th>
                  <th>Situação</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <ProductRow key={item.id} item={item} onRowNavigate={(to) => navigate(to)} />
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        {state.kind === "ok" && total > limit ? (
          <p>
            <button
              type="button"
              disabled={offset <= 0}
              onClick={() =>
                setParams({ ...Object.fromEntries(params), offset: String(Math.max(0, offset - limit)) })
              }
            >
              Anterior
            </button>{" "}
            <button
              type="button"
              disabled={offset + limit >= total}
              onClick={() => setParams({ ...Object.fromEntries(params), offset: String(offset + limit) })}
            >
              Seguinte
            </button>
          </p>
        ) : null}
      </div>
      <aside className="panel">
        <h2>Como ler esta lista</h2>
        <p>
          <StatusBadge tone="sucesso" label="Com receita vigente" /> o produto já pode virar ordem de
          produção.
        </p>
        <p>
          <StatusBadge tone="atencao" label="Sem receita vigente" /> o cadastro é válido, mas a
          produção fica bloqueada até publicar uma receita.
        </p>
        <p>
          <StatusBadge tone="neutro" label="Não se aplica" /> produto comprado pronto: chega
          acabado, sem receita própria.
        </p>
        <p className="meta">
          Modalidades marcadas como em preparação ainda não têm operação completa nesta fase.
        </p>
      </aside>
    </div>
  );
}

function ProductRow({
  item,
  onRowNavigate,
}: {
  item: ProductCard;
  onRowNavigate: (to: string) => void;
}) {
  const detailTo = `/produtos/${item.id}`;
  const nameLabel = `Abrir detalhe de ${item.display_name}`;
  const codeLabel = `Abrir detalhe do código ${item.code}`;
  const detailActionLabel = `Detalhe de ${item.display_name}`;

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
      <td>{productFamilyLabel(item.family)}</td>
      <td>{productPurposeLabel(item.purpose)}</td>
      <td>{productSupplyModeLabel(item.supply_mode)}</td>
      <td>
        <StatusBadge tone={productRecipeTone(item)} label={productRecipeStatusLabel(item)} />
      </td>
      <td>
        <StatusBadge tone={productStatusTone(item.status)} label={productStatusLabel(item.status)} />
      </td>
      <td>
        <Link to={detailTo} aria-label={detailActionLabel}>
          Detalhe
        </Link>
      </td>
    </tr>
  );
}
