import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { ProductCard, ProductFamilyRow, ProductPage } from "../api/types";
import { EmptyState, ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { useAsyncResource } from "../hooks/useAsyncResource";
import {
  productFamilyLabel,
  productNextActionLabel,
  productPendingLabel,
  productProductionLabel,
  productRecipeTone,
  productStatusLabel,
  productStatusTone,
  productSupplyModeLabel,
} from "../language/products";
import { productHref } from "../navigation/returnTo";
import { useOrganization } from "../session/OrganizationContext";

/** Artefato de teste assistivo — não pertence ao seed canônico. */
const DEMO_TEST_PRODUCT_CODE = "AI-P-507c72c8";

export function ProductsPage() {
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const [params, setParams] = useSearchParams();
  const statusParam = params.get("status");
  const query = useMemo(
    () => ({
      q: params.get("q") || undefined,
      status: statusParam === "all" ? undefined : statusParam || "active",
      supply_mode: params.get("supply_mode") || undefined,
      family_id: params.get("family_id") || undefined,
      limit: params.get("limit") || "20",
      offset: params.get("offset") || "0",
    }),
    [params, statusParam],
  );

  const { state } = useAsyncResource<ProductPage>(
    () => api.listProducts(query),
    [api, query, orgId],
    Boolean(orgId),
  );
  const families = useAsyncResource<{ items: ProductFamilyRow[] }>(
    () => api.listProductFamilies(),
    [api, orgId],
    Boolean(orgId),
  );

  const offset = Number(query.offset ?? 0);
  const limit = Number(query.limit ?? 20);
  const total = state.kind === "ok" ? state.data.total : 0;
  const items = (state.kind === "ok" ? state.data.items : []).filter(
    (item) => item.code !== DEMO_TEST_PRODUCT_CODE,
  );
  const familyRows = families.state.kind === "ok" ? families.state.data.items : [];
  const listSearch = params.toString();

  function applyFilters(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setParams({
      q: String(data.get("q") ?? ""),
      status: String(data.get("status") ?? "active"),
      supply_mode: String(data.get("supply_mode") ?? ""),
      family_id: String(data.get("family_id") ?? ""),
      offset: "0",
    });
  }

  return (
    <div className="stage product-doc">
      <ListLive
        kind={state.kind}
        empty={state.kind === "ok" && items.length === 0}
        entityLabel={items[0]?.display_name ?? "produto"}
        status={state.kind === "ok" ? `${total} itens` : undefined}
      />
      <div>
        <p className="product-back">
          <Link to="/fluxo">Voltar ao fluxo produtivo</Link>
        </p>
        <div className="page-head">
          <div>
            <h1>Produtos</h1>
          </div>
        </div>
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
            <input name="q" defaultValue={query.q ?? ""} placeholder="Nome ou código" />
          </label>
          <label>
            Modalidade
            <select name="supply_mode" defaultValue={query.supply_mode ?? ""}>
              <option value="">Todas</option>
              <option value="produced">Produzido na casa</option>
              <option value="purchased">Comprado pronto</option>
            </select>
          </label>
          <label>
            Família
            <select name="family_id" defaultValue={query.family_id ?? ""}>
              <option value="">Todas</option>
              {familyRows.map((family) => (
                <option key={family.id} value={family.id}>
                  {family.display_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Situação
            <select name="status" defaultValue={statusParam || "active"}>
              <option value="all">Todas</option>
              <option value="active">Ativo</option>
              <option value="inactive">Inativo</option>
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
                  <th>Produto</th>
                  <th>Código</th>
                  <th>Modalidade</th>
                  <th>Família</th>
                  <th>Situação</th>
                  <th>Produção</th>
                  <th>Pendência principal</th>
                  <th>Próxima ação</th>
                  <th>Abrir</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <ProductRow key={item.id} item={item} listSearch={listSearch} />
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
    </div>
  );
}

function ProductRow({ item, listSearch }: { item: ProductCard; listSearch: string }) {
  const detailTo = productHref(item.id, listSearch);
  return (
    <tr>
      <td>{item.display_name}</td>
      <td>{item.code}</td>
      <td>{productSupplyModeLabel(item.supply_mode)}</td>
      <td>{productFamilyLabel(item.family)}</td>
      <td>
        <StatusBadge tone={productStatusTone(item.status)} label={productStatusLabel(item.status)} />
      </td>
      <td>
        <StatusBadge tone={productRecipeTone(item)} label={productProductionLabel(item)} />
      </td>
      <td>{productPendingLabel(item)}</td>
      <td>{productNextActionLabel(item)}</td>
      <td>
        <Link to={detailTo} aria-label={`Abrir detalhe de ${item.display_name}`}>
          Abrir
        </Link>
      </td>
    </tr>
  );
}
