import { useEffect, useState, type ReactNode } from "react";
import { StorefrontLayout } from "../../components/StorefrontLayout";
import { formatCents } from "../../lib/money";
import { PartnerMarkLarge } from "./PartnerBadge";
import { deliveryLine, fetchPartnerPage, type PublicPartnerPage } from "./publicApi";
import "./marketplace-public.css";

type Props = {
  slug: string;
  /** O que a rota mostrava antes do marketplace: usado quando a página não existe ou o marketplace está desligado. */
  fallback: ReactNode;
};

function breadHref(slug: string): string {
  return `/paes/${encodeURIComponent(slug)}`;
}

export function PartnerPage({ slug, fallback }: Props) {
  const [state, setState] = useState<{ status: "loading" | "ready" | "missing"; data: PublicPartnerPage | null }>({
    status: "loading",
    data: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading", data: null });
    fetchPartnerPage(slug)
      .then((data) => {
        if (cancelled) return;
        if (data && data.partner && Array.isArray(data.products)) {
          setState({ status: "ready", data });
          document.title = `${data.partner.brand_name} — Loja de Pães`;
        } else {
          setState({ status: "missing", data: null });
        }
      })
      .catch(() => {
        if (!cancelled) setState({ status: "missing", data: null });
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (state.status === "missing") {
    return <>{fallback}</>;
  }
  if (state.status === "loading" || !state.data) {
    return null;
  }

  const { partner, products, combos } = state.data;
  const first = products[0];

  return (
    <StorefrontLayout>
      <main className="mkp-page">
        <p className="mkp-kicker">A Loja de Pães apresenta</p>
        <section className="mkp-hero" aria-labelledby="mkp-partner-name">
          {partner.photo_url ? (
            <img className="mkp-hero-photo" src={partner.photo_url} alt={`Foto de ${partner.brand_name}`} />
          ) : (
            <span className="mkp-hero-photo mkp-photo-empty" aria-hidden="true" />
          )}
          <div className="mkp-hero-body" style={{ borderTopColor: partner.highlight_hex }}>
            <div className="mkp-hero-brand">
              <PartnerMarkLarge partner={partner} />
              <div>
                <h1 id="mkp-partner-name">{partner.brand_name}</h1>
                <p className="mkp-muted">
                  {partner.city} · {partner.region}
                </p>
              </div>
            </div>
            {partner.story ? <p className="mkp-story">{partner.story}</p> : null}
          </div>
        </section>

        {first ? (
          <section className="mkp-delivery" aria-labelledby="mkp-delivery-title">
            <h2 id="mkp-delivery-title">Entrega feita por {partner.brand_name}</h2>
            <p>{deliveryLine(first.delivery, formatCents)}. Chega separado do seu pão, que segue na data da fornada.</p>
          </section>
        ) : null}

        {combos.length ? (
          <section aria-labelledby="mkp-combos-title" className="mkp-block">
            <h2 id="mkp-combos-title">Combinações da casa</h2>
            <ul className="mkp-combos">
              {combos.map((combo) => (
                <li key={combo.id} className="mkp-combo">
                  <p className="mkp-combo-kicker">Pão da casa + {partner.brand_name}</p>
                  <p className="mkp-combo-name">
                    {combo.house_product_slug ? (
                      <a href={breadHref(combo.house_product_slug)}>{combo.house_product_name ?? "Pão da casa"}</a>
                    ) : (
                      "Pão da casa"
                    )}{" "}
                    <span aria-hidden="true">+</span> <span className="mkp-sr">com</span> {combo.product_name}
                  </p>
                  <p className="mkp-why">{combo.reason}</p>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {products.length ? (
          <section aria-labelledby="mkp-products-title" className="mkp-block">
            <h2 id="mkp-products-title">Produtos e com quais pães combinam</h2>
            <ul className="mkp-cards is-page">
              {products.map((item) => (
                <li key={item.id} className="mkp-card">
                  {item.photos[0] ? (
                    <img className="mkp-card-photo" src={item.photos[0]} alt={item.name} loading="lazy" />
                  ) : (
                    <span className="mkp-card-photo mkp-photo-empty" aria-hidden="true" />
                  )}
                  <div className="mkp-card-body">
                    <div className="mkp-card-head">
                      <h3>{item.name}</h3>
                      <p className="mkp-price">{formatCents(item.price_cents)}</p>
                    </div>
                    {item.description ? <p className="mkp-muted">{item.description}</p> : null}
                    {item.pairings?.length ? (
                      <ul className="mkp-pairs">
                        {item.pairings.map((pair) => (
                          <li key={pair.house_product_slug}>
                            Combina com <a href={breadHref(pair.house_product_slug)}>{pair.house_product_name ?? "pão da casa"}</a>
                            {pair.reason ? `: ${pair.reason}` : ""}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <p className="mkp-muted mkp-foot">
          Parceiros são escolhidos e avaliados pela Loja de Pães. Pães, focaccias e fermentação natural são sempre da casa.
        </p>
      </main>
    </StorefrontLayout>
  );
}
