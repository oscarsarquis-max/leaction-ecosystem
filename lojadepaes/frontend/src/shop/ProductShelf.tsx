import { useEffect, useMemo, useState } from "react";
import { formatCents } from "../lib/money";
import { BakeCalendar } from "./BakeCalendar";
import { useCart } from "./CartContext";
import { catalogErrorMessage, fetchShowcase } from "./catalogApi";
import { FeaturedPhoto } from "./FeaturedPhoto";
import { FornadaPanel } from "./FornadaPanel";
import { ProductIngredients } from "./ProductIngredients";
import type { CalendarLine } from "./calendarApi";
import type { PublicProduct } from "./types";

function priceLabel(product: PublicProduct): string {
  if (product.from_price.cents === null) {
    return "Preço a definir";
  }
  const formatted = formatCents(product.from_price.cents);
  return product.price_is_from ? `A partir de ${formatted}` : formatted;
}

export function ProductShelf() {
  const cart = useCart();
  const lines = useMemo<CalendarLine[]>(
    () =>
      cart.lines.map((line) => ({
        kind: "product",
        variant_id: line.variantId,
        quantity: line.quantity,
      })),
    [cart.lines],
  );
  const [items, setItems] = useState<PublicProduct[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  function load() {
    setLoading(true);
    setError(null);
    fetchShowcase()
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
    <section id="paes" className="shelf" aria-labelledby="shelf-title">
      <header className="shelf-head">
        <h2 id="shelf-title">Nossos pães</h2>
      </header>
      <div className="shelf-band">
        <BakeCalendar
          lines={lines}
          layout="shelf"
          selectedDate={selectedDate}
          onSelectDate={setSelectedDate}
        />
        <FornadaPanel selectedDate={selectedDate} lines={lines} cartCount={cart.count} />
      </div>
      {loading ? <p className="shelf-status">Carregando os pães da casa…</p> : null}
      {error ? (
        <p className="shelf-status" role="alert">
          {error}{" "}
          <button type="button" className="text-button" onClick={load}>
            Tentar novamente
          </button>
        </p>
      ) : null}
      {!loading && items && items.length === 0 && !error ? (
        <p className="shelf-status">Ainda não há pães na vitrine.</p>
      ) : null}
      {items && items.length > 0 ? (
        <div className="shelf-grid">
          {items.map((product) => (
            <article key={product.slug} className="shelf-card">
              <FeaturedPhoto product={product} />
              <div className="shelf-card-body">
                <h3>{product.name}</h3>
                {product.short_description ? (
                  <p className="shelf-card-summary">{product.short_description}</p>
                ) : null}
                <ProductIngredients ingredients={product.ingredients} expandable />
                <p className="shelf-options">
                  {product.variants.map((variant) => variant.display_name).join(" · ")}
                </p>
              </div>
              <div className="shelf-card-action">
                <p className="shelf-price">{priceLabel(product)}</p>
                {!product.is_available ? (
                  <p className="shelf-unavailable">Temporariamente indisponível</p>
                ) : null}
                {product.is_available ? (
                  <a className="primary shelf-link" href={`/paes/${product.slug}`}>
                    Escolher meu pão
                  </a>
                ) : (
                  <a className="text-button shelf-link" href={`/paes/${product.slug}`}>
                    Ver pão
                  </a>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
