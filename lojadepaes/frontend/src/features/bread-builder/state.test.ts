import { describe, expect, it } from "vitest";
import {
  bakerTip,
  canAdvanceEssence,
  canComplete,
  chosenIngredientIds,
  createInitialState,
  dateKey,
  earliestDate,
  formatCommercialLine,
  formatLoafPrice,
  goBack,
  goNext,
  inclusionWarning,
  prettyDate,
  receiptLines,
  summaryText,
  toggleExtra,
} from "./state";

describe("assistente de criação", () => {
  it("mantém massa, inclusões e forma ao voltar", () => {
    let state = createInitialState(new Date("2026-09-16T12:00:00"));
    state = {
      ...state,
      massId: "massa",
      massName: "Maturada (Long fermentation)",
      flourId: "f1",
      flourName: "Branca (Strong white)",
      extraIds: ["a", "b"],
      extraNames: ["Nozes", "Damasco"],
    };
    state = goNext(state);
    state = { ...state, shapeId: "forma", shapeName: "Pão de forma" };
    state = goNext(state);
    state = goBack(state);
    state = goBack(state);
    expect(state.step).toBe(0);
    expect(state.massName).toBe("Maturada (Long fermentation)");
    expect(state.flourName).toBe("Branca (Strong white)");
    expect(state.extraNames).toEqual(["Nozes", "Damasco"]);
    expect(chosenIngredientIds(state)).toEqual(["f1", "a", "b"]);
    state = goNext(state);
    state = goNext(state);
    expect(state.shapeName).toBe("Pão de forma");
  });

  it("só avança a essência com farinha e preparo", () => {
    let state = createInitialState(new Date("2026-09-16T12:00:00"));
    expect(canAdvanceEssence(state)).toBe(false);
    state = { ...state, massId: "prep" };
    expect(canAdvanceEssence(state)).toBe(false);
    state = { ...state, flourId: "flour" };
    expect(canAdvanceEssence(state)).toBe(true);
  });

  it("não conclui sem data", () => {
    let state = createInitialState(new Date("2026-09-16T12:00:00"));
    state = { ...state, massId: "massa", shapeId: "forma" };
    state = goNext(goNext(goNext(state)));
    expect(state.step).toBe(3);
    expect(canComplete(state)).toBe(false);
    expect(goNext(state).finished).toBe(false);
    state = { ...state, date: "2026-09-20" };
    expect(goNext(state).finished).toBe(true);
  });

  it("monta o resumo com peso, preço e ingrediente livre", () => {
    const earliest = earliestDate(new Date("2026-09-16T12:00:00"));
    const state = {
      ...createInitialState(new Date("2026-09-16T12:00:00")),
      step: 3 as const,
      massName: "Maturada (Long fermentation)",
      flourName: "Branca (Strong white)",
      extraNames: ["Alecrim"],
      freeText: "pepperoni",
      shapeName: "Rústico de cesto",
      date: dateKey(new Date(earliest.getFullYear(), earliest.getMonth(), earliest.getDate() + 1)),
      priceCents: 7000,
      weightGrams: 500,
      quantity: 2,
    };
    expect(summaryText(state)).toContain("Maturada");
    expect(summaryText(state)).toContain("Branca (Strong white)");
    expect(summaryText(state)).toContain("pepperoni");
    expect(summaryText(state)).toContain("Rústico de cesto");
    expect(formatLoafPrice(7000, 500)).toContain("500 g");
    expect(formatLoafPrice(7000, 500)).toContain("70,00");
    expect(formatCommercialLine(7000, 500).replace(/\u00a0/g, " ")).toBe(
      "Pão personalizado: 500 g · R$ 70,00 por unidade.",
    );
    const receipt = receiptLines(state);
    expect(receipt[0]).toBe("Branca (Strong white) · Maturada (Long fermentation)");
    expect(receipt[1]).toContain("Alecrim");
    expect(receipt[1]).toContain("pepperoni");
    expect(receipt[3]).toContain(prettyDate(state.date));
    expect(receipt[3]).toContain("2 ×");
  });

  it("alterna inclusões", () => {
    expect(toggleExtra([], "Nozes")).toEqual(["Nozes"]);
    expect(toggleExtra(["Nozes"], "Nozes")).toEqual([]);
    expect(bakerTip(3)).toContain("Muitos sabores");
  });

  it("avisa incompatibilidade sem remover a inclusão", () => {
    expect(
      inclusionWarning("massa-2", [
        { id: "a", name: "Nozes", compatible_dough_ids: ["massa-1"] },
        { id: "b", name: "Granola", compatible_dough_ids: [] },
      ]),
    ).toContain("Nozes");
    expect(
      inclusionWarning("massa-1", [{ id: "a", name: "Nozes", compatible_dough_ids: ["massa-1"] }]),
    ).toBe("");
  });
});
