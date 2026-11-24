import { formatCents } from "../../lib/money";
import { PartnerBadge } from "./PartnerBadge";
import { PartnerPhoto } from "./PartnerPhoto";
import { COMBO_HOUSE_FREIGHT_CENTS, comboPrice } from "./comboPricing";
import { comboCheckoutHref } from "./comboApi";
import { deliveryLine, partnerHref, type BreadPartners } from "./publicApi";

function LockIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <rect x="5" y="11" width="14" height="10" rx="2" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

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
            const breadCents = combo.house_unit_price_cents ?? breadPriceCents;
            const price =
              breadCents == null
                ? null
                : comboPrice(breadCents, [{ itemCents: combo.price_cents, freightCents: combo.freight_cents }]);
            return (
              <li key={combo.id} className="mkp-combo">
                <p className="mkp-combo-kicker">Combinação da casa</p>
                <p className="mkp-combo-name">
                  {breadName} <span aria-hidden="true">+</span> <span className="mkp-sr">com</span> {combo.product_name}
                </p>
                {combo.partner ? <PartnerBadge partner={combo.partner} /> : null}
                <p className="mkp-why">{combo.reason}</p>
                {price ? (
                  <div className="mkp-combo-total">
                    <p className="mkp-combo-price">
                      <span className="mkp-combo-from">a partir de</span> {formatCents(price.totalCents)}
                    </p>
                    <p className="mkp-muted">já com as entregas</p>
                  </div>
                ) : (
                  <p className="mkp-price">Preço na página do parceiro</p>
                )}
                {price ? (
                  <dl className="mkp-combo-deliveries" aria-label="Entregas da combo">
                    <div>
                      <dt>Entrega do pão · Loja de Pães</dt>
                      <dd>{formatCents(COMBO_HOUSE_FREIGHT_CENTS)}</dd>
                    </div>
                    <div>
                      <dt>Entrega do parceiro · {combo.partner?.brand_name ?? "parceiro"}</dt>
                      <dd>{combo.freight_cents ? formatCents(combo.freight_cents) : "grátis"}</dd>
                    </div>
                  </dl>
                ) : null}
                {price ? (
                  <p className="mkp-combo-pay">
                    <LockIcon />
                    Você paga cada parte direto a quem entrega, em {price.payments} pagamentos pelo Mercado Pago.
                  </p>
                ) : null}
                {price ? (
                  <a className="mkp-combo-cta" href={comboCheckoutHref(combo.id)}>
                    Quero esta combo
                  </a>
                ) : null}
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
