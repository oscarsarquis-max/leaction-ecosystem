import { describe, expect, it } from "vitest";
import { formatCents, lineTotalCents, parseBrlToCents, sumCents } from "./money";

describe("dinheiro", () => {
  it("converte 24,90 para 2490 centavos e soma em inteiros", () => {
    expect(parseBrlToCents("24,90")).toBe(2490);
    expect(parseBrlToCents("1.240,50")).toBe(124050);
    expect(formatCents(2490)).toBe("R$ 24,90");
    expect(lineTotalCents(2490, 2)).toBe(4980);
    expect(sumCents([2490, 3200])).toBe(5690);
  });

  it("rejeita formato inválido e zero", () => {
    expect(() => parseBrlToCents("24.90")).toThrow();
    expect(() => parseBrlToCents("0,00")).toThrow();
    expect(parseBrlToCents("")).toBeNull();
  });
});
