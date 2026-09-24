/**
 * Ajuste de uso nas telas novas: orientação recolhida e erro de abertura ao vivo.
 * Não reabre a homologação funcional já aprovada.
 */
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FISCAL_DOCUMENT_ID, ORG_A } from "./api/fixtures";
import { isManualFormRoute, shouldStartCoachCollapsed } from "./fluxo/formRoutes";
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

describe("rotas de formulário manual", () => {
  it("marca consolidar, abertura e revisão fiscal, e não a lista de entradas", () => {
    expect(isManualFormRoute("/componentes/ingredientes/consolidar")).toBe(true);
    expect(isManualFormRoute("/componentes/estoque/abertura")).toBe(true);
    expect(isManualFormRoute(`/gestao/compras/entradas/${FISCAL_DOCUMENT_ID}`)).toBe(true);
    expect(isManualFormRoute("/gestao/compras/entradas")).toBe(false);
    expect(isManualFormRoute("/gestao/compras/entradas/nova")).toBe(true);
    expect(isManualFormRoute("/componentes/estoque")).toBe(false);
    expect(shouldStartCoachCollapsed("/componentes/estoque")).toBe(true);
  });
});

describe("orientação recolhida nas telas novas", () => {
  beforeEach(() => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
  });

  for (const width of [390, 1440]) {
    for (const path of [
      "/componentes/ingredientes/consolidar",
      "/componentes/estoque/abertura",
      `/gestao/compras/entradas/${FISCAL_DOCUMENT_ID}`,
    ]) {
      it(`em ${width} px inicia recolhida em ${path}`, async () => {
        stubViewport(width, 844);
        expect(shouldStartCoachCollapsed(path)).toBe(true);
        await renderApp(path);
        const coach = await screen.findByRole("complementary", { name: "Orientação do processo" });
        expect(coach).toHaveClass("is-collapsed");
        expect(coach).toHaveClass("flow-coach--form");
        expect(within(coach).queryByText(/Finalidade/)).not.toBeInTheDocument();
        expect(within(coach).getByRole("button", { name: "Abrir" })).toBeVisible();
      });
    }
  }

  it("abre, cabe no fluxo, fecha com Escape e devolve o foco ao acionador", async () => {
    stubViewport(390, 844);
    const user = userEvent.setup();
    await renderApp("/componentes/estoque/abertura");
    const coach = await screen.findByRole("complementary", { name: "Orientação do processo" });
    const toggle = within(coach).getByRole("button", { name: "Abrir" });
    const quantidade = await screen.findByLabelText("Quantidade");

    await user.click(quantidade);
    await user.type(quantidade, "3");
    expect(quantidade).toHaveValue("3");

    await user.click(toggle);
    expect(coach).toHaveClass("is-open");
    expect(within(coach).getByText(/Finalidade/)).toBeInTheDocument();
    expect(within(coach).getByRole("button", { name: "Recolher" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Confirmar abertura" })).toBeVisible();

    await user.clear(quantidade);
    await user.type(quantidade, "4");
    expect(quantidade).toHaveValue("4");

    await user.keyboard("{Escape}");
    expect(coach).toHaveClass("is-collapsed");
    expect(within(coach).queryByText(/Finalidade/)).not.toBeInTheDocument();
    expect(within(coach).getByRole("button", { name: "Abrir" })).toHaveFocus();
    expect(quantidade).toHaveValue("4");
  });
});

describe("erro de abertura some ao corrigir o campo", () => {
  beforeEach(() => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    stubViewport(390, 844);
  });

  it("envio vazio mostra o erro; ingrediente e lugar corrigidos tiram a pendência antiga", async () => {
    const user = userEvent.setup();
    await renderApp("/componentes/estoque/abertura");

    await user.click(await screen.findByRole("button", { name: "Confirmar abertura" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Escolha o ingrediente deste saldo.");

    await user.selectOptions(screen.getByLabelText("Ingrediente"), "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee");
    expect(screen.queryByText("Escolha o ingrediente deste saldo.")).not.toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Escolha o lugar onde o saldo está.");
    expect(screen.getByLabelText("Ingrediente")).toHaveValue("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee");

    await user.selectOptions(screen.getByLabelText("Lugar"), "Almoxarifado Central");
    expect(screen.queryByText("Escolha o ingrediente deste saldo.")).not.toBeInTheDocument();
    expect(screen.queryByText("Escolha o lugar onde o saldo está.")).not.toBeInTheDocument();
    expect(screen.getByText(/Farinha de trigo tipo 1 em Almoxarifado Central/)).toBeInTheDocument();

    await user.type(screen.getByLabelText("Quantidade"), "2");
    await user.type(screen.getByPlaceholderText("Ex.: contagem física da despensa"), "contagem de ensaio");
    await user.click(screen.getByLabelText("Custo desconhecido"));
    await user.click(screen.getByLabelText(/Confirmo esta abertura/));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Confirmar abertura" }));
    expect(await screen.findByRole("status")).toHaveTextContent(/Abertura registrada/);
  });
});
