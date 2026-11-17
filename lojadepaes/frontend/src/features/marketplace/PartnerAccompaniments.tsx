import { formatCents } from "../../lib/money";
import { PartnerBadge } from "./PartnerBadge";
import { PartnerPhoto } from "./PartnerPhoto";
import { deliveryLine, partnerHref, type BreadPartners } from "./publicApi";

type Props = {
  breadName: string;
  breadPriceCents: number | null;
  data: BreadPartners;
};

/** Produtos e combinações de parceiros que acompanham este pão. Só leitura nesta fase: a compra entra na fase 3. */
export function PartnerAccompaniments({ breadName, breadPriceCents, data }: Props) {
  if (!data.products.length && !data.combos.length) {
    return null;
  }
  return (
    <section className="mkp-section" aria-labelledby="mkp-title">
      <p className="eyebrow">Escolhidos pela casa</p>
      <h2 id="mkp-title">Dos nossos parceiros</h2>
      <p className="mkp-lead">Selecionados pela Loja de Pães para acompanhar este pão. Cada parceiro entrega o próprio produto.</p>

      {data.combos.length ? (
        <ul className="mkp-combos" aria-label="Combinações da casa">
          {data.combos.map((combo) => {
            const total =
              breadPriceCents === null ? null : breadPriceCents + combo.price_cents + (combo.freight_cents ?? 0);
            return (
              <li key={combo.id} className="mkp-combo">
                <p className="mkp-combo-kicker">Combinação da casa</p>
                <p className="mkp-combo-name">
                  {breadName} <span aria-hidden="true">+</span> <span className="mkp-sr">com</span> {combo.product_name}
                </p>
                {combo.partner ? <PartnerBadge partner={combo.partner} /> : null}
                <p className="mkp-why">{combo.reason}</p>
                <p className="mkp-price">
                  {total === null ? "Preço na página do parceiro" : `a partir de ${formatCents(total)}`}
                  <span className="mkp-muted"> · pão + {combo.product_name.toLowerCase()} + frete do parceiro</span>
                </p>
              </li>
            );
          })}
        </ul>
      ) : null}

      {data.products.length ? (
        <ul className="mkp-cards">
          {data.products.map((item) => (
            <li key={item.id} className="mkp-card">
              <PartnerPhoto className="mkp-card-photo" src={item.photos[0]} alt={item.name} lazy />
              <div className="mkp-card-body">
                {item.partner ? <PartnerBadge partner={item.partner} /> : null}
                <h3>{item.name}</h3>
                {item.why_pairs ? <p className="mkp-why">{item.why_pairs}</p> : null}
                <p className="mkp-price">{formatCents(item.price_cents)}</p>
                <p className="mkp-muted">{deliveryLine(item.delivery, formatCents)}</p>
                {item.partner ? (
                  <a className="mkp-link" href={partnerHref(item.partner.brand_slug)}>
                    Conhecer {item.partner.brand_name}
                  </a>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      <p className="mkp-muted mkp-foot">
        Seu pão segue na data da fornada. Produtos de parceiros chegam separados, pela entrega de cada um.
      </p>
    </section>
  );
}
