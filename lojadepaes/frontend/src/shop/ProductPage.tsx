import { useEffect, useMemo, useState } from "react";
import { formatCents, lineTotalCents } from "../lib/money";
import { catalogErrorMessage, fetchProduct } from "./catalogApi";
import { useCart } from "./CartContext";
import { packDescription } from "./selection";
import type { PublicProduct } from "./types";

type ProductPageProps = {
  slug: string;
};

export function ProductPage({ slug }: ProductPageProps) {
  const cart = useCart();
  const [product, setProduct] = useState<PublicProduct | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [variantId, setVariantId] = useState<string>("");
  const [quantity, setQuantity] = useState(1);

  useEffect(() => {
    let cancelled = false;
    fetchProduct(slug)
      .then((data) => {
        if (cancelled) {
          return;
        }
        setProduct(data);
        setVariantId(data.variants[0]?.id ?? "");
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(catalogErrorMessage(reason));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  const variant = useMemo(
    () => product?.variants.find((item) => item.id === variantId) ?? product?.variants[0],
    [product, variantId],
  );
  const unitCents = variant?.price.cents ?? null;
  const subtotal = unitCents !== null ? lineTotalCents(unitCents, quantity) : null;

  function handleAdd() {
    if (!product || !variant || !product.is_available || unitCents === null) {
      return;
    }
    cart.add(product.slug, variant.id, quantity);
  }

  return (
    <main className="product-page">
      <p className="eyebrow">
        <a href="/#paes">Nossos pães</a>
      </p>
      {!product && !error ? <p>Carregando este pão…</p> : null}
      {error ? <p className="shelf-status">{error}</p> : null}
      {product ? (
        <article className="product-detail">
          {product.image_url ? (
            <img src={product.image_url} alt={product.image_alt || product.name} />
          ) : null}
          <div>
            <h1>{product.name}</h1>
            <p>{product.long_description || product.short_description}</p>
            {product.ingredients && product.ingredients.length > 0 ? (
              <>
                <h2>Ingredientes básicos</h2>
                <p>{product.ingredients.map((item) => item.name).join(", ")}.</p>
              </>
            ) : null}
            <p className="demo">{product.allergen_note}</p>
            <fieldset className="product-options">
              <legend>Apresentação</legend>
              {product.variants.map((item) => (
                <label key={item.id}>
                  <input
                    type="radio"
                    name="variant"
                    checked={variant?.id === item.id}
                    onChange={() => setVariantId(item.id)}
                  />
                  <span>
                    {item.display_name}
                    {item.pack_label && item.pack_label !== item.display_name ? ` · ${item.pack_label}` : ""}
                    {item.price.cents !== null ? ` — ${formatCents(item.price.cents)}` : ""}
                  </span>
                </label>
              ))}
            </fieldset>
            <label className="product-qty">
              Quantidade
              <input
                type="number"
                min={1}
                max={20}
                value={quantity}
                onChange={(event) => setQuantity(Math.max(1, Number.parseInt(event.target.value, 10) || 1))}
              />
            </label>
            {variant ? <p className="shelf-options">{packDescription(product, variant.id)}</p> : null}
            <p className="shelf-price">
              {unitCents === null ? "Preço a definir" : `Subtotal ${formatCents(subtotal ?? 0)}`}
            </p>
            {!product.is_available ? <p className="shelf-unavailable">Temporariamente indisponível</p> : null}
            <button
              type="button"
              className="primary"
              disabled={!product.is_available || unitCents === null || !variant}
              onClick={handleAdd}
            >
              Adicionar à seleção
            </button>
          </div>
        </article>
      ) : null}
    </main>
  );
}
