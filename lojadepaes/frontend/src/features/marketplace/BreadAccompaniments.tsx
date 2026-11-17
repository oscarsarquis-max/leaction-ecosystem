import { useEffect, useState } from "react";
import { ProductAccompaniments } from "../../shop/ProductAccompaniments";
import { PartnerAccompaniments } from "./PartnerAccompaniments";
import { fetchBreadPartners, type BreadPartners } from "./publicApi";
import "./marketplace-public.css";

type Props = {
  slug: string;
  breadName: string;
  breadPriceCents: number | null;
};

/**
 * "Para acompanhar este pão" na página do pão.
 * Marketplace desligado (rota 404) ou com erro: só a seção de hoje, sem mudança.
 * Ligado: parceiros primeiro; ofertas externas somem nas categorias que já têm parceiro.
 */
export function BreadAccompaniments({ slug, breadName, breadPriceCents }: Props) {
  const [partners, setPartners] = useState<BreadPartners | null>(null);

  useEffect(() => {
    let cancelled = false;
    setPartners(null);
    fetchBreadPartners(slug)
      .then((data) => {
        if (!cancelled && data && Array.isArray(data.products) && Array.isArray(data.combos)) {
          setPartners(data);
        }
      })
      .catch(() => {
        if (!cancelled) setPartners(null);
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  return (
    <>
      {partners ? <PartnerAccompaniments breadName={breadName} breadPriceCents={breadPriceCents} data={partners} /> : null}
      <ProductAccompaniments slug={slug} hideCategories={partners?.covered_categories ?? []} />
    </>
  );
}
