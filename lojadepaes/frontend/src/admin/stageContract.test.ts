/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { statusLabel } from "./format";

const css = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "admin.css"), "utf8");
const list = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "OrdersList.tsx"), "utf8");

const stageColors: Array<[string, string]> = [
  ["open", "#eceae4"],
  ["accepted", "#f8e7a0"],
  ["paid", "#d7e6f6"],
  ["in-production", "#d7ecd6"],
  ["delivered", "#fff"],
  ["rejected", "#f8d6d2"],
  ["cancelled", "#f3eee8"],
  ["finalized", "#f7f4ee"],
  ["ready-legacy", "#f7f4ee"],
];

describe("contrato visual da etapa", () => {
  it("fixa a cor de cada classe de etapa no CSS atual", () => {
    for (const [stage, color] of stageColors) {
      const rule = css.split("}").find((part) => part.includes(`.admin-stage.is-${stage}`));
      expect(rule, stage).toBeTruthy();
      expect(rule).toContain(`background:${color}`);
    }
  });

  it("fixa os rótulos do status persistido, distintos da etapa visível", () => {
    expect(statusLabel("submitted")).toBe("Solicitado");
    expect(statusLabel("confirmed")).toBe("Confirmado");
    expect(statusLabel("in_production")).toBe("Em produção");
    expect(statusLabel("ready")).toBe("Pronto — aguardando confirmação de entrega");
    expect(statusLabel("completed")).toBe("Finalizado");
    expect(statusLabel("cancelled")).toBe("Cancelado");
    expect(statusLabel("draft")).toBe("Rascunho");
  });

  it("a lista usa o rótulo vindo da API e só cai no texto local sem visible_label", () => {
    expect(list).toContain("if (item.visible_label)");
    expect(list).toContain('return "Encomenda: Aguardando avaliação de A Loja"');
    expect(list).toContain('admin-stage is-${stage.replaceAll("_", "-")}');
  });
});
