import { describe, expect, it } from "vitest";
import { comboPrice } from "./comboPricing";

describe("comboPrice", () => {
  it("cliente paga os preços de face; o acordo sai do parceiro e entra na Loja", () => {
    const price = comboPrice(3600, [{ itemCents: 5800, freightCents: 1200 }]);
    expect(price.totalCents).toBe(11400);
    expect(price.houseCents).toBe(4650);
    expect(price.partnerCents).toEqual([6750]);
    expect(price.houseCents + price.partnerCents[0]).toBe(price.totalCents);
    expect(price.payments).toBe(2);
  });

  it("com dois parceiros, um acordo por parceiro e três pagamentos", () => {
    const price = comboPrice(3600, [
      { itemCents: 5800, freightCents: 1200 },
      { itemCents: 8900, freightCents: null, feeCents: 300 },
    ]);
    expect(price.totalCents).toBe(3600 + 800 + 7000 + 8900);
    expect(price.houseCents).toBe(3600 + 800 + 250 + 300);
    expect(price.partnerCents).toEqual([6750, 8600]);
    expect(price.payments).toBe(3);
  });
});
