import { useMemo, useState } from "react";
import { Link, useLocation, useParams, useSearchParams } from "react-router-dom";
import type { Envelope, LabelingDossier, ProductCard } from "../api/types";
import { ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { TechnicalAuditDetails } from "../components/TechnicalAuditDetails";
import { formatDateTime, formatDecimal } from "../format";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { nutrientLabel } from "../language/labeling";
import {
  isSupplyModeInPreparation,
  productComponentRoleLabel,
  productFamilyLabel,
  productHasPrep,
  productInitials,
  productLabelingStatusLabel,
  productNetContentLabel,
  productNextActionLabel,
  productProductionLabel,
  productQuantityLabel,
  productReadyToProduce,
  productRecipeStatusLabel,
  productRecipeTone,
  productStatusLabel,
  productStatusTone,
  productSupplyModeLabel,
  productSupplyModeTone,
  productUnitLabel,
  productYieldLabel,
} from "../language/products";
import { safeReturnTo } from "../navigation/returnTo";
import { useCommand } from "../ops/useCommand";
import { useOrganization } from "../session/OrganizationContext";

export function ProductDetailPage() {
  const { productId } = useParams();
  const location = useLocation();
  const [params] = useSearchParams();
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const command = useCommand();
  const [labelOpen, setLabelOpen] = useState(false);

  const listTo = safeReturnTo(params.get("from"), "/produtos");
  const { state, reload } = useAsyncResource<Envelope<ProductCard>>(
    () => api.getProduct(productId!),
    [api, productId, orgId],
    Boolean(orgId && productId),
  );
  const dossiers = useAsyncResource<{ items: LabelingDossier[]; total: number }>(
    () => api.listLabelingDossiers(),
    [api, orgId],
    Boolean(orgId && hasPermission("labeling.read")),
  );

  const product = state.kind === "ok" ? state.data.data : null;
  const recipe = product?.current_recipe ?? null;
  const dossier = useMemo(() => {
    if (!recipe || dossiers.state.kind !== "ok") return null;
    return dossiers.state.data.items.find((row) => row.formulation_id === recipe.id) ?? null;
  }, [dossiers.state, recipe]);

  const dossierDetail = useAsyncResource<Envelope<LabelingDossier>>(
    () => api.getLabelingDossier(dossier!.id),
    [api, dossier?.id],
    Boolean(dossier && hasPermission("labeling.read")),
  );
  const previewDossier =
    dossierDetail.state.kind === "ok" ? dossierDetail.state.data.data : dossier;

  const labelingStatus = productLabelingStatusLabel({
    supply_mode: product?.supply_mode,
    dossierStatus: dossier?.status ?? null,
    recipePublished: Boolean(recipe?.is_published),
    recipeVersionMatches: dossier
      ? Boolean(recipe && dossier.formulation_version_id === recipe.version_id)
      : null,
  });

  async function changeStatus(next: "active" | "inactive") {
    if (!product || command.pending) return;
    try {
      await command.run(`product-status:${product.id}:${next}`, (key) =>
        api.setProductStatus(product.id, next, { idempotencyKey: key, rowVersion: product.row_version }),
      );
      reload();
    } catch {
      /* command.error */
    }
  }

  const checks = product ? readinessChecks(product) : [];
  const commercialMissing =
    product != null && !product.packaging_description && !product.net_content;
  const canPreview = Boolean(dossier && hasPermission("labeling.read"));

  return (
    <div className="stage product-doc">
      <ListLive
        kind={state.kind}
        entityLabel={product?.display_name ?? "produto"}
        status={product ? productStatusLabel(product.status) : undefined}
      />
      <div>
        <p className="product-back">
          <Link to={listTo}>{params.get("from") ? "Voltar" : "Voltar para Produtos"}</Link>
          {" · "}
          <Link to="/fluxo">Voltar ao fluxo produtivo</Link>
        </p>
        {state.kind === "carregando" ? <LoadingState /> : null}
        {state.kind === "erro" ? <ErrorState error={state.error} onRetry={() => reload()} /> : null}
        {product ? (
          <>
            <header className="product-identity">
              <div className="product-identity__media" aria-hidden="false">
                <div className="product-fallback" aria-label="Imagem do produto não informada">
                  <span className="product-fallback__mode">
                    {product.supply_mode === "purchased" ? "Comprado" : "Produzido"}
                  </span>
                  <span className="product-fallback__initials">{productInitials(product.display_name)}</span>
                </div>
                <p className="meta">Imagem do produto não informada.</p>
              </div>
              <div className="product-identity__core">
                <h1>{product.display_name}</h1>
                <p className="meta">{product.code}</p>
                <p>
                  <StatusBadge tone={productStatusTone(product.status)} label={productStatusLabel(product.status)} />{" "}
                  <StatusBadge
                    tone={productSupplyModeTone(product.supply_mode)}
                    label={productSupplyModeLabel(product.supply_mode)}
                  />{" "}
                  <StatusBadge tone={productRecipeTone(product)} label={productProductionLabel(product)} />{" "}
                  <StatusBadge
                    tone={labelingStatus === "Aprovada" || labelingStatus === "Não se aplica" ? "neutro" : "atencao"}
                    label={labelingStatus}
                  />
                </p>
                <dl className="product-facts">
                  <div>
                    <dt>Modalidade</dt>
                    <dd>{productSupplyModeLabel(product.supply_mode)}</dd>
                  </div>
                  <div>
                    <dt>Família</dt>
                    <dd>{productFamilyLabel(product.family)}</dd>
                  </div>
                  <div>
                    <dt>Unidade comercial</dt>
                    <dd>{productUnitLabel(product.sale_unit)}</dd>
                  </div>
                  <div>
                    <dt>Receita</dt>
                    <dd>{productRecipeStatusLabel(product)}</dd>
                  </div>
                  <div>
                    <dt>Situação produtiva</dt>
                    <dd>{productProductionLabel(product)}</dd>
                  </div>
                  <div>
                    <dt>Situação comercial</dt>
                    <dd>{labelingStatus}</dd>
                  </div>
                  <div>
                    <dt>Próxima ação</dt>
                    <dd>{productNextActionLabel(product)}</dd>
                  </div>
                  {commercialMissing ? (
                    <div className="product-facts--span">
                      <dt>Pendência comercial</dt>
                      <dd>Embalagem e conteúdo líquido não informados.</dd>
                    </div>
                  ) : (
                    <>
                      {product.packaging_description ? (
                        <div>
                          <dt>Embalagem</dt>
                          <dd>{product.packaging_description}</dd>
                        </div>
                      ) : null}
                      {product.net_content ? (
                        <div>
                          <dt>Conteúdo líquido</dt>
                          <dd>{productNetContentLabel(product.net_content, product.net_content_unit)}</dd>
                        </div>
                      ) : null}
                    </>
                  )}
                </dl>
                {canPreview ? (
                  <p className="product-identity__preview-actions">
                    <button type="button" className="ghost" onClick={() => setLabelOpen(true)}>
                      Ver prévia da rotulagem
                    </button>
                    {labelingStatus === "Aprovada" && hasPermission("labeling.render") ? (
                      <Link className="ghost" to={`/conformidade/dossies/${dossier!.id}/imprimir`}>
                        Imprimir etiqueta
                      </Link>
                    ) : null}
                    <Link className="ghost" to={`/conformidade/dossies/${dossier!.id}`}>
                      Completar dossiê
                    </Link>
                  </p>
                ) : product.supply_mode === "purchased" ? (
                  <p className="meta">Rotulagem não se aplica a produto comprado neste recorte.</p>
                ) : (
                  <p className="meta">Rotulagem não iniciada.</p>
                )}
              </div>
            </header>

            <section>
              <h2>Como este produto é obtido</h2>
              {product.supply_mode === "purchased" ? (
                <p>
                  Produto adquirido pronto. Receita e produção: <strong>Não se aplica</strong>.
                  Produto comprado pronto não gera ordem de produção. Fornecedor, item e estoque não
                  estão neste cadastro.
                </p>
              ) : isSupplyModeInPreparation(product.supply_mode) ? (
                <p>Modalidade em preparação. Receita e produção ainda não operam nesta fase.</p>
              ) : recipe ? (
                <dl className="product-facts">
                  <div>
                    <dt>Receita</dt>
                    <dd>
                      {recipe.display_name} ({recipe.code})
                    </dd>
                  </div>
                  <div>
                    <dt>Versão</dt>
                    <dd>v{recipe.version_number}</dd>
                  </div>
                  <div>
                    <dt>Publicação</dt>
                    <dd>{recipe.is_published ? "Publicada" : "Rascunho — não vigente"}</dd>
                  </div>
                  <div>
                    <dt>Publicado em</dt>
                    <dd>
                      {recipe.published_at ? formatDateTime(recipe.published_at) : "Sem publicação"}
                    </dd>
                  </div>
                  <div>
                    <dt>Rendimento</dt>
                    <dd>{productYieldLabel(recipe.yield_mass_g)}</dd>
                  </div>
                </dl>
              ) : (
                <p>
                  Não há receita ligada a este produto. Cadastro válido sem receita; produção fica
                  bloqueada até haver receita vigente.
                </p>
              )}
            </section>

            {product.supply_mode === "produced" && recipe ? (
              <>
                <section>
                  <h2>Componentes</h2>
                  {recipe.items.length === 0 ? (
                    <p>Nenhum componente informado nesta versão.</p>
                  ) : (
                    <div className="table-wrap">
                      <table>
                        <caption>Componentes da receita {recipe.code}</caption>
                        <thead>
                          <tr>
                            <th>Componente</th>
                            <th>Quantidade</th>
                            <th>Função</th>
                            <th></th>
                          </tr>
                        </thead>
                        <tbody>
                          {recipe.items.map((item) => (
                            <tr key={`${item.code}-${item.quantity}`}>
                              <td>{item.display_name || item.code || "Componente sem nome"}</td>
                              <td>{productQuantityLabel(item.quantity, item.unit)}</td>
                              <td>{productComponentRoleLabel(item)}</td>
                              <td>
                                {item.ingredient_id && hasPermission("ingredient.read") ? (
                                  <Link
                                    to={`/componentes/ingredientes/${item.ingredient_id}?from=${encodeURIComponent(location.pathname + location.search)}`}
                                  >
                                    Abrir ingrediente
                                  </Link>
                                ) : null}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>
                <section>
                  <h2>Modo de preparo</h2>
                  <p className="meta">
                    Versão v{recipe.version_number}
                    {recipe.is_published ? " publicada" : " em rascunho"}.
                  </p>
                  {recipe.steps.length === 0 ? (
                    <p>
                      Sem sequência de preparo.{" "}
                      {hasPermission("recipe.read") ? (
                        <Link to={`/receitas/${recipe.id}`}>Registrar etapas na receita</Link>
                      ) : (
                        "Registrar etapas na receita."
                      )}
                    </p>
                  ) : (
                    <ol className="product-steps">
                      {recipe.steps.map((step) => (
                        <li key={step.sequence}>
                          <strong>{step.title}</strong>
                          {step.instructions ? ` — ${step.instructions}` : ""}
                        </li>
                      ))}
                    </ol>
                  )}
                </section>
              </>
            ) : null}

            <section>
              <h2>Prontidão e pendências</h2>
              <p className="meta">
                Produção: {productProductionLabel(product)}. Comercial:{" "}
                {labelingStatus === "Aprovada" && product.net_content
                  ? "Pode ser apresentado com as informações já cadastradas."
                  : "Ainda não está pronto para apresentação comercial."}
              </p>
              <div className="table-wrap">
                <table>
                  <caption>Verificações</caption>
                  <thead>
                    <tr>
                      <th>Verificação</th>
                      <th>Situação</th>
                      <th>Causa</th>
                      <th>Consequência</th>
                      <th>Ação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {checks.map((row) => (
                      <tr key={row.id}>
                        <td>{row.label}</td>
                        <td>{row.ok ? "Ok" : "Pendente"}</td>
                        <td>{row.cause}</td>
                        <td>{row.consequence}</td>
                        <td>{row.action}</td>
                      </tr>
                    ))}
                    <tr>
                      <td>Imagem do produto</td>
                      <td>Pendente</td>
                      <td>Imagem do produto não informada.</td>
                      <td>Não bloqueia produção.</td>
                      <td>Aguardar contrato de mídia.</td>
                    </tr>
                    <tr>
                      <td>Rotulagem</td>
                      <td>{labelingStatus === "Não se aplica" || labelingStatus === "Aprovada" ? "Ok" : "Pendente"}</td>
                      <td>
                        {labelingStatus === "Não iniciada"
                          ? "Rotulagem não iniciada."
                          : labelingStatus === "Rotulagem: requer revisão"
                            ? "Rotulagem aguardando revisão."
                            : labelingStatus}
                      </td>
                      <td>
                        {product.supply_mode === "purchased"
                          ? "Não se aplica."
                          : "Pode bloquear a liberação comercial."}
                      </td>
                      <td>
                        {dossier && hasPermission("labeling.read") ? (
                          <Link to={`/conformidade/dossies/${dossier.id}`}>Completar dossiê</Link>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            {command.error ? (
              <p className="error" role="alert">
                {command.error.message || "Não foi possível concluir a ação."}
              </p>
            ) : null}

            <section className="product-actions">
              <h2>Ações</h2>
              <p>
                {productReadyToProduce(product) && hasPermission("production.board.read") ? (
                  <Link className="primary" to={`/producao?product_id=${product.id}`}>
                    Abrir produção deste produto
                  </Link>
                ) : null}{" "}
                {recipe && hasPermission("recipe.read") ? (
                  <Link className="ghost" to={`/receitas/${recipe.id}`}>
                    Abrir receita
                  </Link>
                ) : null}{" "}
                {hasPermission("costing.read") ? (
                  <Link className="ghost" to={`/gestao/custos/formacao?produto=${product.id}`}>
                    Analisar custos
                  </Link>
                ) : null}{" "}
                {hasPermission("product.update") ? (
                  <Link className="ghost" to={`/produtos/${product.id}/editar`}>
                    Editar dados do produto
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
                {recipe && hasPermission("recipe.read") ? (
                  productHasPrep(product) ? (
                    <Link className="ghost" to={`/receitas/${recipe.id}/versoes/${recipe.version_id}/ficha`}>
                      Imprimir ficha operacional
                    </Link>
                  ) : (
                    <span className="meta">
                      Imprimir ficha operacional indisponível. Registre o modo de preparo antes de imprimir a ficha.
                    </span>
                  )
                ) : null}{" "}
                <a className="ghost" href="#historico">
                  Ver histórico
                </a>
              </p>
            </section>

            <section id="historico">
              <h2>Histórico</h2>
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

      {labelOpen ? (
        <div className="product-label-dialog" role="dialog" aria-modal="true" aria-label="Prévia da rotulagem">
          <div className="product-label-dialog__panel">
            <p>
              <button type="button" className="ghost" onClick={() => setLabelOpen(false)}>
                Fechar
              </button>
            </p>
            <LabelPreview product={product!} dossier={previewDossier} />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function LabelPreview({
  product,
  dossier,
}: {
  product: ProductCard;
  dossier: LabelingDossier | null;
}) {
  const current = dossier?.current ?? null;
  const ingredients = current?.ingredients ?? [];
  const warnings = current?.warnings ?? [];
  const nutrition = current?.nutrition;
  const completeLines =
    nutrition?.lines.filter(
      (line) =>
        line.completeness === "complete" && Boolean(line.declared_per_100g || line.presented),
    ) ?? [];
  const conservation = current?.mandatory?.find(
    (row) => /conserv|armazen/i.test(row.label) || /conserv|armazen/i.test(row.code),
  );
  const pendencies: string[] = [];
  if (!product.net_content) pendencies.push("Conteúdo líquido não informado.");
  if (!product.packaging_description) pendencies.push("Embalagem não informada.");
  if (ingredients.length === 0) pendencies.push("Lista de ingredientes incompleta.");
  if (completeLines.length === 0) pendencies.push("Informação nutricional incompleta.");
  if (!dossier || dossier.status !== "reviewed") pendencies.push("Rotulagem ainda não aprovada.");

  return (
    <article className="label-preview">
      <p className="label-preview__mark">Prévia para revisão — não aprovada</p>
      <h2>{product.display_name}</h2>
      {product.net_content ? (
        <p>
          Conteúdo líquido: {productNetContentLabel(product.net_content, product.net_content_unit)}
        </p>
      ) : null}
      <h3>Ingredientes</h3>
      {ingredients.length > 0 ? (
        <p>{ingredients.map((item) => item.display_name).filter(Boolean).join(", ")}.</p>
      ) : (
        <p>Lista de ingredientes ainda não disponível nesta prévia.</p>
      )}
      <h3>Alergênicos</h3>
      {warnings.length > 0 ? (
        <ul>
          {warnings.map((row) => (
            <li key={row.code}>{row.statement}</li>
          ))}
        </ul>
      ) : (
        <p>Declaração de alergênicos pendente.</p>
      )}
      {conservation?.value ? (
        <>
          <h3>Conservação</h3>
          <p>{conservation.value}</p>
        </>
      ) : null}
      {completeLines.length > 0 ? (
        <>
          <h3>Informação nutricional</h3>
          {nutrition?.portion_g ? (
            <p className="meta">
              Porção: {formatDecimal(nutrition.portion_g)} g
              {nutrition.household_measure ? ` (${nutrition.household_measure})` : ""}
            </p>
          ) : null}
          <table>
            <caption>Valores por 100 g</caption>
            <thead>
              <tr>
                <th>Nutriente</th>
                <th>Valor</th>
              </tr>
            </thead>
            <tbody>
              {completeLines.map((line) => (
                <tr key={line.nutrient_code}>
                  <td>{nutrientLabel(line.nutrient_code)}</td>
                  <td>{formatDecimal(line.declared_per_100g || line.presented)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <p>Informação nutricional incompleta — não exibida como tabela de etiqueta.</p>
      )}
      {pendencies.length > 0 ? (
        <>
          <h3>Pendências</h3>
          <ul>
            {pendencies.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          {dossier ? (
            <p>
              <Link to={`/conformidade/dossies/${dossier.id}`}>Completar dossiê</Link>
            </p>
          ) : null}
        </>
      ) : null}
    </article>
  );
}

function readinessChecks(product: ProductCard): Array<{
  id: string;
  label: string;
  ok: boolean;
  cause: string;
  consequence: string;
  action: string;
}> {
  if (product.supply_mode === "purchased" || isSupplyModeInPreparation(product.supply_mode)) {
    return [
      {
        id: "na",
        label: "Receita publicada",
        ok: true,
        cause: "Não se aplica.",
        consequence: "Sem ordem de produção.",
        action: "—",
      },
    ];
  }
  const recipe = product.current_recipe;
  const saleOk = Boolean(product.sale_unit);
  const hasSteps = productHasPrep(product);
  return [
    {
      id: "recipe",
      label: "Receita publicada",
      ok: Boolean(product.has_published_recipe),
      cause: product.has_published_recipe ? "Versão publicada ligada ao produto." : "Sem receita vigente.",
      consequence: product.has_published_recipe
        ? hasSteps
          ? "Pode gerar ordem."
          : "Ainda falta o modo de preparo."
        : "Produção bloqueada.",
      action: product.has_published_recipe ? "—" : "Abrir ou publicar a receita.",
    },
    {
      id: "items",
      label: "Componentes informados",
      ok: Boolean(recipe && recipe.items.length > 0),
      cause: recipe && recipe.items.length > 0 ? "Itens da versão vigente." : "Nenhum componente na versão.",
      consequence:
        recipe && recipe.items.length > 0
          ? hasSteps
            ? "Componentes e preparo informados."
            : "Componentes disponíveis; preparo incompleto."
          : "Não há o que pesar.",
      action: recipe ? "Abrir receita" : "Ligar uma receita ao produto.",
    },
    {
      id: "yield",
      label: "Rendimento informado",
      ok: Boolean(recipe?.yield_mass_g),
      cause: recipe?.yield_mass_g ? "Massa de rendimento gravada." : "Rendimento ausente.",
      consequence: recipe?.yield_mass_g ? "Escala conhecida." : "Sem base de escala.",
      action: recipe?.yield_mass_g ? "—" : "Informar rendimento na receita.",
    },
    {
      id: "steps",
      label: "Etapas informadas",
      ok: hasSteps,
      cause: hasSteps ? "Modo de preparo gravado." : "Sem etapas.",
      consequence: hasSteps ? "Preparo visível." : "Sem sequência de preparo.",
      action: hasSteps ? "—" : "Registrar etapas na receita.",
    },
    {
      id: "unit",
      label: "Unidade comercial",
      ok: saleOk,
      cause: saleOk ? "Unidade de venda cadastrada." : "Unidade comercial ausente.",
      consequence: saleOk ? "Identidade comercial completa neste recorte." : "Cadastro incompleto.",
      action: saleOk ? "—" : "Editar dados do produto.",
    },
  ];
}
