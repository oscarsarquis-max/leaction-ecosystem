import { beforeEach, describe, expect, it } from "vitest";
import {
  buildBatch,
  clearDraft,
  draftKey,
  emptyRow,
  headerIssues,
  loadDraft,
  mapServerErrors,
  parseDate,
  parseNumber,
  parsePaste,
  parseUnit,
  rowIssues,
  saveDraft,
  summarize,
  summaryText,
  type BatchRow,
} from "./inventoryBatch";

const FARINHA = { id: "ing-farinha", display_name: "Farinha de trigo tipo 1" };
const ACUCAR = { id: "ing-acucar", display_name: "Açúcar cristal" };
const ingredients = [FARINHA, ACUCAR];
const items = [{ ingredient_id: FARINHA.id, unit_code: "kg" }];

function row(patch: Partial<BatchRow>): BatchRow {
  return { ...emptyRow(), ...patch };
}

describe("números, datas e unidades digitados à mão", () => {
  it("aceita vírgula, ponto de milhar e R$", () => {
    expect(parseNumber("4,80")).toBe(4.8);
    expect(parseNumber("R$ 1.234,50")).toBe(1234.5);
    expect(parseNumber("25")).toBe(25);
    expect(parseNumber("abc")).toBeNull();
    expect(parseNumber("")).toBeNull();
  });

  it("entende dia/mês/ano e data ISO, e recusa dia que não existe", () => {
    expect(parseDate("15/03/2027")).toBe("2027-03-15");
    expect(parseDate("2027-03-15")).toBe("2027-03-15");
    expect(parseDate("31/02/2027")).toBeNull();
    expect(parseDate("amanhã")).toBeNull();
  });

  it("reconhece unidades comuns e palavras de embalagem", () => {
    expect(parseUnit("KG")).toBe("kg");
    expect(parseUnit("Quilos")).toBe("kg");
    expect(parseUnit("g")).toBe("g");
    expect(parseUnit("pacote")).toBe("emb");
    expect(parseUnit("Caixa")).toBe("emb");
    expect(parseUnit("unidade")).toBe("un");
    expect(parseUnit("xyz")).toBeNull();
  });
});

describe("colar da planilha", () => {
  it("preenche nome, quantidade, unidade, validade e custo, e marca o que é novo", () => {
    const text = [
      "Farinha de trigo tipo 1\t25\tkg\t15/03/2027\t4,80",
      "Fermento biológico\t3\tpacote\t01/12/2026\t",
      "Sal marinho\t5\tkg",
    ].join("\r\n");
    const result = parsePaste(text, ingredients, items);
    expect(result.rows).toHaveLength(3);
    const [farinha, fermento, sal] = result.rows;
    expect(farinha.ingredientId).toBe(FARINHA.id);
    expect(farinha.isNew).toBe(false);
    expect(farinha.expires).toBe("2027-03-15");
    expect(farinha.cost).toBe("4,80");
    expect(fermento.isNew).toBe(true);
    expect(fermento.unit).toBe("emb");
    expect(sal.isNew).toBe(true);
    expect(sal.expires).toBe("");
  });

  it("pula a linha de títulos e aceita ponto e vírgula", () => {
    const result = parsePaste("Nome;Quantidade;Unidade\nAçúcar cristal;10;kg", ingredients, items);
    expect(result.skippedHeader).toBe(true);
    expect(result.rows).toHaveLength(1);
    expect(result.rows[0].ingredientId).toBe(ACUCAR.id);
  });

  it("usa a unidade de estoque do ingrediente quando a planilha não traz unidade", () => {
    const result = parsePaste("Farinha de trigo tipo 1\t12", ingredients, items);
    expect(result.rows[0].unit).toBe("kg");
  });

  it("guarda o aviso do campo que não deu para entender sem perder a linha", () => {
    const result = parsePaste("Sal\t2\tfurlong\t99/99/2027\tbarato", ingredients, items);
    const [only] = result.rows;
    expect(only.name).toBe("Sal");
    expect(only.issues.unit).toMatch(/não foi entendida/);
    expect(only.issues.expires).toMatch(/não foi entendida/);
    expect(only.issues.cost).toMatch(/não foi entendido/);
  });
});

