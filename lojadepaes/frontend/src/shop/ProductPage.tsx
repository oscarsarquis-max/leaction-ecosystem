import { useEffect, useMemo, useState } from "react";
import { formatCents, lineTotalCents } from "../lib/money";
import { catalogErrorMessage, fetchProduct } from "./catalogApi";
import { FeaturedPhoto } from "./FeaturedPhoto";
import { ProductIngredients } from "./ProductIngredients";
import { AdaptationDisclosure } from "./AdaptationRequest";
import { useCart } from "./CartContext";
import { packDescription, type AdaptationDraft } from "./selection";
import { trackEvent } from "./tracking";
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
  const [adaptation, setAdaptation] = useState<AdaptationDraft>({ text: "", reason: "" });

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
  const dateHint = useMemo(() => {
    const raw = new URLSearchParams(window.location.search).get("data");
    if (!raw || !/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
      return null;
    }
    const [year, month, day] = raw.split("-").map(Number);
    const value = new Date(year, month - 1, day);
    return new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "2-digit", month: "2-digit" }).format(value);
  }, []);
  const unitCents = variant?.price.cents ?? null;
  const subtotal = unitCents !== null ? lineTotalCents(unitCents, quantity) : null;

  function handleAdd() {
    if (!product || !variant || !product.is_available || unitCents === null) {
      return;
    }
    cart.add(product.slug, variant.id, quantity, adaptation);
    trackEvent("fornada_escolher", {
      dados: { produto_id: variant.id, quantidade: quantity },
    });
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
            <FeaturedPhoto product={product} figureClassName="product-figure" />
          ) : null}
          <div>
            <h1>{product.name}</h1>
            {dateHint ? <p className="fornada-note">Pensando em {dateHint} — ainda sem reserva.</p> : null}
            {product.short_description ? <p className="product-summary">{product.short_description}</p> : null}
            {product.long_description ? <p>{product.long_description}</p> : null}
            <ProductIngredients ingredients={product.ingredients} />
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
            <AdaptationDisclosure value={adaptation} onChange={setAdaptation} />
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
