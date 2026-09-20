import { describe, expect, it } from "vitest";
import {
  bakerTip,
  canComplete,
  createInitialState,
  dateKey,
  earliestDate,
  goBack,
  goNext,
  prettyDate,
  receiptLines,
  summaryText,
  toggleExtra,
} from "./state";

describe("assistente de criação", () => {
  it("mantém massa, inclusões e forma ao voltar", () => {
    let state = createInitialState(new Date("2026-09-16T12:00:00"));
    state = { ...state, massIndex: 2, extras: ["Nozes", "Damasco"] };
    state = goNext(state);
    state = { ...state, shapeIndex: 1 };
    state = goNext(state);
    state = goBack(state);
    state = goBack(state);
    expect(state.step).toBe(0);
    expect(state.massIndex).toBe(2);
    expect(state.extras).toEqual(["Nozes", "Damasco"]);
    state = goNext(state);
    state = goNext(state);
    expect(state.shapeIndex).toBe(1);
  });

  it("não conclui sem data e horário", () => {
    let state = createInitialState(new Date("2026-09-16T12:00:00"));
    state = goNext(goNext(goNext(state)));
    expect(state.step).toBe(3);
    expect(canComplete(state)).toBe(false);
    const blocked = goNext(state);
    expect(blocked.finished).toBe(false);
    state = { ...state, date: "2026-09-20" };
    expect(goNext(state).finished).toBe(false);
    state = { ...state, time: "8h–10h" };
    expect(goNext(state).finished).toBe(true);
  });

  it("monta o resumo e o recibo com as escolhas", () => {
    const earliest = earliestDate(new Date("2026-09-16T12:00:00"));
    const state = {
      ...createInitialState(new Date("2026-09-16T12:00:00")),
      step: 3 as const,
      massIndex: 1,
      extras: ["Alecrim"],
      shapeIndex: 0,
      date: dateKey(new Date(earliest.getFullYear(), earliest.getMonth(), earliest.getDate() + 1)),
      time: "14h–16h",
    };
    expect(summaryText(state)).toContain("Integral");
    expect(summaryText(state)).toContain("Alecrim");
    expect(summaryText(state)).toContain("Rústico de cesto");
    expect(summaryText(state)).toContain("14h–16h");
    const receipt = receiptLines(state);
    expect(receipt[0]).toBe("Integral");
    expect(receipt[1]).toBe("Alecrim");
    expect(receipt[3]).toContain(prettyDate(state.date));
  });

  it("alterna inclusões e escolhe a dica correspondente", () => {
    expect(toggleExtra([], "Nozes")).toEqual(["Nozes"]);
    expect(toggleExtra(["Nozes"], "Nozes")).toEqual([]);
    expect(bakerTip(["Alecrim", "Damasco"])).toContain("damasco");
  });
});
