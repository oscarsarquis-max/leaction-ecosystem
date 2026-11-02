import { describe, expect, it } from "vitest";
import {
  costLabel,
  decisionFor,
  emptyRow,
  findSimilar,
  formatMoney,
  packageFromVolume,
  parsePaste,
  parseUnit,
  rowIssues,
  saveBlockers,
  summarize,
  summaryText,
  type BatchRow,
} from "./inventoryBatch";

const FARINHA = { id: "ing-farinha", display_name: "Farinha de trigo tipo 1" };
const ACUCAR = { id: "ing-acucar", display_name: "Açúcar cristal" };
const MANTEIGA = { id: "ing-manteiga", display_name: "Manteiga sem sal" };
const ingredients = [FARINHA, ACUCAR, MANTEIGA];
const ctx = { items: [], today: "2026-11-02", ingredients };

function row(patch: Partial<BatchRow>): BatchRow {
  return { ...emptyRow(), ...patch };
}

describe("ingrediente parecido", () => {
  it("acha o parecido sem acento nem caixa, por 'contém' ou por poucas letras de diferença", () => {
    expect(findSimilar("acucar cristalino", ingredients)?.id).toBe(ACUCAR.id);
    expect(findSimilar("CRISTAL", ingredients)?.id).toBe(ACUCAR.id);
    expect(findSimilar("Farinha", ingredients)?.id).toBe(FARINHA.id);
    expect(findSimilar("Manteiga", ingredients)?.id).toBe(MANTEIGA.id);
    expect(findSimilar("Açucar cristol", ingredients)?.id).toBe(ACUCAR.id);
  });

  it("nome igual depois de tirar acento e caixa não é 'parecido'", () => {
    expect(findSimilar("ACUCAR CRISTAL", ingredients)).toBeUndefined();
    expect(findSimilar("  açúcar   cristal ", ingredients)).toBeUndefined();
  });

  it("não inventa parecido para nome curto ou diferente", () => {
    expect(findSimilar("Ovo", ingredients)).toBeUndefined();
    expect(findSimilar("Fe", ingredients)).toBeUndefined();
    expect(findSimilar("Granola da casa", ingredients)).toBeUndefined();
    expect(findSimilar("Chocolate", ingredients)).toBeUndefined();
  });

  it("a linha fica 'a decidir' até escolher: nova confirmada ou ingrediente escolhido saem da decisão", () => {
    const typed = row({ name: "Manteiga", isNew: true, quantity: "2", unit: "kg" });
    expect(decisionFor(typed, ingredients)?.id).toBe(MANTEIGA.id);
    expect(decisionFor({ ...typed, confirmedNew: true }, ingredients)).toBeUndefined();
    expect(decisionFor({ ...typed, ingredientId: MANTEIGA.id }, ingredients)).toBeUndefined();
    expect(decisionFor(typed, [])).toBeUndefined();
    expect(decisionFor(row({ name: "Granola", isNew: true }), ingredients)).toBeUndefined();
  });

  it("a conferência da linha pede a escolha, citando o nome parecido", () => {
    const issues = rowIssues(row({ name: "Manteiga", isNew: true, quantity: "2", unit: "kg" }), ctx);
    expect(issues.ingredient).toMatch(/parecido: "Manteiga sem sal"/);
    expect(issues.ingredient).toMatch(/Usar este/);
    const decided = rowIssues(row({ name: "Manteiga", isNew: true, confirmedNew: true, quantity: "2", unit: "kg" }), ctx);
    expect(decided.ingredient).toBeUndefined();
  });

  it("colar deixa o parecido para decidir, sem trocar o nome sozinho", () => {
    const result = parsePaste("Manteiga\t2\tkg", ingredients, []);
    const [only] = result.rows;
    expect(only.ingredientId).toBe("");
    expect(only.name).toBe("Manteiga");
    expect(only.confirmedNew).toBe(false);
    expect(decisionFor(only, ingredients)?.id).toBe(MANTEIGA.id);
  });
});

