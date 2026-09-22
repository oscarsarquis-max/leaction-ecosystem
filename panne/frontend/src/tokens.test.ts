import { describe, expect, it } from "vitest";
import { contrastRatio, BROWN_SCALE, TOKEN_PAIRS } from "./styles/contrast";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const tokens = readFileSync(resolve(__dirname, "styles/tokens.css"), "utf8");

describe("tokens e contraste (tema marrom)", () => {
  it("mantém pares oficiais acima de AA 4.5:1", () => {
    for (const pair of TOKEN_PAIRS) {
      expect(contrastRatio(pair.fg, pair.bg), pair.name).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("expõe a escala marrom/bege aprovada", () => {
    expect(BROWN_SCALE.grafite).toBe("#323334");
    expect(BROWN_SCALE.bege).toBe("#e5e4d6");
    expect(BROWN_SCALE.espresso).toBe("#49352a");
  });

  it("não reintroduz a escala verde rejeitada", () => {
    expect(tokens).not.toMatch(/--panne-green-/);
    expect(tokens).toMatch(/--panne-espresso:\s*#49352a/i);
    expect(tokens).toMatch(/--panne-bege:\s*#e5e4d6/i);
  });
});
