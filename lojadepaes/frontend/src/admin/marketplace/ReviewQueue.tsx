import { Button } from "../shell/Button";
import { categoryLabel, houseName, partnerById, stampLabel } from "./labels";
import { Photo } from "./Photo";
import { ComboReviewCard } from "./ComboReview";
import type { Partner, PartnerProduct, ProductCombo } from "./types";
import { formatCents } from "../../lib/money";

type Props = {
  products: PartnerProduct[];
  combos?: ProductCombo[];
  allProducts?: PartnerProduct[];
  onComboDecided?: (message: string) => void;
  partners: Partner[];
  onOpen: (id: string) => void;
};

export function ReviewQueue({ products, combos = [], allProducts = [], onComboDecided = () => undefined, partners, onOpen }: Props) {
  if (products.length === 0 && combos.length === 0) {
    return (
      <div className="admin-card mkt-empty">
        <p className="mkt-empty-title">Nada esperando avaliação.</p>
        <p className="mkt-muted">Quando um parceiro enviar um produto, ele aparece aqui.</p>
      </div>
    );
  }
  const byId = partnerById(partners);
  const comboList = combos.length ? (
    <section className="mkt-queue-group" aria-labelledby="mkt-combos-title">
      <h2 id="mkt-combos-title" className="mkt-h2">
        Combinações <span className="mkt-muted">· {combos.length}</span>
      </h2>
      <ul className="mkt-combo-list">
        {combos.map((combo) => (
          <ComboReviewCard
            key={combo.id}
            combo={combo}
            partner={byId.get(combo.partner_id)}
            product={allProducts.find((row) => row.id === combo.partner_product_id)}
            onDecided={onComboDecided}
          />
        ))}
      </ul>
    </section>
  ) : null;
  if (products.length === 0) {
    return comboList;
  }
  return (
    <div className="mkt-stack">
    {combos.length ? (
      <h2 className="mkt-h2">
        Produtos <span className="mkt-muted">· {products.length}</span>
      </h2>
    ) : null}
    <ul className="mkt-queue" aria-label="Produtos esperando avaliação">
      {products.map((product) => {
        const partner = byId.get(product.partner_id);
        const photo = product.photos[0];
        const pairs = product.pairings.map((row) => houseName(row.house_product_slug, row.house_product_name));
        return (
          <li key={product.id} className="admin-card mkt-queue-card">
            {photo ? (
              <Photo className="mkt-queue-photo" src={photo} alt={product.name} />
            ) : (
              <div className="mkt-queue-photo is-empty" aria-hidden="true" />
            )}
            <div className="mkt-queue-body">
              <div className="mkt-queue-meta">
                <span className="admin-chip c-acc">
                  <span className="dot" aria-hidden="true" />
                  Em avaliação
                </span>
                {product.updated_at ? <span className="mkt-muted">enviado {stampLabel(product.updated_at)}</span> : null}
              </div>
              <h2 className="mkt-queue-title">{product.name}</h2>
              <p className="mkt-muted">
                {partner?.brand_name ?? "Parceiro"} · {categoryLabel(product.category)} · {formatCents(product.price_cents)}
              </p>
              <p className="mkt-queue-pairs">{pairs.length ? `Combina com: ${pairs.join(", ")}` : "Sem pão da casa indicado"}</p>
            </div>
            <Button variant="primary" onClick={() => onOpen(product.id)} aria-label={`Avaliar ${product.name}`}>
              Avaliar
            </Button>
          </li>
        );
      })}
    </ul>
    {comboList}
    </div>
  );
}
