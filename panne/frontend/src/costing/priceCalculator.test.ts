import { describe, expect, it } from "vitest";
import {
  applyDesiredPrice,
  applyMarkupFactor,
  initFromCostBase,
} from "./priceCalculator";

describe("calculadora de preço", () => {
  it("recalcula preço e margem ao alterar markup", () => {
    const base = initFromCostBase({
      amount: "10",
      origin: "batch_total",
      originLabel: "Total",
      incomplete: false,
      initialMarkup: "2",
    });
    expect(base.price).toBe("20");
    expect(base.marginPercent).toBe("50");
    expect(base.marginMoney).toBe("10");

    const next = applyMarkupFactor(base, "2.5");
    expect(next.price).toBe("25");
    expect(next.markupFactor).toBe("2.5");
    expect(next.marginPercent).toBe("60");
    expect(next.marginMoney).toBe("15");
    expect(next.error).toBeNull();
  });

  it("recalcula markup e margem ao alterar preço desejado", () => {
    const base = initFromCostBase({
      amount: "12.5",
      origin: "sellable_unit",
      originLabel: "Vendável",
      incomplete: false,
      initialMarkup: "2",
    });
    const next = applyDesiredPrice(base, "20");
    expect(next.markupFactor).toBe("1.6");
    expect(next.marginPercent).toBe("37.5");
    expect(next.marginMoney).toBe("7.5");
  });

  it("trata custo ausente e zero sem inventar valor", () => {
    const absent = initFromCostBase({
      amount: null,
      origin: "absent",
      originLabel: "Ausente",
    });
    expect(absent.price).toBeNull();
    expect(absent.error).toMatch(/ausente/i);

    const zero = initFromCostBase({
      amount: "0",
      origin: "batch_total",
      originLabel: "Total",
    });
    expect(zero.error).toMatch(/inválido/i);
  });

  it("sinaliza custo incompleto e preço zero", () => {
    const partial = initFromCostBase({
      amount: "12.50",
      origin: "batch_total",
      originLabel: "Total parcial",
      incomplete: true,
      initialMarkup: "2",
    });
    expect(partial.warning).toMatch(/incompleto/i);
    expect(partial.price).toBe("25");

    const zeroPrice = applyDesiredPrice(partial, "0");
    expect(zeroPrice.error).toMatch(/divisão por zero|zero/i);
    expect(zeroPrice.marginPercent).toBeNull();
  });

  it("rejeita markup inválido", () => {
    const base = initFromCostBase({
      amount: "10",
      origin: "produced_unit",
      originLabel: "Produzida",
      incomplete: false,
    });
    const bad = applyMarkupFactor(base, "0");
    expect(bad.error).toMatch(/Markup inválido/i);
    expect(bad.price).toBeNull();
  });
});
