import { useEffect, useState } from "react";
import { formatCents } from "../lib/money";
import { catalogErrorMessage, fetchCatalog } from "./catalogApi";
import type { PublicProduct } from "./types";

function priceLabel(product: PublicProduct): string {
  if (product.from_price.cents === null) {
    return "Preço a definir";
  }
  const formatted = formatCents(product.from_price.cents);
  return product.price_is_from ? `A partir de ${formatted}` : formatted;
}

export function ProductShelf() {
  const [items, setItems] = useState<PublicProduct[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    setError(null);
    fetchCatalog()
      .then((data) => {
        setItems(data.items);
      })
      .catch((reason: unknown) => {
        setItems([]);
        setError(catalogErrorMessage(reason));
      })
      .finally(() => {
        setLoading(false);
      });
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <section id="paes" className="shelf" aria-label="Nossos pães">
      <div className="section-head">
        <h2>Nossos pães</h2>
        <p>Pães da casa, prontos para escolher o tamanho ou a embalagem.</p>
      </div>
      {loading ? <p className="shelf-status">Carregando os pães da casa…</p> : null}
      {error ? (
        <p className="shelf-status">
          {error}{" "}
          <button type="button" className="text-button" onClick={load}>
            Tentar novamente
          </button>
        </p>
      ) : null}
      {!loading && items && items.length === 0 && !error ? (
        <p className="shelf-status">Ainda não há pães publicados na vitrine.</p>
      ) : null}
      {items && items.length > 0 ? (
        <div className="shelf-grid">
          {items.map((product) => (
            <article key={product.slug} className="shelf-card">
              {product.image_url ? (
                <img src={product.image_url} alt={product.image_alt || product.name} />
              ) : (
                <div className="shelf-photo-fallback" aria-hidden="true" />
              )}
              <h3>{product.name}</h3>
              <p>{product.short_description}</p>
              <p className="shelf-options">{product.variants.map((variant) => variant.display_name).join(" · ")}</p>
              <p className="shelf-price">{priceLabel(product)}</p>
              {!product.is_available ? <p className="shelf-unavailable">Temporariamente indisponível</p> : null}
              <a className="primary shelf-link" href={`/paes/${product.slug}`}>
                Ver pão
              </a>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
