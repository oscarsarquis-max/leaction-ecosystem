import { describe, expect, it } from "vitest";
import { commercialLabels, lineMeasure } from "./draftMeasure";

describe("conta da linha da nota", () => {
  it("mostra 2 pacotes × 100 g = 200 g e o valor por pacote", () => {
    expect(
      lineMeasure({
        quantity: "2",
        unit: "pacote",
        content: "100",
        contentUnit: "g",
        price: "4,50",
      }).formula,
    ).toBe("2 pacotes × 100 g = 200 g no total · Valor da linha: R$ 9,00");
  });

  it("mostra 100 pacotes × 100 g = 10 kg", () => {
    expect(
      lineMeasure({
        quantity: "100",
        unit: "pacote",
        content: "100",
        contentUnit: "g",
        price: "5",
      }).formula,
    ).toBe("100 pacotes × 100 g = 10 kg no total · Valor da linha: R$ 500,00");
  });

  it("nomeia pacote sem pré-selecionar kg", () => {
    expect(commercialLabels("").quantity).toBe("Quantos foram comprados?");
    expect(commercialLabels("").price).toBe("Preço por embalagem (R$)");
    expect(commercialLabels("pacote").price).toBe("Preço por pacote (R$)");
  });
});
