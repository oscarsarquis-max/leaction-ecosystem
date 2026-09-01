/**
 * Contratos de layout por largura disponível (painel lateral / zoom).
 * Medição real de scrollWidth fica no script Playwright capture-028-narrow-viewport.mjs.
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

describe("Overflow por largura disponível (~500–520 / intermediárias)", () => {
  beforeEach(() => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
  });

  it("em 512px o fluxo expõe mapa, menu e Gigio sem depender de nav horizontal", async () => {
    stubViewport(512, 900);
    await renderApp("/fluxo");

    expect(await screen.findByRole("heading", { name: "Fluxo produtivo" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Menu" })).toBeInTheDocument();
    expect(document.querySelector(".fluxo-pin")).not.toBeNull();
    expect(screen.getAllByRole("link", { name: /Fluxo produtivo/i }).length).toBeGreaterThanOrEqual(1);

    const map = screen.getByRole("navigation", { name: "Etapas do fluxo produtivo" });
    expect(within(map).getAllByRole("button").length).toBeGreaterThanOrEqual(7);

    expect(
      screen.getByRole("button", { name: "Abrir Gigio" }),
    ).toBeInTheDocument();
  });

  it("em 1024px (painel + zoom) o pin de fluxo substitui a nav completa", async () => {
    stubViewport(1024, 768);
    await renderApp("/fluxo");

    expect(await screen.findByRole("heading", { name: "Fluxo produtivo" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Menu" })).toBeInTheDocument();
    expect(document.querySelector(".fluxo-pin")).not.toBeNull();
  });

  it("em 512px o mapa do caminho crítico está no DOM com track utilizável", async () => {
    stubViewport(512, 900);
    await renderApp("/fluxo");
    await screen.findByRole("heading", { name: "Fluxo produtivo" });
    const track = document.querySelector(".flow-map__track");
    expect(track).not.toBeNull();
    expect(track?.querySelectorAll(".flow-map__item").length).toBeGreaterThanOrEqual(7);
  });
});
