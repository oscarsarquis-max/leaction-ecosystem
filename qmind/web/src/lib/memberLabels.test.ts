import { describe, expect, it } from "vitest";
import { formatMemberOptionLabel, labelMembershipRole } from "@/lib/memberLabels";

describe("memberLabels", () => {
  it("prefers name and email over technical ids", () => {
    expect(
      formatMemberOptionLabel({
        display_name: "Ana Silva",
        email: "ana@oficina.example",
        roles: ["quality_manager"],
      }),
    ).toBe("Ana Silva (ana@oficina.example) — Gestor da qualidade");
  });

  it("falls back to email when name missing", () => {
    expect(
      formatMemberOptionLabel({
        display_name: null,
        email: "gestor@example.com",
        roles: ["org_admin"],
      }),
    ).toBe("gestor@example.com — Administrador");
  });

  it("never invents a uuid-looking label", () => {
    const label = formatMemberOptionLabel({
      display_name: "",
      email: "",
      roles: [],
    });
    expect(label).toBe("Membro sem identificação");
    expect(label).not.toMatch(/[0-9a-f]{8}/i);
  });

  it("labels membership roles in pt-BR", () => {
    expect(labelMembershipRole("consultant_auditor")).toBe("Consultor / auditor");
  });
});
