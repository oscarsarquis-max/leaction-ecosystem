/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { statusLabel } from "./format";

const root = dirname(fileURLToPath(import.meta.url));
const tokens = readFileSync(join(root, "shell/tokens.css"), "utf8");
const chip = readFileSync(join(root, "orders/TrackChip.tsx"), "utf8");
const cards = readFileSync(join(root, "orders/QueueCards.tsx"), "utf8");

const toneTokens = [
  "--admin-stage-open-bg: #eceae6",
  "--admin-stage-open-ink: #3f3b36",
  "--admin-stage-accepted-bg: #fbefc7",
  "--admin-stage-accepted-ink: #6b5208",
  "--admin-stage-paid-bg: #dceaf7",
  "--admin-stage-paid-ink: #1f4f7a",
  "--admin-stage-prod-bg: #ddf0e1",
  "--admin-stage-prod-ink: #1e5e33",
  "--admin-stage-delivered-border: #cfc8bc",
  "--admin-stage-cancelled-bg: #f8dedb",
  "--admin-stage-cancelled-ink: #8a2a22",
  "--admin-stage-warn-bg: #fce9d6",
  "--admin-stage-warn-ink: #7a4210",
  "--admin-line-strong: #e2dcd2",
];

describe("contrato visual da etapa", () => {
  it("fixa as cores de tom nos tokens, não numa tabela da tela", () => {
    for (const token of toneTokens) {
      expect(tokens).toContain(token);
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

  it("o selo da trilha e o da etapa usam o que a API mandou", () => {
    expect(chip).toContain("track.label");
    expect(chip).toContain("track.tone");
    expect(chip).not.toContain("submitted");
    expect(chip).not.toContain("statusLabel");
    expect(cards).toContain("item.visible_label");
    expect(cards).not.toContain("statusLabel");
  });
});
