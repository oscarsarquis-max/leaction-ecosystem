import { useEffect, useState } from "react";
import { fetchProductAccompaniments, type AccompanimentCard } from "./accompanimentsApi";

export function ProductAccompaniments({ slug }: { slug: string }) {
  const [items, setItems] = useState<AccompanimentCard[]>([]);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchProductAccompaniments(slug)
      .then((data) => {
        if (cancelled) {
          return;
        }
        setItems(data.enabled ? data.items : []);
        setNote(data.enabled ? data.commission_note : null);
      })
      .catch(() => {
        if (!cancelled) {
          setItems([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (!items.length) {
    return null;
  }

  return (
    <section className="acc-product" aria-labelledby="acc-product-title">
      <p className="eyebrow">Para a mesa</p>
      <h2 id="acc-product-title">Para acompanhar este pão</h2>
      <ul>
        {items.map((item) => (
          <li key={item.id}>
            <a href={item.story_href}>{item.name}</a>
            {item.why_pairs ? <span> — {item.why_pairs}</span> : null}
            {item.price_label ? <span> · {item.price_fresh ? item.price_label : `${item.price_label} (confirme no site de compra)`}</span> : null}
            {item.outbound_href && !item.demo && item.commercial_enabled !== false ? (
              <a
                className="acc-mini-out"
                href={item.outbound_href}
                target="_blank"
                rel="noopener noreferrer"
              >
                {item.outbound_label || "Ver no Mercado Livre"}
              </a>
            ) : item.demo ? (
              <span> — demonstração local, sem compra</span>
            ) : null}
          </li>
        ))}
      </ul>
      <p className="acc-notice">
        {items[0]?.external_notice ||
          "Compra e entrega realizadas separadamente pelo Mercado Livre ou pela Amazon. Confira preço e disponibilidade no site de compra."}
      </p>
      {note ? <p className="acc-commission">{note}</p> : null}
    </section>
  );
}
