import { CATEGORIES, dayLabel, linkActive, linkTone, linkTypeLabel, periodLabel, todayIso } from "./labels";
import type { Partner, PartnerLink } from "./types";

type Props = {
  partners: Partner[];
  onOpen: (id: string) => void;
};

const RULE: Record<string, string> = {
  exclusive: "Só este parceiro na categoria",
  partial: "Aparece primeiro; outros parceiros podem entrar",
  none: "Divide a categoria com outros parceiros",
};

export function LinksTable({ partners, onOpen }: Props) {
  const today = todayIso();
  const rows: Array<{ link: PartnerLink; partner: Partner }> = [];
  for (const partner of partners) {
    for (const link of partner.links ?? []) {
      if (linkActive(link.starts_on, link.ends_on, today) || link.starts_on > today) {
        rows.push({ link, partner });
      }
    }
  }
  return (
    <div className="mkt-links">
      <div className="admin-card mkt-table-wrap">
        <table className="mkt-table">
          <caption className="mkt-sr">Vínculos por categoria</caption>
          <thead>
            <tr>
              <th scope="col">Categoria</th>
              <th scope="col">Parceiro</th>
              <th scope="col">Vínculo</th>
              <th scope="col">Vigência</th>
              <th scope="col">Na harmonização</th>
            </tr>
          </thead>
          <tbody>
            {CATEGORIES.map(([key, label]) => {
              const own = rows.filter((row) => row.link.category === key);
              if (own.length === 0) {
                return (
                  <tr key={key}>
                    <th scope="row">{label}</th>
                    <td colSpan={4} className="mkt-muted" data-label="Situação">
                      Sem parceiro · ofertas externas, quando houver
                    </td>
                  </tr>
                );
              }
              return own.map(({ link, partner }, index) => (
                <tr key={link.id}>
                  {index === 0 ? (
                    <th scope="row" rowSpan={own.length}>
                      {label}
                    </th>
                  ) : null}
                  <td data-label="Parceiro">
                    <a
                      className="mkt-link"
                      href={`/admin/marketplace/parceiros/${partner.id}`}
                      onClick={(event) => {
                        event.preventDefault();
                        onOpen(partner.id);
                      }}
                    >
                      {partner.brand_name}
                    </a>
                  </td>
                  <td data-label="Vínculo">
                    <span className={`admin-chip ${linkTone(link.link_type)}`}>{linkTypeLabel(link.link_type)}</span>
                  </td>
                  <td data-label="Vigência">
                    {link.starts_on > today && !link.ends_on
                      ? `a partir de ${dayLabel(link.starts_on)}`
                      : periodLabel(link.starts_on, link.ends_on)}
                  </td>
                  <td data-label="Na harmonização">{RULE[link.link_type] ?? "—"}</td>
                </tr>
              ));
            })}
          </tbody>
        </table>
      </div>
      <p className="mkt-note">
        Ordem de preferência: exclusivo → parcial → sem exclusividade → ofertas do Mercado Livre e da Amazon, só onde não houver parceiro.
      </p>
    </div>
  );
}
