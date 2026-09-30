import { describe, expect, it } from "vitest";
import { formatCpf, isValidCpf, parseDemoState } from "./houseFidelity";

describe("regras da fidelidade da casa", () => {
  it("formata e valida CPF sem aceitar sequência repetida", () => {
    expect(formatCpf("52998224725")).toBe("529.982.247-25");
    expect(isValidCpf("529.982.247-25")).toBe(true);
    expect(isValidCpf("111.111.111-11")).toBe(false);
    expect(isValidCpf("123")).toBe(false);
  });

  it("só aplica estados demonstrativos na prévia protegida", () => {
    expect(parseDemoState("credit", false)).toBe("visitor");
    expect(parseDemoState("parcial", true)).toBe("partial");
    expect(parseDemoState("credito", true)).toBe("credit");
    expect(parseDemoState("visitante", true)).toBe("visitor");
  });
});
