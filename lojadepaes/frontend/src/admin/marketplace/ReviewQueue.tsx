import { Button } from "../shell/Button";
import { categoryLabel, houseName, partnerById, stampLabel } from "./labels";
import type { Partner, PartnerProduct } from "./types";
import { formatCents } from "../../lib/money";

type Props = {
  products: PartnerProduct[];
  partners: Partner[];
  onOpen: (id: string) => void;
};

export function ReviewQueue({ products, partners, onOpen }: Props) {
  if (products.length === 0) {
    return (
      <div className="admin-card mkt-empty">
        <p className="mkt-empty-title">Nada esperando avaliação.</p>
        <p className="mkt-muted">Quando um parceiro enviar um produto, ele aparece aqui.</p>
      </div>
    );
  }
  const byId = partnerById(partners);
  return (
    <ul className="mkt-queue" aria-label="Produtos esperando avaliação">
      {products.map((product) => {
        const partner = byId.get(product.partner_id);
        const photo = product.photos[0];
        const pairs = product.pairings.map((row) => houseName(row.house_product_slug, row.house_product_name));
        return (
          <li key={product.id} className="admin-card mkt-queue-card">
            {photo ? (
              <img className="mkt-queue-photo" src={photo} alt="" loading="lazy" />
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
  );
}
