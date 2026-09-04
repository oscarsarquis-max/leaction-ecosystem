import { Link, useParams } from "react-router-dom";
import type { Envelope, ProductCard } from "../api/types";
import { ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { TechnicalAuditDetails } from "../components/TechnicalAuditDetails";
import { formatDateTime } from "../format";
import { useAsyncResource } from "../hooks/useAsyncResource";
import {
  isSupplyModeInPreparation,
  productFamilyLabel,
  productNetContentLabel,
  productPurposeLabel,
  productRecipeStatusLabel,
  productRecipeTone,
  productShelfLifeLabel,
  productStatusLabel,
  productStatusTone,
  productSupplyModeLabel,
  productUnitLabel,
} from "../language/products";
import { useCommand } from "../ops/useCommand";
import { useOrganization } from "../session/OrganizationContext";

export function ProductDetailPage() {
  const { productId } = useParams();
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const command = useCommand();

  const { state, reload } = useAsyncResource<Envelope<ProductCard>>(
    () => api.getProduct(productId!),
    [api, productId, orgId],
    Boolean(orgId && productId),
  );

  const product = state.kind === "ok" ? state.data.data : null;

  async function changeStatus(next: "active" | "inactive") {
    if (!product || command.pending) return;
    try {
      await command.run(`product-status:${product.id}:${next}`, (key) =>
        api.setProductStatus(product.id, next, { idempotencyKey: key, rowVersion: product.row_version }),
      );
      reload();
    } catch {
      /* erro apresentado em command.error */
    }
  }

  return (
    <div className="stage">
      <ListLive
        kind={state.kind}
        entityLabel={product?.display_name ?? "produto"}
        status={product ? productStatusLabel(product.status) : undefined}
      />
      <div>
        {state.kind === "carregando" ? <LoadingState /> : null}
        {state.kind === "erro" ? <ErrorState error={state.error} onRetry={() => reload()} /> : null}
        {product ? (
          <>
            <div className="page-head">
              <div>
                <h1>{product.display_name}</h1>
              </div>
            </div>
            <p className="lede">
              <StatusBadge tone={productStatusTone(product.status)} label={productStatusLabel(product.status)} />{" "}
              <StatusBadge tone={productRecipeTone(product)} label={productRecipeStatusLabel(product)} />{" "}
              Código {product.code} · {productFamilyLabel(product.family)}
            </p>
            {product.description ? <p>{product.description}</p> : null}

            {(product.operational_notes ?? []).length > 0 ? (
              <section className="panel">
                <h2>O que ainda falta nesta fase</h2>
                <ul>
                  {(product.operational_notes ?? []).map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </section>
            ) : null}

            <section className="panel">
              <h2>Identidade</h2>
              <p>
                <strong>Finalidade: </strong>
                {productPurposeLabel(product.purpose)}
              </p>
              <p>
                <strong>Abastecimento: </strong>
                {productSupplyModeLabel(product.supply_mode)}
              </p>
              <p>
                <strong>Família: </strong>
                {productFamilyLabel(product.family)}
              </p>
              <p>
                <strong>Receita: </strong>
                {productRecipeStatusLabel(product)}
              </p>
            </section>

            <section className="panel">
              <h2>Embalagem e medida</h2>
              <p>
                <strong>Unidade de estoque: </strong>
                {productUnitLabel(product.stock_unit)}
              </p>
              <p>
                <strong>Unidade de venda: </strong>
                {productUnitLabel(product.sale_unit)}
              </p>
              <p>
                <strong>Conteúdo líquido: </strong>
                {productNetContentLabel(product.net_content, product.net_content_unit)}
              </p>
              <p>
                <strong>Validade padrão: </strong>
                {productShelfLifeLabel(product.default_shelf_life_days)}
              </p>
              <p>
                <strong>Embalagem: </strong>
                {product.packaging_description || "Não informada"}
              </p>
            </section>

            <section className="panel">
              <h2>Ligações</h2>
              <p>
                {product.links
                  ? `${product.links.recipes_count} receita(s) e ${product.links.orders_count} ordem(ns) referenciam este produto.`
                  : "Ligações não disponíveis neste recorte."}
              </p>
            </section>

            {command.error ? (
              <p className="error" role="alert">
                {command.error.message || "Não foi possível concluir a ação."}
              </p>
            ) : null}

            <p>
              {hasPermission("product.update") ? (
                <Link className="primary" to={`/produtos/${product.id}/editar`}>
                  Editar produto
                </Link>
              ) : null}{" "}
              {hasPermission("product.activate") ? (
                <button
                  type="button"
                  className="ghost"
                  disabled={command.pending}
                  onClick={() => void changeStatus(product.status === "active" ? "inactive" : "active")}
                >
                  {product.status === "active" ? "Inativar produto" : "Ativar produto"}
                </button>
              ) : null}{" "}
              <Link className="ghost" to="/produtos">
                Voltar aos produtos
              </Link>
            </p>

            <section className="panel">
              <h2>Auditoria</h2>
              <TechnicalAuditDetails
                rows={[
                  { label: "Identificador do produto", value: product.id, copyable: true },
                  { label: "Versão de linha", value: String(product.row_version) },
                  { label: "Criado em", value: formatDateTime(product.created_at) },
                  { label: "Atualizado em", value: formatDateTime(product.updated_at) },
                ]}
              />
            </section>
          </>
        ) : null}
      </div>
      <aside className="panel">
        <h2>Produção</h2>
        {product && product.supply_mode === "purchased" ? (
          <p>Produto comprado pronto não gera ordem de produção.</p>
        ) : product && isSupplyModeInPreparation(product.supply_mode) ? (
          <p>Esta modalidade ainda está em preparação e não gera ordem de produção nesta fase.</p>
        ) : product && !product.has_published_recipe ? (
          <p>
            O cadastro é válido sem receita. Para planejar produção, vincule e publique uma receita
            para este produto.
          </p>
        ) : (
          <p>Produto com receita vigente: já pode entrar em planos e ordens de produção.</p>
        )}
        <p className="meta">Situação do produto não é liberação de venda nem de rotulagem.</p>
      </aside>
    </div>
  );
}
