/**
 * Guardrail: preços praticados não inventam markup no cliente.
 */
import { describe, expect, it } from "vitest";
import type { PracticedPrice } from "./api/types";

function clientMarkupFromPrice(price: PracticedPrice): string | null {
  const cmp = price.comparison;
  if (!cmp?.allowed) return null;
  return cmp.markup_factor != null ? String(cmp.markup_factor) : null;
}

describe("economic honesty — practiced price comparison", () => {
  it("bloqueia markup quando sale_basis não informada (legado A–D)", () => {
    const price: PracticedPrice = {
      id: "p1",
      channel: "own_counter",
      amount: "8.90",
      status: "active",
      row_version: 1,
      justification: "demo",
      currency: "BRL",
      sale_basis: {
        informed: false,
        quantity: null,
        unit: null,
        label: null,
        status: "not_informed",
        status_label: "Base comercial do preço não informada",
      },
      comparison: {
        allowed: false,
        reason: "sale_basis_not_informed",
        reason_label: "Base comercial do preço não informada",
        markup_factor: null,
        margin_rate: null,
        margin_amount: null,
      },
    };
    expect(clientMarkupFromPrice(price)).toBeNull();
  });

  it("só exibe markup quando a API autoriza", () => {
    const price: PracticedPrice = {
      id: "p2",
      channel: "own_counter",
      amount: "10.00",
      status: "active",
      row_version: 1,
      justification: null,
      currency: "BRL",
      comparison: {
        allowed: true,
        reason: null,
        reason_label: null,
        markup_factor: "2.50000000",
        margin_rate: "0.60000000",
        margin_amount: "6.000000",
      },
    };
    expect(clientMarkupFromPrice(price)).toBe("2.50000000");
  });
});
