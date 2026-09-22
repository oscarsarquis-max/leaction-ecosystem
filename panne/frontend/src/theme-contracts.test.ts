/**
 * Contratos de tema/responsividade via leitura de CSS (Node).
 * Tema marrom/bege aprovado — verde rejeitado pelo proprietário.
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const tokens = readFileSync(resolve(__dirname, "styles/tokens.css"), "utf8");
const app = readFileSync(resolve(__dirname, "styles/app.css"), "utf8");
const printCss = readFileSync(resolve(__dirname, "styles/print.css"), "utf8");

describe("tema marrom — contratos CSS", () => {
  it("usa tokens marrom/bege literais (sem escala verde)", () => {
    expect(tokens).toMatch(/--panne-bege:\s*#e5e4d6/i);
    expect(tokens).toMatch(/--panne-espresso:\s*#49352a/i);
    expect(tokens).toMatch(/--panne-grafite:\s*#323334/i);
    expect(tokens).not.toMatch(/--panne-green-/);
    expect(app).not.toMatch(/--panne-green-/);
  });

  it("cabeçalho usa grafite; primary usa espresso", () => {
    expect(app).toMatch(/\.shell-header\s*\{[^}]*background:\s*var\(--panne-grafite\)/s);
    expect(app).toMatch(/\.primary\s*\{[^}]*background:\s*var\(--panne-espresso\)/s);
  });

  it("mapa responsivo sem min-width 9.5rem e sem overflow-x:clip", () => {
    expect(app).not.toMatch(/\.flow-map__item\s*\{[^}]*min-width:\s*9\.5rem/s);
    expect(app).toMatch(/minmax\(min\(100%,\s*10rem\),\s*1fr\)/);
    expect(app).not.toMatch(/overflow-x:\s*clip/);
  });

  it("em <=600px o cabeçalho fica numa linha compacta", () => {
    expect(app).toMatch(/@media \(max-width: 600px\)[\s\S]*?\.shell-header\s*\{[\s\S]*?flex-wrap:\s*nowrap/);
    expect(app).toMatch(/@media \(max-width: 600px\)[\s\S]*?\.shell-tools\s*\{[\s\S]*?flex-wrap:\s*nowrap/);
    expect(app).not.toMatch(/@media \(max-width: 600px\)[\s\S]*?\.shell-tools\s*\{[\s\S]*?flex:\s*1 1 100%/);
  });

  it("reserva o canto do Gigio no conteúdo móvel", () => {
    expect(app).toMatch(/\.shell > \.main[\s\S]*?padding-right:\s*max\(6rem/);
    expect(app).toMatch(/\.assistant-avatar\s*\{[\s\S]*?position:\s*fixed/);
  });

  it("impressão prioriza branco/preto", () => {
    expect(printCss).toMatch(/@media print/);
    expect(printCss).toMatch(/background:\s*#fff/);
    expect(printCss).toMatch(/color:\s*#111/);
  });
});
