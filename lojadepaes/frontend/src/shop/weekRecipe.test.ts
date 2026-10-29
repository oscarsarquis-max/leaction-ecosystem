import { describe, expect, it } from "vitest";
import { recipeImagePosition } from "./weekRecipe";

describe("recipeImagePosition", () => {
  it("aceita o foco publicado", () => {
    expect(recipeImagePosition("50% 50%")).toBe("50% 50%");
    expect(recipeImagePosition("49% 53%")).toBe("49% 53%");
    expect(recipeImagePosition(" 57% 62% ")).toBe("57% 62%");
  });

  it("recusa valor que não é ponto focal", () => {
    expect(recipeImagePosition("center")).toBeUndefined();
    expect(recipeImagePosition("sopa-de-cebolas")).toBeUndefined();
    expect(recipeImagePosition("")).toBeUndefined();
  });
});
