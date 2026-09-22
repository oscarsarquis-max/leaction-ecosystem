import { Link } from "react-router-dom";
import type { Envelope, ProductCard, ProductRecipeItem } from "../api/types";
import type { ApiClient } from "../api/client";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { ingredientHref, productHref, recipeHref } from "../navigation/returnTo";
import {
  describeProductStructure,
  graphItemKind,
  graphItemKindLabel,
  graphItemQuantityLabel,
  graphProductMeta,
  graphRecipeName,
  graphRecipeSituation,
  graphRecipeVersionLabel,
} from "./productStructureModel";

type PanelProps = {
  selectedId: string | null;
  listSearch: string;
  orgId: string | null;
  api: ApiClient;
};

export function ProductStructurePanel({
  selectedId,
  listSearch,
  orgId,
  api,
}: PanelProps) {
  const detail = useAsyncResource<Envelope<ProductCard>>(
    () => api.getProduct(selectedId!),
    [api, selectedId, orgId],
    Boolean(orgId && selectedId),
  );

  if (!selectedId) {
    return <ExamplePreview />;
  }

  if (detail.state.kind === "carregando") {
    return (
      <section className="product-structure" aria-labelledby="product-structure-title">
        <h2 id="product-structure-title">Estrutura cadastrada</h2>
        <p className="product-structure__status" role="status">
          Carregando a estrutura…
        </p>
      </section>
    );
  }

  if (detail.state.kind === "erro") {
    const openTo = productHref(selectedId, listSearch);
    return (
      <section className="product-structure" aria-labelledby="product-structure-title">
        <h2 id="product-structure-title">Estrutura cadastrada</h2>
        <p className="product-structure__alert" role="alert">
          Não foi possível carregar a estrutura deste produto.
        </p>
        <p className="product-structure__actions">
          <button type="button" className="primary" onClick={() => detail.reload()}>
            Tentar novamente
          </button>
          <Link className="ghost" to={openTo}>
            Abrir produto
          </Link>
        </p>
      </section>
    );
  }

  const product = detail.state.data.data;
  const view = describeProductStructure(product);
  const productTo = productHref(product.id, listSearch);

  return (
    <section className="product-structure" aria-labelledby="product-structure-title">
      <h2 id="product-structure-title">Estrutura cadastrada</h2>
      {view.kind === "purchased" ? (
        <div className="pgraph-flow">
          <div className="pgraph-col">
            <StructureNode
              kind="product"
              typeTitle="Produto"
              name={view.product.display_name}
              meta={graphProductMeta(view.product)}
              href={productTo}
            />
          </div>
          <div className="pgraph-edge" aria-hidden="true" />
          <div className="pgraph-col">
            <p className="product-structure__note">Produção não se aplica a produto comprado.</p>
          </div>
        </div>
      ) : null}
      {view.kind === "produced_gap" ? (
        <div className="pgraph-flow">
          <div className="pgraph-col">
            <StructureNode
              kind="product"
              typeTitle="Produto"
              name={view.product.display_name}
              meta={graphProductMeta(view.product)}
              href={productTo}
            />
          </div>
          <div className="pgraph-edge" aria-hidden="true" />
          <div className="pgraph-col">
            <StructureNode kind="gap" typeTitle="Receita técnica" name="Receita técnica não cadastrada." />
          </div>
        </div>
      ) : null}
      {view.kind === "produced_recipe" ? (
        <>
          <div className="pgraph-flow">
            <div className="pgraph-col">
              <StructureNode
                kind="product"
                typeTitle="Produto"
                name={view.product.display_name}
                meta={graphProductMeta(view.product)}
                href={productTo}
              />
            </div>
            <div className="pgraph-edge" aria-hidden="true" />
            <div className="pgraph-col">
              <StructureNode
                kind="recipe"
                typeTitle="Receita técnica"
                name={graphRecipeName(view.recipe)}
                meta={[graphRecipeVersionLabel(view.recipe.version_number), graphRecipeSituation(view.recipe)]}
                href={recipeHref(view.recipe.id, listSearch)}
              />
            </div>
            {view.visibleItems.length > 0 || view.hiddenCount > 0 ? (
              <>
                <div className="pgraph-edge" aria-hidden="true" />
                <div className="pgraph-col pgraph-col--items">
                  {view.visibleItems.map((item, index) => (
                    <RecipeItemNode key={itemKey(item, index)} item={item} listSearch={listSearch} />
                  ))}
                  {view.hiddenCount > 0 ? (
                    <Link className="pgraph-more" to={recipeHref(view.recipe.id, listSearch)}>
                      + {view.hiddenCount} componentes na receita
                    </Link>
                  ) : null}
                </div>
              </>
            ) : null}
          </div>
          {view.missingPrep ? (
            <p className="product-structure__note">Modo de preparo ainda não registrado.</p>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

function ExamplePreview() {
  return (
    <section
      className="product-structure product-structure--exemplo"
      aria-labelledby="product-structure-title"
    >
      <h2 id="product-structure-title">Como a estrutura de um produto aparece</h2>
      <p className="product-structure__mark">Exemplo ilustrativo</p>
      <div className="pgraph-flow">
        <div className="pgraph-col">
          <StructureNode kind="product" typeTitle="Produto" name="Produto" example />
        </div>
        <div className="pgraph-edge" />
        <div className="pgraph-col">
          <StructureNode kind="recipe" typeTitle="Receita técnica" name="Receita técnica" example />
        </div>
        <div className="pgraph-edge" />
        <div className="pgraph-col pgraph-col--items">
          <StructureNode kind="ingredient" typeTitle="Ingrediente" name="Ingrediente" example />
          <StructureNode kind="ingredient" typeTitle="Ingrediente" name="Ingrediente" example />
          <StructureNode kind="component" typeTitle="Componente" name="Componente" example />
        </div>
      </div>
      <p className="product-structure__hint">
        Selecione um produto na tabela para substituir esta prévia pela estrutura cadastrada.
      </p>
    </section>
  );
}

function RecipeItemNode({ item, listSearch }: { item: ProductRecipeItem; listSearch: string }) {
  const kind = graphItemKind(item);
  const typeTitle = graphItemKindLabel(kind);
  const name = item.display_name?.trim() || item.code?.trim() || typeTitle;
  const quantity = graphItemQuantityLabel(item);
  const href = item.ingredient_id
    ? ingredientHref(item.ingredient_id, listSearch)
    : undefined;
  return (
    <StructureNode
      kind={kind}
      typeTitle={typeTitle}
      name={name}
      meta={quantity ? [quantity] : undefined}
      href={href}
    />
  );
}

function itemKey(item: ProductRecipeItem, index: number): string {
  return `${item.ingredient_id ?? item.code ?? "item"}-${index}`;
}

function StructureNode({
  kind,
  typeTitle,
  name,
  meta,
  href,
  example = false,
}: {
  kind: "product" | "recipe" | "ingredient" | "component" | "gap";
  typeTitle: string;
  name?: string;
  meta?: string[];
  href?: string;
  example?: boolean;
}) {
  const className = `pnode pnode--${kind}${example ? " pnode--exemplo" : ""}`;
  const inner = (
    <>
      <span className="pnode__icon" aria-hidden="true">
        <GraphGlyph kind={kind} />
      </span>
      <span className="pnode__body">
        <span className="pnode__kind">{typeTitle}</span>
        {name ? <span className="pnode__name">{name}</span> : null}
        {meta?.map((line) => (
          <span key={line} className="pnode__meta">
            {line}
          </span>
        ))}
      </span>
    </>
  );
  if (href && !example) {
    return (
      <Link className={className} to={href} aria-label={`${typeTitle} ${name ?? ""}`.trim()}>
        {inner}
      </Link>
    );
  }
  return <div className={className}>{inner}</div>;
}

function GraphGlyph({ kind }: { kind: "product" | "recipe" | "ingredient" | "component" | "gap" }) {
  if (kind === "product") {
    return (
      <svg viewBox="0 0 20 20" width="18" height="18">
        <rect x="3" y="3" width="14" height="14" rx="1.5" fill="currentColor" />
      </svg>
    );
  }
  if (kind === "recipe" || kind === "gap") {
    return (
      <svg viewBox="0 0 20 20" width="18" height="18">
        <path
          d="M6 3h6l4 4v10H6z"
          fill={kind === "gap" ? "none" : "currentColor"}
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
        <path d="M12 3v4h4" fill="none" stroke="currentColor" strokeWidth="1.6" />
      </svg>
    );
  }
  if (kind === "component") {
    return (
      <svg viewBox="0 0 20 20" width="18" height="18">
        <polygon
          points="10,2 18,7 18,13 10,18 2,13 2,7"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
        />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 20 20" width="18" height="18">
      <circle cx="10" cy="10" r="6.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}
