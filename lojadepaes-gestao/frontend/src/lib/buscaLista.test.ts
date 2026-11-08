import { describe, expect, it } from "vitest";
import { casaBusca, casaLote, rotuloItens, rotuloLotes } from "./buscaLista";

describe("busca da lista", () => {
  it("'-12' acha o lote E20261103-12 e não um 12 no meio da data", () => {
    expect(casaLote("-12", "E20261103-12")).toBe(true);
    expect(casaLote("E20261103-12", "E20261103-12")).toBe(true);
    expect(casaLote("-12", "E20261112-01")).toBe(false);
    expect(casaLote("-12", "E20261103-02")).toBe(false);
  });

  it("'fuba' acha Fubá Orgânico, sem acento e sem caixa", () => {
    expect(casaBusca("fuba", ["Fubá Orgânico"])).toBe(true);
    expect(casaBusca("FUBÁ", ["fuba organico"])).toBe(true);
    expect(casaBusca("fuba", ["Trigo Sarraceno"])).toBe(false);
  });

  it("a linha resume os itens e o intervalo de lotes", () => {
    expect(rotuloItens(["Fubá Orgânico", "Trigo Sarraceno", "Sal"])).toBe("Fubá Orgânico, Trigo Sarraceno e mais 1");
    expect(rotuloLotes(["E20261103-12", "E20261103-13", "E20261103-14"])).toBe("E20261103-12 a -14");
    expect(rotuloLotes(["E20261103-12"])).toBe("E20261103-12");
  });
});
