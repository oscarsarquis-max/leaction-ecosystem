import type { PublicPartnerBrand } from "./publicApi";
import { partnerHref } from "./publicApi";

function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter((word) => !/^(d[aeo]s?|e)$/i.test(word));
  const letters = words.length >= 2 ? words[0].charAt(0) + words[words.length - 1].charAt(0) : (words[0] ?? "").slice(0, 2);
  return letters.toUpperCase() || "?";
}

/** Selo "por <parceiro>": a marca do parceiro aparece pequena, dentro da moldura da Loja, com link para a página dele. */
export function PartnerBadge({ partner }: { partner: PublicPartnerBrand }) {
  return (
    <a className="mkp-badge" href={partnerHref(partner.brand_slug)}>
      {partner.logo_url ? (
        <img className="mkp-badge-mark" src={partner.logo_url} alt="" width={20} height={20} />
      ) : (
        <span className="mkp-badge-mark" style={{ background: partner.highlight_hex }} aria-hidden="true">
          {initials(partner.brand_name)}
        </span>
      )}
      <span>por {partner.brand_name}</span>
    </a>
  );
}

export function PartnerMarkLarge({ partner }: { partner: PublicPartnerBrand }) {
  if (partner.logo_url) {
    return <img className="mkp-mark-lg" src={partner.logo_url} alt="" width={56} height={56} />;
  }
  return (
    <span className="mkp-mark-lg" style={{ background: partner.highlight_hex }} aria-hidden="true">
      {initials(partner.brand_name)}
    </span>
  );
}

/** Marca média (36 px) para listas, como as partes da combo. */
export function PartnerMark({ partner }: { partner: PublicPartnerBrand }) {
  if (partner.logo_url) {
    return <img className="mkp-mark-md" src={partner.logo_url} alt="" width={36} height={36} />;
  }
  return (
    <span className="mkp-mark-md" style={{ background: partner.highlight_hex }} aria-hidden="true">
      {initials(partner.brand_name)}
    </span>
  );
}
