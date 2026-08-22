import { describe, expect, it } from "vitest";
import { hasCostLeak } from "./api/client";
import { boardFixture } from "./api/fixtures";

const sources = import.meta.glob("./**/*.{ts,tsx}", {
  query: "?raw",
  eager: true,
  import: "default",
}) as Record<string, string>;

describe("segurança e limites", () => {
  it("não usa HTML cru da API nem armazena token", () => {
    const text = Object.values(sources).join("\n");
    expect(text).not.toContain("dangerouslySetInnerHTML");
    expect(text).not.toMatch(/localStorage\.setItem\([^)]*token/i);
    expect(text.toLowerCase()).not.toContain("boto3");
    expect(text.toLowerCase()).not.toContain("cognito-identity");
    expect(text.toLowerCase()).not.toContain("bedrock");
  });

  it("não vaza custo nas projeções", () => {
    expect(hasCostLeak(boardFixture)).toBe(false);
  });
});
