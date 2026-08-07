import { describe, expect, it } from "vitest";
import {
  humanizeQuestionPrompt,
  humanizeScopeLabel,
  isDemoOrTestQuestion,
} from "./humanizeAuditCopy";

describe("humanizeAuditCopy", () => {
  it("traduz rótulo de requisito inglês", () => {
    expect(
      humanizeScopeLabel("Requisito 4 — Context of the organization (ref)"),
    ).toBe("Cláusula 4 — Contexto da organização");
  });

  it("filtra perguntas de teste", () => {
    expect(isDemoOrTestQuestion("Q-TEST-01", "Test interview prompt")).toBe(true);
    expect(isDemoOrTestQuestion("Q-CTX-01", "Como a empresa define o contexto?")).toBe(
      false,
    );
  });

  it("suaviza prompt inglês sem código", () => {
    const out = humanizeQuestionPrompt(
      "Q-CTX-01",
      "How does the organization determine external and internal issues?",
    );
    expect(out).not.toMatch(/How does/);
    expect(out).toMatch(/empresa|cláusula/i);
  });
});
