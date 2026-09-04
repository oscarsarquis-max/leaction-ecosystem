/**
 * Adendo: experiência mobile/tablet — apresentação Fluxo + Gigio + entradas fiscais.
 * Não altera lógica de orientação; cobre layout, toque e não-sobreposição do avatar.
 */
import { screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ORG_A } from "./api/fixtures";
import { installApiMock } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

function stubViewport(width: number, height: number) {
  Object.defineProperty(window, "innerWidth", { configurable: true, value: width });
  Object.defineProperty(window, "innerHeight", { configurable: true, value: height });
  window.matchMedia = ((query: string) => {
    const max = /max-width:\s*(\d+)px/.exec(query);
    const min = /min-width:\s*(\d+)px/.exec(query);
    let matches = true;
    if (max) matches = matches && width <= Number(max[1]);
    if (min) matches = matches && width >= Number(min[1]);
    return {
      matches,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    } as MediaQueryList;
  }) as typeof window.matchMedia;
}

describe("Experiência mobile e tablet — Fluxo + Gigio + entradas", () => {
  beforeEach(() => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
  });

  it("em celular o coach inicia recolhido e o avatar permanece acessível", async () => {
    stubViewport(390, 844);
    await renderApp("/gestao/compras/entradas");

    const coach = await screen.findByRole("complementary", { name: "Orientação do processo" });
    expect(coach).toHaveClass("is-collapsed");
    expect(within(coach).getByRole("button", { name: "Abrir" })).toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: "Abrir Gigio, assistente da Panne" }),
    ).toBeInTheDocument();
  });

  it("em tablet vertical o fluxo mostra Gigio editorial e trilho utilizável", async () => {
    stubViewport(768, 1024);
    await renderApp("/fluxo");

    expect(await screen.findByRole("heading", { name: "Fluxo produtivo" })).toBeInTheDocument();
    const gigioPanel = document.querySelector(".flow-gigio");
    expect(gigioPanel).not.toBeNull();
    expect(gigioPanel?.textContent ?? "").toMatch(/Pendência principal|etapa|Finalidade|Orientador/i);

    const rail = screen.getByRole("navigation", { name: "Etapas do fluxo produtivo" });
    const buttons = within(rail).getAllByRole("button");
    expect(buttons.length).toBeGreaterThanOrEqual(7);
  });

  it("entradas fiscais em celular expõem as quatro vias sem UUID cru", async () => {
    stubViewport(390, 844);
    await renderApp("/gestao/compras/entradas/nova");

    expect(await screen.findByRole("heading", { name: "Registrar entrada" })).toBeInTheDocument();
    for (const title of [
      "Preencher manualmente",
      "Importar XML",
      "Enviar PDF ou foto",
      "Buscar documentos da Fazenda",
    ]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    const main = screen.getByRole("main").textContent ?? "";
    expect(main).not.toMatch(
      /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/i,
    );
  });

  it("em tablet horizontal a trilha e o coach do fluxo permanecem no chrome", async () => {
    stubViewport(1024, 768);
    await renderApp("/produtos");

    expect(await screen.findByRole("navigation", { name: "Trilha do fluxo produtivo" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Fluxo produtivo/i }).length).toBeGreaterThanOrEqual(1);
    expect(
      await screen.findByRole("complementary", { name: "Orientação do processo" }),
    ).toBeInTheDocument();
  });

  it("em celular o avatar flutuante não cobre o CTA Registrar entrada", async () => {
    stubViewport(390, 844);
    await renderApp("/gestao/compras/entradas");

    const avatar = await screen.findByRole("button", {
      name: "Abrir Gigio, assistente da Panne",
    });
    const cta = await screen.findByRole("link", { name: "Registrar entrada" });
    const filtrar = screen.getByRole("button", { name: "Filtrar" });
    const a = avatar.getBoundingClientRect();
    for (const el of [cta, filtrar]) {
      const c = el.getBoundingClientRect();
      const overlaps =
        a.left < c.right && a.right > c.left && a.top < c.bottom && a.bottom > c.top;
      expect(overlaps).toBe(false);
    }
  });
});
