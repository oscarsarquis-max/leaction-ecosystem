
import { describe, expect, it } from "vitest";
import { boardDefaultOperationalDate } from "./format";

describe("R026-002 data padrão do quadro", () => {
  it("usa a âncora no modo demo e hoje fora do demo", () => {
    expect(boardDefaultOperationalDate(true, "2026-08-24", "2026-08-27")).toBe("2026-08-24");
    expect(boardDefaultOperationalDate(false, "2026-08-24", "2026-08-27")).toBe("2026-08-27");
    expect(boardDefaultOperationalDate(true, "invalida", "2026-08-27")).toBe("2026-08-27");
  });
});
