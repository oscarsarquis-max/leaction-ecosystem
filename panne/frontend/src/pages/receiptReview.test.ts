import { describe, expect, it } from "vitest";
import { conversionPreview, factorIsUsable, purchaseCostCaption, receiptGaps } from "./receiptReview";
import type { FiscalDocument } from "../api/types";

describe("revisão da entrada", () => {
  it("separa o custo da nota e o custo da unidade de estoque", () => {
    const cost = purchaseCostCaption({
      invoiceUnitPrice: "4.50",
      invoiceUnit: "UN",
      stockUnitCost: "0.018000",
      stockUnit: "g",
      fallbackUnitCost: "0.018000",
      currency: "BRL",
    });
    expect(cost.note).toBe("R$ 4,5 por UN");
    expect(cost.stock).toBe("R$ 0,018 por g");
    expect(cost.stock).not.toContain("UN");
  });

  it("não inventa fator a partir do nome e exige fator quando a unidade muda", () => {
    expect(conversionPreview("1", "UN", "", "g")).toBeNull();
    expect(conversionPreview("1", "UN", "250", "g")).toBe("1 UN × 250 = 250 g");
    expect(factorIsUsable("UN", "g", "1")).toBe(false);
    expect(factorIsUsable("UN", "g", "250")).toBe(true);
    expect(factorIsUsable("kg", "KG", "")).toBe(true);
  });

  it("lista insumo, conteúdo, conferência e local enquanto a revisão está vazia", () => {
    const document = {
      items: [
        {
          id: "1",
          sequence: 1,
          supplier_description: "Pao",
          supplier_sku: null,
          invoiced_quantity: "1",
          unit_code: "UN",
          match: {
            status: "unmatched",
            target_kind: null,
            target_id: null,
            target_label: null,
            suggestion_reason: null,
          },
          physical: null,
        },
      ],
      divergence_count: 0,
      stock_applied: false,
    } as FiscalDocument;
    const gaps = receiptGaps({
      document,
      locationId: "",
      locationName: "",
      drafts: {
        "1": {
          creating: false,
          ingredientId: "",
          newName: "",
          stockUnit: "g",
          packageContent: "",
          receivedText: "",
          asExpected: true,
          issue: "",
        },
      },
    });
    expect(gaps.map((gap) => gap.key)).toEqual(["insumo-1", "conteudo-1", "chegou-1", "local"]);
    const done = receiptGaps({
      document: { ...document, stock_applied: true },
      locationId: "",
      drafts: {},
      acceptDivergence: false,
    });
    expect(done).toEqual([]);
  });
});
