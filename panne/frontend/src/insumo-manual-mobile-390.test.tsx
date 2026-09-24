/**
 * Gate visual dirigido: telas novas de insumo/abertura/nota em 390 CSS px.
 * Não reabre a homologação funcional; cobre reflow, campos úteis e ausência de scale.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FISCAL_DOCUMENT_ID, ORG_A } from "./api/fixtures";
import { installApiMock } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

const css = readFileSync(path.resolve(path.dirname(fileURLToPath(import.meta.url)), "styles/app.css"), "utf8");

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

describe("CSS do caminho manual não estica o viewport", () => {
  it("recolhe chrome e campos sem transform: scale", () => {
    expect(css).not.toMatch(/transform\s*:\s*scale\s*\(/);
    expect(css).toMatch(/html\s*\{[^}]*overflow-x:\s*visible/s);
    expect(css).not.toMatch(/html\s*\{[^}]*overflow-x:\s*clip/s);
    expect(css).not.toMatch(/overflow-x:\s*clip/);
    expect(css).toMatch(/\.submenu\s*\{[^}]*flex-wrap:\s*wrap/s);
    expect(css).toMatch(/\.manual-path[\s\S]*?max-width:\s*min\(960px,\s*100%\)/);
    expect(css).toMatch(/@media \(max-width: 720px\)[\s\S]*\.manual-units\s*\{[\s\S]*grid-template-columns:\s*1fr/);
    const manualCss = css
      .split(/\/\*[\s\S]*?\*\//)
      .join("")
      .match(/\.manual-path[\s\S]*?(?=\n\.estoque-util|\n@media \(max-width: 960px\))/);
    expect(manualCss?.[0] ?? "").not.toMatch(/overflow-wrap:\s*anywhere/);
    expect(css).toMatch(/\.estoque-util[\s\S]*?overflow-wrap:\s*break-word/);
  });
});

describe("Telas novas em 390 CSS px", () => {
  beforeEach(() => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    stubViewport(390, 844);
  });

  it("consolidação deixa escolher destino, nota/lote, unidade e revisar", async () => {
    const user = userEvent.setup();
    await renderApp("/componentes/ingredientes/consolidar");

    expect(await screen.findByRole("heading", { name: "Consolidar insumo" })).toBeInTheDocument();
    expect(screen.getByLabelText("Organização ativa")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Submenu" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abrir Gigio" })).toBeInTheDocument();

    const destino = await screen.findByLabelText("Ingrediente de destino");
    await user.selectOptions(destino, "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee");
    expect(await screen.findByRole("checkbox", { name: /Associar Farinha de trigo especial 25 kg/ })).toBeInTheDocument();
    expect(screen.getByText(/Nota 352/)).toBeInTheDocument();
    expect(screen.getByText(/Lote LOT-ENS-001/)).toBeInTheDocument();

    await user.click(screen.getByRole("checkbox", { name: /Associar Farinha de trigo especial 25 kg/ }));
    expect(screen.getByLabelText(/Conteúdo de LOT-ENS-001/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Revisar antes de confirmar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar vínculos" })).toBeEnabled();
  });

  it("abertura empilha ingrediente, lugar, data, quantidade, unidade, custo e confirma", async () => {
    const user = userEvent.setup();
    await renderApp("/componentes/estoque/abertura");

    expect(await screen.findByRole("heading", { name: "Abrir saldo sem nota" })).toBeInTheDocument();
    expect(screen.getByLabelText("Ingrediente")).toBeInTheDocument();
    expect(screen.getByLabelText("Lugar")).toBeInTheDocument();
    expect(screen.getByLabelText("Data da contagem")).toBeInTheDocument();
    expect(screen.getByLabelText("Quantidade")).toBeInTheDocument();
    expect(screen.getByLabelText("Unidade")).toBeInTheDocument();
    expect(screen.getByLabelText("Custo desconhecido")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar abertura" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Confirmar abertura" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/Escolha o ingrediente/);

    await user.selectOptions(screen.getByLabelText("Ingrediente"), "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee");
    await user.selectOptions(screen.getByLabelText("Lugar"), "Almoxarifado Central");
    await user.type(screen.getByLabelText("Quantidade"), "2");
    await user.type(screen.getByPlaceholderText("Ex.: contagem física da despensa"), "contagem de ensaio");
    await user.click(screen.getByLabelText("Custo desconhecido"));
    await user.click(screen.getByLabelText(/Confirmo esta abertura/));
    await user.click(screen.getByRole("button", { name: "Confirmar abertura" }));
    expect(await screen.findByRole("status")).toHaveTextContent(/Abertura registrada/);
  });

  it("revisão fiscal em 390 expõe dados da nota e mantém Gigio fora do conteúdo", async () => {
    await renderApp(`/gestao/compras/entradas/${FISCAL_DOCUMENT_ID}`);

    expect(await screen.findByRole("heading", { name: /Nota/ })).toBeInTheDocument();
    expect(screen.getByText("Fornecedor")).toBeInTheDocument();
    expect(screen.getByText("Emissão")).toBeInTheDocument();
    const main = screen.getByRole("main");
    expect(main.textContent ?? "").toMatch(/Moinho Demo|Fornecedor/);
    expect(within(main).queryByRole("button", { name: "Abrir Gigio" })).toBeNull();
    expect(screen.getByRole("button", { name: "Abrir Gigio" })).toBeInTheDocument();
  });
});
