import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { SupplierDetail, SupplierItemCard, SupplierPriceRow } from "../api/types";
import { EmptyState, ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { formatDateTime } from "../format";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { formatMoneyAmount, formatPackageQuantity } from "../language/ingredients";
import {
  priceSourceLabel,
  supplierItemStatusLabel,
  supplierStatusLabel,
  supplierStatusTone,
} from "../language/suppliers";
import { useOrganization } from "../session/OrganizationContext";

function packageLabel(item: SupplierItemCard): string {
  if (!item.unit) {
    return item.package_quantity ? `${item.package_quantity} · Unidade não informada` : "Unidade não informada";
  }
  return formatPackageQuantity(item.package_quantity, item.unit);
}

function ingredientLabel(item: SupplierItemCard): string {
  const name = item.ingredient?.display_name?.trim();
  return name || "Ingrediente indisponível";
}

export function SupplierDetailPage() {
  const { supplierId = "" } = useParams();
  const { api, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const [historyItemId, setHistoryItemId] = useState<string | null>(null);

  useEffect(() => {
    setHistoryItemId(null);
  }, [orgId, supplierId]);

  const { state } = useAsyncResource<{ data: SupplierDetail }>(
    () => api.getSupplier(supplierId),
    [api, orgId, supplierId],
    Boolean(orgId && supplierId),
  );

  const { state: historyState } = useAsyncResource<{
    data: SupplierPriceRow[];
    price_access: boolean;
  }>(
    () => api.listItemPrices(historyItemId as string),
    [api, orgId, historyItemId],
    Boolean(orgId && historyItemId),
  );

  if (state.kind === "carregando") {
    return (
      <div className="stage">
        <LoadingState />
      </div>
    );
  }
  if (state.kind === "erro") {
    return (
      <div className="stage">
        <p>
          <Link to="/componentes/fornecedores">← Fornecedores</Link>
        </p>
        <ErrorState error={state.error} />
      </div>
    );
  }

  const supplier = state.data.data;
  const items = supplier.items ?? [];
  const priceAccess = supplier.price_access !== false;

  return (
    <div className="stage">
      <div>
        <p>
          <Link to="/componentes/fornecedores">← Fornecedores</Link>
        </p>
        <h1>{supplier.display_name}</h1>
        <p className="lede">
          Código {supplier.code} ·{" "}
          <StatusBadge
            tone={supplierStatusTone(supplier.status)}
            label={supplierStatusLabel(supplier.status)}
          />
        </p>
        <p className="meta">
          Os preços pertencem aos itens de cada fornecedor. O custeio seleciona o preço conforme a
          política vigente da organização. Estes valores apoiam custos operacionais; não representam
          valor contábil do estoque.
        </p>
        <p className="meta">
          Consulta nesta tela. O registro de novos itens e preços ocorre na jornada do ingrediente ou
          nas compras.
        </p>

        {items.length === 0 ? (
          <EmptyState>Nenhum item comercial cadastrado</EmptyState>
        ) : (
          <div className="table-wrap">
            <table>
              <caption>Itens comerciais</caption>
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Ingrediente</th>
                  <th>Embalagem</th>
                  <th>Situação</th>
                  {priceAccess ? <th>Último preço</th> : null}
                  {priceAccess ? <th>Observado em</th> : null}
                  {priceAccess ? <th>Histórico</th> : null}
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const purchase = priceAccess ? item.latest_purchase : null;
                  return (
                    <tr key={item.id}>
                      <td>{item.supplier_sku}</td>
                      <td>
                        {item.ingredient ? (
                          <Link to={`/componentes/ingredientes/${item.ingredient.id}`}>
                            {ingredientLabel(item)}
                          </Link>
                        ) : (
                          ingredientLabel(item)
                        )}
                      </td>
                      <td>{packageLabel(item)}</td>
                      <td>
                        <StatusBadge
                          tone={supplierStatusTone(item.status)}
                          label={supplierItemStatusLabel(item.status)}
                        />
                      </td>
                      {priceAccess ? (
                        <td>
                          {purchase
                            ? formatMoneyAmount(purchase.unit_price, purchase.currency)
                            : "Nenhum preço observado"}
                        </td>
                      ) : null}
                      {priceAccess ? (
                        <td>{purchase ? formatDateTime(purchase.observed_at) : "—"}</td>
                      ) : null}
                      {priceAccess ? (
                        <td>
                          <button
                            type="button"
                            className="ghost"
                            aria-expanded={historyItemId === item.id}
                            aria-controls={`price-history-${item.id}`}
                            onClick={() =>
                              setHistoryItemId((current) => (current === item.id ? null : item.id))
                            }
                          >
                            {historyItemId === item.id ? "Ocultar histórico" : "Histórico"}
                          </button>
                        </td>
                      ) : null}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {historyItemId ? (
          <section
            className="panel"
            id={`price-history-${historyItemId}`}
            aria-label="Histórico de preços"
          >
            <h2>Histórico de preços</h2>
            {historyState.kind === "carregando" ? <LoadingState /> : null}
            {historyState.kind === "erro" ? <ErrorState error={historyState.error} /> : null}
            {historyState.kind === "ok" && historyState.data.price_access === false ? (
              <p>Sem permissão para consultar preços de compra.</p>
            ) : null}
            {historyState.kind === "ok" &&
            historyState.data.price_access !== false &&
            historyState.data.data.length === 0 ? (
              <EmptyState>Nenhum preço observado</EmptyState>
            ) : null}
            {historyState.kind === "ok" &&
            historyState.data.price_access !== false &&
            historyState.data.data.length > 0 ? (
              <div className="table-wrap">
                <table>
                  <caption>Observações append-only (mais recente primeiro)</caption>
                  <thead>
                    <tr>
                      <th>Valor</th>
                      <th>Data</th>
                      <th>Origem</th>
                      <th>Seleção</th>
                    </tr>
                  </thead>
                  <tbody>
                    {historyState.data.data.map((row) => (
                      <tr key={row.id}>
                        <td>{formatMoneyAmount(row.unit_price, row.currency)}</td>
                        <td>{formatDateTime(row.observed_at)}</td>
                        <td>{priceSourceLabel(row.source)}</td>
                        <td>{row.is_latest ? "Mais recente" : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </section>
        ) : null}
      </div>
    </div>
  );
}
