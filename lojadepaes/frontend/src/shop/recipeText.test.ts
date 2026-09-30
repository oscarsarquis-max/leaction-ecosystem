import { describe, expect, it } from "vitest";
import { ingredientsToText, methodTextToSteps, stepsToMethodText, textToIngredients } from "./recipeText";

describe("compatibilidade de texto da receita", () => {
  it("abre passos antigos como texto único sem inventar numeração", () => {
    const text = stepsToMethodText(["1. Misture a farinha", "2. Sove", "Leve ao forno"]);
    expect(text).toBe("1. Misture a farinha\n\n2. Sove\n\nLeve ao forno");
    expect(methodTextToSteps(text)).toEqual(["1. Misture a farinha", "2. Sove", "Leve ao forno"]);
  });

  it("salvar duas vezes não duplica parágrafos nem números", () => {
    const first = methodTextToSteps("1. Abrir o pão\n\n2. Rechear");
    const again = methodTextToSteps(stepsToMethodText(first));
    expect(again).toEqual(["1. Abrir o pão", "2. Rechear"]);
  });

  it("preserva ingredientes e ignora linhas vazias", () => {
    expect(textToIngredients("2 fatias\n\n  azeite  \n\n")).toEqual(["2 fatias", "azeite"]);
    expect(ingredientsToText(["2 fatias", "azeite"])).toBe("2 fatias\nazeite");
  });
});
