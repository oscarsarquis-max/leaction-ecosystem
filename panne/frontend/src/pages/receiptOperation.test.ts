import { describe, expect, it } from "vitest";
import {
  canonicalUnit,
  invoiceSays,
  movementSentence,
  packageHintFromName,
  parseArrived,
  principalStockName,
  stockAmount,
  suggestControl,
} from "./receiptOperation";

describe("recebimento operacional", () => {
  it("narra só o que a nota trouxe e trata o conteúdo do nome como pista", () => {
    expect(
      invoiceSays({
        supplier_description: "Erva doce",
        invoiced_quantity: "1",
        unit_code: "UN",
        total_cost: "4.50",
        currency: "BRL",
      }),
    ).toBe("A nota diz: 1 unidade de Erva doce, total R$ 4,5.");
    expect(packageHintFromName("Erva doce")).toBeNull();
    expect(packageHintFromName("Erva doce 250g")).toEqual({ amount: 250, unit: "g" });
    expect(packageHintFromName("Caixa 12 x 250 g")).toBeNull();
  });

  it("sugere gramas quando há uma pista e embalagem quando não há", () => {
    const hinted = suggestControl({
      invoiceUnit: "UN",
      hint: { amount: 250, unit: "g" },
    });
    expect(hinted).toMatchObject({ unit: "g", content: "250", fromName: true, byPackage: false });
    const plain = suggestControl({ invoiceUnit: "UN", hint: null });
    expect(plain.byPackage).toBe(true);
    expect(plain.content).toBeNull();
    expect(suggestControl({ invoiceUnit: "KG", hint: null }).unit).toBe("KG");
    expect(canonicalUnit("UN")).toBe("un");
    expect(canonicalUnit("KG")).toBe("kg");
    expect(canonicalUnit("CX")).toBe("un");
  });

  it("aceita 1 UN na unidade do campo e não devolve texto", () => {
    expect(parseArrived("1 UN", "UN")).toEqual({ amount: 1, unit: "UN" });
    expect(parseArrived("1", "UN")).toEqual({ amount: 1, unit: "UN" });
    expect(parseArrived("1 g", "UN")).toBeNull();
    expect(stockAmount(1, "UN", "g", "250")).toBe(250);
    expect(movementSentence(1, "UN", "g", "250")).toBe("1 embalagem recebida → 250 g no estoque");
    expect(movementSentence(2, "KG", "KG", "")).toBe("2 KG no estoque");
  });

  it("nomeia o lugar a partir do estabelecimento, sem tratar o estabelecimento como local", () => {
    expect(principalStockName("Loja Central")).toBe("Estoque principal de Loja Central");
    expect(principalStockName("")).toBe("Estoque principal");
  });
});
