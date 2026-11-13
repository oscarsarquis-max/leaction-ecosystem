import { initials } from "./labels";
import type { Partner } from "./types";

type Props = {
  partner: Pick<Partner, "brand_name" | "highlight_hex" | "logo_url">;
  size?: "md" | "lg";
};

export function PartnerMark({ partner, size = "md" }: Props) {
  const className = size === "lg" ? "mkt-mark is-lg" : "mkt-mark";
  if (partner.logo_url) {
    return <img className={className} src={partner.logo_url} alt="" width={size === "lg" ? 56 : 40} height={size === "lg" ? 56 : 40} />;
  }
  return (
    <span className={className} style={{ background: partner.highlight_hex }} aria-hidden="true">
      {initials(partner.brand_name)}
    </span>
  );
}
