import { describe, expect, it } from "vitest";
import { contrastRatio, TOKEN_PAIRS } from "./styles/contrast";

describe("tokens e contraste", () => {
  it("mantém pares oficiais acima de AA 4.5:1", () => {
    for (const pair of TOKEN_PAIRS) {
      expect(contrastRatio(pair.fg, pair.bg), pair.name).toBeGreaterThanOrEqual(4.5);
    }
  });
});
