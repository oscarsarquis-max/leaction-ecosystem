/**
 * Fórmulas econômicas — unitário, sem UI.
 */
import { describe, expect, it } from "vitest";
import {
  applyDesiredPrice,
  applyMarkupFactor,
  initFromCostBase,
} from "./costing/priceCalculator";
import { varianceSignal } from "./language/costing";
import { formatMoneyAmount } from "./language/ingredients";

function derive(cost: number, price: number) {
  return {
    markup: price / cost,
    acrescimo: (price - cost) / cost,
    margemPct: (price - cost) / price,
    margemMoney: price - cost,
  };
}

describe("fórmulas econômicas", () => {
  it("separa markup de margem (PAO-FR-like)", () => {
    const cost = 0.456647;
    const price = 0.9;
    const d = derive(cost, price);
    expect(d.markup).toBeCloseTo(1.9709, 3);
    expect(d.acrescimo).toBeCloseTo(0.9709, 3);
    expect(d.margemPct).toBeCloseTo(0.4926, 3);
    expect(d.margemMoney).toBeCloseTo(0.443353, 5);
    expect(d.markup).not.toBeCloseTo(d.margemPct, 2);
  });

  it("calculadora bidirecional markup ↔ preço", () => {
    const base = initFromCostBase({
      amount: "12.50",
      origin: "sellable_unit",
      originLabel: "custo unitário",
      incomplete: false,
      initialMarkup: "2",
    });
    const byMarkup = applyMarkupFactor(base, "3");
    expect(Number(byMarkup.price)).toBeCloseTo(37.5, 4);
    const byPrice = applyDesiredPrice(byMarkup, "30");
    expect(Number(byPrice.markupFactor)).toBeCloseTo(2.4, 4);
  });

  it("custo ausente não inventa markup", () => {
    const base = initFromCostBase({
      amount: null,
      origin: "absent",
      originLabel: "ausente",
      incomplete: true,
      initialMarkup: "2",
    });
    expect(base.costBase).toBeNull();
    expect(base.error || base.warning || base.incomplete).toBeTruthy();
  });

  it("variação: custo sobe = desfavorável; rendimento cai = desfavorável; iguais = neutro", () => {
    expect(varianceSignal("cost", "10", "12").label).toBe("desfavorável");
    expect(varianceSignal("cost", "10", "8").label).toBe("favorável");
    expect(varianceSignal("cost", "10", "10").label).toBe("neutro");
    expect(varianceSignal("yield", "8", "7").label).toBe("desfavorável");
    expect(varianceSignal("yield", "7", "8").label).toBe("favorável");
  });

  it("moeda BRL com 2 casas na superfície", () => {
    expect(formatMoneyAmount("27.398813", "BRL")).toMatch(/R\$\s*27,40/);
    expect(formatMoneyAmount("0.456647", "BRL")).toMatch(/R\$\s*0,46/);
    expect(formatMoneyAmount("18.00", "BRL")).not.toMatch(/,\d{3}/);
  });
});
