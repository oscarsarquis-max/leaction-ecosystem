import { Button } from "../shell/Button";
import {
  categoryLabel,
  feeLabel,
  linkActive,
  linkTone,
  linkTypeLabel,
  partnerStatus,
  partnerTypeLabel,
  todayIso,
} from "./labels";
import { PartnerMark } from "./PartnerMark";
import type { Partner, PartnerProduct } from "./types";

type Props = {
  partners: Partner[];
  products: PartnerProduct[];
  onOpen: (id: string) => void;
  onInvite: () => void;
};

function ProductSummary({ rows }: { rows: PartnerProduct[] }) {
  if (rows.length === 0) {
    return <span className="mkt-muted">Nenhum ainda</span>;
  }
  const published = rows.filter((row) => row.status === "approved").length;
  const pending = rows.filter((row) => row.status === "pending").length;
  return (
    <span className="mkt-cell-lines">
      <span>
        {published} {published === 1 ? "publicado" : "publicados"}
      </span>
      {pending ? <span className="mkt-muted">{pending} em avaliação</span> : null}
    </span>
  );
}

export function PartnersTable({ partners, products, onOpen, onInvite }: Props) {
  if (partners.length === 0) {
    return (
      <div className="admin-card mkt-empty">
        <p className="mkt-empty-title">Nenhum parceiro ainda.</p>
        <p className="mkt-muted">Convide o primeiro produtor. Ele recebe um link para criar a senha e cadastrar os produtos.</p>
        <Button variant="primary" onClick={onInvite}>
          Convidar parceiro
        </Button>
      </div>
    );
  }
  const today = todayIso();
  return (
    <div className="admin-card mkt-table-wrap">
      <table className="mkt-table">
        <caption className="mkt-sr">Parceiros do marketplace</caption>
        <thead>
          <tr>
            <th scope="col">Parceiro</th>
            <th scope="col">Tipo</th>
            <th scope="col">Vínculo vigente</th>
            <th scope="col">Produtos</th>
            <th scope="col" className="mkt-num">
              Taxa por pedido
            </th>
            <th scope="col">Situação</th>
            <th scope="col">
              <span className="mkt-sr">Ação</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {partners.map((partner) => {
            const status = partnerStatus(partner.status);
            const links = (partner.links ?? []).filter((link) => linkActive(link.starts_on, link.ends_on, today));
            const own = products.filter((row) => row.partner_id === partner.id);
            return (
              <tr key={partner.id}>
                <td data-label="Parceiro">
                  <div className="mkt-brand">
                    <PartnerMark partner={partner} />
                    <div className="mkt-brand-text">
                      <strong>{partner.brand_name}</strong>
                      <span className="mkt-muted">
                        {partner.city} · {partner.region}
                      </span>
                    </div>
                  </div>
                </td>
                <td data-label="Tipo">{partnerTypeLabel(partner.partner_type)}</td>
                <td data-label="Vínculo vigente">
                  {links.length === 0 ? (
                    <span className="mkt-muted">Sem vínculo</span>
                  ) : (
                    <ul className="mkt-chips">
                      {links.map((link) => (
                        <li key={link.id} className="mkt-link-cell">
                          <span className={`admin-chip ${linkTone(link.link_type)}`}>{linkTypeLabel(link.link_type)}</span>
                          <span>{categoryLabel(link.category)}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </td>
                <td data-label="Produtos">
                  <ProductSummary rows={own} />
                </td>
                <td data-label="Taxa por pedido" className="mkt-num">
                  {feeLabel(partner.fee_cents)}
                </td>
                <td data-label="Situação">
                  <span className={`admin-chip ${status.tone}`}>
                    <span className="dot" aria-hidden="true" />
                    {status.label}
                  </span>
                </td>
                <td className="mkt-action">
                  <Button onClick={() => onOpen(partner.id)} aria-label={`Abrir ${partner.brand_name}`}>
                    Abrir
                  </Button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
