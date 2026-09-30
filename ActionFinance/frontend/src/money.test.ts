import { compactReference, formatDateBr, formatHistoryValue, formatMinor, formatStatusLabel, parseBrlInput } from "./money";

describe("money", () => {
  it("parses Brazilian decimals without float", () => {
    expect(parseBrlInput("1.234,56")).toEqual({ minor: "123456" });
    expect(parseBrlInput("")).toEqual({});
    expect(parseBrlInput("0,00").error).toMatch(/maior que zero/);
    expect(parseBrlInput("1,234").error).toBeDefined();
  });

  it("formats minor units", () => {
    expect(formatMinor("123456")).toBe("R$ 1.234,56");
    expect(formatMinor("0")).toBe("R$ 0,00");
    expect(formatMinor("-2500")).toBe("R$ -25,00");
    expect(formatMinor(null)).toBe("Não informado");
  });

  it("formats business dates and history values in Portuguese", () => {
    expect(formatDateBr("2026-09-15")).toBe("15/09/2026");
    expect(formatStatusLabel("OPEN")).toBe("Em aberto");
    expect(formatHistoryValue("amountMinor", "2500")).toBe("R$ 25,00");
    expect(formatHistoryValue("status", "DRAFT")).toBe("Rascunho");
    expect(compactReference("REC-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee").short).toBe("REC-eeeeeeee");
    expect(compactReference("PAG-11111111-cccc-4111-a111-111111111304").short).toBe("PAG-11111304");
    expect(compactReference("PAG-11111111-cccc-4111-a111-111111111305").short).toBe("PAG-11111305");
    expect(compactReference("PAG-11111111-cccc-4111-a111-111111111304").short).not.toBe(
      compactReference("PAG-11111111-cccc-4111-a111-111111111305").short,
    );
  });
});