describe("resumo com pendências, total e motivo para não gravar", () => {
  const rows = [
    row({ ingredientId: FARINHA.id, name: FARINHA.display_name, quantity: "25", unit: "kg", cost: "4,80" }),
    row({ ingredientId: ACUCAR.id, name: ACUCAR.display_name, quantity: "10", unit: "kg", cost: "R$ 3,5" }),
    row({ ingredientId: MANTEIGA.id, name: MANTEIGA.display_name, quantity: "2", unit: "un" }),
    row({ name: "Fermento", isNew: true, quantity: "3", unit: "emb", cost: "9,90" }),
    row({ name: "Manteiga", isNew: true, quantity: "1", unit: "kg" }),
    row({ name: "Granola", isNew: true, quantity: "4", unit: "kg" }),
  ];

  it("soma quantidade × custo só das linhas com custo e conta incompletas e a decidir", () => {
    const summary = summarize(rows, ctx);
    expect(summary.total).toBe(184.7);
    expect(summary.withCost).toBe(3);
    expect(summary.incomplete).toBe(1);
    expect(summary.toDecide).toBe(1);
    expect(summary.newIngredients).toBe(2);
    expect(summaryText(summary)).toBe(
      "6 itens · 2 ingredientes novos · 3 sem custo · 6 sem validade · 1 linha incompleta · 1 a decidir",
    );
  });

  it("uma linha só a decidir não conta como incompleta; as duas coisas contam nas duas", () => {
    const onlyDecide = summarize([row({ name: "Manteiga", isNew: true, quantity: "1", unit: "kg" })], ctx);
    expect(onlyDecide.toDecide).toBe(1);
    expect(onlyDecide.incomplete).toBe(0);
    const both = summarize([row({ name: "Manteiga", isNew: true, unit: "kg" })], ctx);
    expect(both.toDecide).toBe(1);
    expect(both.incomplete).toBe(1);
  });

  it("sem custo nenhum o total é zero e a linha sem custo não soma", () => {
    const summary = summarize([row({ name: "Granola", isNew: true, quantity: "4", unit: "kg" })], ctx);
    expect(summary.total).toBe(0);
    expect(summary.withCost).toBe(0);
    expect(formatMoney(1234.5).replace(/\s/g, " ")).toBe("R$ 1.234,50");
  });

  it("lista o motivo de cada bloqueio, e fica vazia quando pode gravar", () => {
    const blocked = saveBlockers(summarize(rows, ctx), { location: "Escolha o local do estoque." });
    expect(blocked.join(" | ")).toMatch(/1 linha incompleta/);
    expect(blocked.join(" | ")).toMatch(/1 a decidir/);
    expect(blocked.join(" | ")).toMatch(/Escolha o local/);
    expect(saveBlockers(summarize([], ctx), {})).toEqual(["Digite ou cole ao menos um item."]);
    const ok = summarize([rows[0]], ctx);
    expect(saveBlockers(ok, {})).toEqual([]);
  });
});

describe("custo pela unidade e litro/ml", () => {
  it("o rótulo do custo segue a unidade", () => {
    expect(costLabel("kg")).toBe("R$ por kg");
    expect(costLabel("g")).toBe("R$ por g");
    expect(costLabel("un")).toBe("R$ por unidade");
    expect(costLabel("emb")).toBe("R$ por embalagem");
  });

  it("entende l e ml na planilha e não deixa gravar nessas unidades", () => {
    expect(parseUnit("L")).toBe("l");
    expect(parseUnit("litros")).toBe("l");
    expect(parseUnit("ml")).toBe("ml");
    const issues = rowIssues(row({ name: "Leite", isNew: true, quantity: "2", unit: "l" }), ctx);
    expect(issues.unit).toMatch(/Lance como embalagem/);
  });

  it("'Lançar como embalagem' troca a unidade e guarda o conteúdo informado", () => {
    const liters = row({ name: "Leite", isNew: true, quantity: "2", unit: "l" });
    expect(packageFromVolume(liters, " 1 ")).toEqual({ unit: "emb", packQty: "1", packUnit: "l" });
    const mls = row({ name: "Essência", isNew: true, quantity: "3", unit: "ml" });
    expect(packageFromVolume(mls, "500")).toEqual({ unit: "emb", packQty: "500", packUnit: "ml" });
    const converted = { ...liters, ...packageFromVolume(liters, "1") };
    expect(rowIssues(converted, ctx).unit).toBeUndefined();
    expect(rowIssues(converted, ctx).packQty).toBeUndefined();
  });
});