describe("conferência antes de gravar", () => {
  const ctx = { items, today: "2026-11-02" };

  it("linha em branco não tem erro", () => {
    expect(rowIssues(emptyRow(), ctx)).toEqual({});
  });

  it("pede ingrediente, quantidade e unidade", () => {
    const issues = rowIssues(row({ name: "Sal", unit: "" }), ctx);
    expect(issues.ingredient).toMatch(/Criar/);
    expect(issues.quantity).toMatch(/Informe a quantidade/);
    expect(issues.unit).toMatch(/Escolha a unidade/);
  });

  it("exige o conteúdo da embalagem quando a unidade é embalagem", () => {
    const issues = rowIssues(row({ name: "Fermento", isNew: true, quantity: "3", unit: "emb" }), ctx);
    expect(issues.packQty).toMatch(/cada embalagem/);
    const ok = rowIssues(row({ name: "Fermento", isNew: true, quantity: "3", unit: "emb", packQty: "500" }), ctx);
    expect(ok.packQty).toBeUndefined();
  });

  it("avisa quando a unidade foge da que o estoque já usa", () => {
    const issues = rowIssues(row({ ingredientId: FARINHA.id, name: FARINHA.display_name, quantity: "2", unit: "g" }), ctx);
    expect(issues.unit).toMatch(/controlado em quilos/);
  });

  it("confere local, data e motivo do topo", () => {
    expect(headerIssues({ locationId: "", date: "", reason: "" }, "2026-11-02")).toMatchObject({
      location: expect.any(String),
      date: expect.any(String),
    });
    expect(headerIssues({ locationId: "x", date: "2026-12-01", reason: "" }, "2026-11-02").date).toMatch(/depois de hoje/);
    expect(headerIssues({ locationId: "x", date: "2026-11-02", reason: "Inventário inicial" }, "2026-11-02")).toEqual({});
  });
});

describe("resumo e envio", () => {
  const rows = [
    row({ ingredientId: FARINHA.id, name: FARINHA.display_name, quantity: "25", unit: "kg", expires: "2027-03-15", cost: "4,80" }),
    row({ name: "Sal marinho", isNew: true, quantity: "5", unit: "kg" }),
    row({ name: "sal marinho", isNew: true, quantity: "2", unit: "kg", lot: "L2" }),
    emptyRow(),
  ];

  it("conta itens, ingredientes novos (sem repetir o mesmo nome), sem custo e sem validade", () => {
    const summary = summarize(rows);
    expect(summary).toEqual({
      items: 3,
      newIngredients: 1,
      noCost: 2,
      noExpiry: 2,
      incomplete: 0,
      toDecide: 0,
      total: 120,
      withCost: 1,
    });
    expect(summaryText(summary)).toBe("3 itens · 1 ingrediente novo · 2 sem custo · 2 sem validade");
  });

  it("monta o pedido com custo desconhecido, sem validade e ingrediente novo", () => {
    const built = buildBatch({ locationId: "loc-1", date: "2026-11-02", reason: "" }, rows);
    expect(built.rowIds).toHaveLength(3);
    const body = built.body as { reason: string; counted_on: string; lines: Record<string, unknown>[] };
    expect(body.reason).toBe("Inventário inicial");
    expect(body.counted_on).toBe("2026-11-02");
    expect(body.lines[0]).toMatchObject({ ingredient_id: FARINHA.id, unit_cost: "4.8", cost_unknown: false, no_expiry: false });
    expect(body.lines[1]).toMatchObject({
      new_ingredient: { display_name: "Sal marinho", unit_code: "kg" },
      cost_unknown: true,
      unit_cost: null,
      no_expiry: true,
    });
    expect(body.lines[2]).toMatchObject({ lot_code: "L2" });
  });

  it("envia embalagem com o conteúdo de cada uma", () => {
    const pack = row({ name: "Fermento", isNew: true, quantity: "3", unit: "emb", packQty: "500", packUnit: "g" });
    const body = buildBatch({ locationId: "loc-1", date: "2026-11-02", reason: "Contagem" }, [pack]).body as {
      lines: Record<string, unknown>[];
    };
    expect(body.lines[0]).toMatchObject({
      unit_code: "embalagem",
      package_content_quantity: "500",
      package_content_unit: "g",
    });
  });

  it("liga cada erro da API à linha da tela e separa os do topo", () => {
    const mapped = mapServerErrors(
      [
        { index: 1, field: "quantity", code: "x", message: "Quantidade inválida." },
        { index: null, field: "counted_on", code: "y", message: "Data inválida." },
      ],
      ["a", "b", "c"],
    );
    expect(mapped.rows).toEqual({ b: { quantity: "Quantidade inválida." } });
    expect(mapped.general).toEqual(["Data inválida."]);
  });
});

describe("rascunho no navegador", () => {
  beforeEach(() => localStorage.clear());

  it("salva só as linhas preenchidas e volta igual", () => {
    const key = draftKey("org-1");
    const header = { locationId: "loc-1", date: "2026-11-02", reason: "Inventário inicial" };
    saveDraft(key, header, [row({ name: "Sal", isNew: true, quantity: "5", unit: "kg" }), emptyRow()]);
    const draft = loadDraft(key);
    expect(draft?.rows).toHaveLength(1);
    expect(draft?.rows[0].name).toBe("Sal");
    expect(draft?.header).toEqual(header);
    clearDraft(key);
    expect(loadDraft(key)).toBeNull();
  });

  it("não guarda rascunho vazio e ignora lixo", () => {
    const key = draftKey("org-1");
    saveDraft(key, { locationId: "", date: "", reason: "" }, [emptyRow()]);
    expect(localStorage.getItem(key)).toBeNull();
    localStorage.setItem(key, "{não é json");
    expect(loadDraft(key)).toBeNull();
  });
});
