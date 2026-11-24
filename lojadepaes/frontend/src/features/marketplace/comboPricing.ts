/**
 * Preço da combo (decisões de 24/11/2026).
 *
 * - O cliente paga só os preços de face: pão + frete da Loja + item(ns) do parceiro + frete de cada parceiro.
 * - O pagamento é feito por parte: um para a Loja e um para cada parceiro.
 * - O acordo de comercialização (taxa por parceiro, hoje R$ 2,50) não aparece para o cliente: sai do valor de face
 *   do item do parceiro e entra no pagamento da Loja.
 *
 * Nesta fase o cálculo é só de exibição (marketplace desligado). O backend será a fonte no pedido da combo.
 */

/** Frete único da Loja na combo. */
export const COMBO_HOUSE_FREIGHT_CENTS = 800;
/** Acordo de comercialização padrão por parceiro (o parceiro pode ter outro valor em `fee_cents`). */
export const COMBO_DEFAULT_FEE_CENTS = 250;

export type ComboPartnerPart = {
  /** Preço de face do item do parceiro. */
  itemCents: number;
  /** Frete do parceiro (nulo quando o parceiro não informou). */
  freightCents: number | null;
  /** Acordo de comercialização do parceiro. */
  feeCents?: number;
};

export type ComboPrice = {
  /** O que o cliente paga no total (soma dos preços de face). */
  totalCents: number;
  /** Pagamento da Loja: pão + frete da Loja + acordos de todos os parceiros. */
  houseCents: number;
  /** Pagamento de cada parceiro, na mesma ordem: item + frete − acordo. */
  partnerCents: number[];
  /** Quantidade de pagamentos que o cliente faz. */
  payments: number;
};

export function comboPrice(breadCents: number, partners: ComboPartnerPart[]): ComboPrice {
  let house = breadCents + COMBO_HOUSE_FREIGHT_CENTS;
  let total = house;
  const partnerCents = partners.map((part) => {
    const fee = part.feeCents ?? COMBO_DEFAULT_FEE_CENTS;
    const face = part.itemCents + (part.freightCents ?? 0);
    total += face;
    house += fee;
    return face - fee;
  });
  return { totalCents: total, houseCents: house, partnerCents, payments: 1 + partners.length };
}
