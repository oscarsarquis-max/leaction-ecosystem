import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ORG_A } from "./api/fixtures";
import {
  groupBalancesForOverview,
  overviewAvailableNote,
  overviewContextLabel,
  overviewLotSituation,
  overviewTransitCaption,
  unconfirmedPackageNotice,
} from "./language/inventory";
import { shouldStartCoachCollapsed } from "./fluxo/formRoutes";
import { formatOperationalQuantity } from "./language/quantities";
import { installApiMock, json } from "./test/fetchMock";
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

function balance(row: Record<string, unknown>) {
  return {
    reserved_quantity: "0",
    impeded_quantity: "0",
    eligible_quantity: row.physical_quantity,
    production_eligible: true,
    ...row,
  };
}

describe("agrupamento da visão geral", () => {
  it("não soma unidades diferentes e marca embalagem sem conteúdo", () => {
    const groups = groupBalancesForOverview(
      [
        balance({
          inventory_item_id: "a",
          inventory_location_id: "l",
          inventory_lot_id: "1",
          item_label: "Farinha",
          location_label: "Loja",
          lot_code: "LOT-1",
          unit_code: "g",
          physical_quantity: "250",
        }),
        balance({
          inventory_item_id: "b",
          inventory_location_id: "l",
          inventory_lot_id: "2",
          item_label: "Farinha Caputo",
          location_label: "Loja",
          lot_code: "LOT-2",
          unit_code: "un",
          physical_quantity: "4",
        }),
      ],
      [{ id: "2", package_content_quantity: null }],
    );
    expect(groups).toHaveLength(2);
    expect(groups.find((row) => row.unit === "g")?.physical).toBe(250);
    expect(groups.find((row) => row.unit === "un")?.packageMissing).toBe(true);
    expect(overviewContextLabel(groups)).toBe("2 insumos em 2 lotes");
  });

  it("conta dois cadastros com o mesmo nome como dois insumos e não funde saldos", () => {
    const groups = groupBalancesForOverview([
      balance({
        inventory_item_id: "item-caputo",
        inventory_location_id: "loja",
        inventory_lot_id: "lot-a",
        item_label: "Farinha Caputo",
        location_label: "Loja",
        lot_code: "LOT-A",
        unit_code: "kg",
        physical_quantity: "10",
      }),
      balance({
        inventory_item_id: "item-globo",
        inventory_location_id: "loja",
        inventory_lot_id: "lot-b",
        item_label: "Farinha Caputo",
        location_label: "Loja",
        lot_code: "LOT-B",
        unit_code: "kg",
        physical_quantity: "3",
      }),
    ]);
    expect(groups).toHaveLength(2);
    expect(groups.every((row) => row.itemLabel === "Farinha Caputo")).toBe(true);
    expect(new Set(groups.map((row) => row.itemId))).toEqual(new Set(["item-caputo", "item-globo"]));
    expect(groups.map((row) => row.physical).sort((a, b) => a - b)).toEqual([3, 10]);
    expect(overviewContextLabel(groups)).toBe("2 insumos em 2 lotes");
  });

  it("conta o mesmo cadastro em dois locais como um insumo e mantém as linhas", () => {
    const groups = groupBalancesForOverview([
      balance({
        inventory_item_id: "item-1",
        inventory_location_id: "loja",
        inventory_lot_id: "lot-loja",
        item_label: "Farinha",
        location_label: "Loja",
        lot_code: "LOT-LOJA",
        unit_code: "kg",
        physical_quantity: "8",
      }),
      balance({
        inventory_item_id: "item-1",
        inventory_location_id: "deposito",
        inventory_lot_id: "lot-dep",
        item_label: "Farinha",
        location_label: "Depósito",
        lot_code: "LOT-DEP",
        unit_code: "kg",
        physical_quantity: "2",
      }),
    ]);
    expect(groups).toHaveLength(2);
    expect(groups.map((row) => row.locationLabel).sort()).toEqual(["Depósito", "Loja"]);
    expect(new Set(groups.map((row) => row.itemId))).toEqual(new Set(["item-1"]));
    expect(groups.reduce((sum, row) => sum + row.physical, 0)).toBe(10);
    expect(overviewContextLabel(groups)).toBe("1 insumo em 2 lotes");
  });
});

describe("aviso de embalagem e trânsito", () => {
  it("avisa só o conteúdo ausente e não afirma receita verificada", () => {
    const missing = groupBalancesForOverview(
      [
        balance({
          inventory_item_id: "pkg",
          inventory_location_id: "l",
          inventory_lot_id: "lot-un",
          item_label: "Embalagens",
          location_label: "Loja",
          lot_code: "LOT-UN",
          unit_code: "un",
          physical_quantity: "4",
        }),
      ],
      [{ id: "lot-un", package_content_quantity: null }],
    );
    expect(unconfirmedPackageNotice(missing)).toBe(
      "Há 4 embalagens sem conteúdo declarado; para consumi-las em receita medida em massa/volume, confirme o conteúdo.",
    );
    expect(unconfirmedPackageNotice(missing)).not.toMatch(/cuja receita usa/);
    expect(overviewAvailableNote(missing[0])).toMatch(/consumo em massa\/volume bloqueado/);
    expect(overviewLotSituation(missing[0].lots[0])).toMatch(/livre no estoque/);
    expect(overviewLotSituation(missing[0].lots[0])).not.toBe("livre e elegível para produção");

    const declared = groupBalancesForOverview(
      [
        balance({
          inventory_item_id: "pkg",
          inventory_location_id: "l",
          inventory_lot_id: "lot-un",
          item_label: "Embalagens",
          location_label: "Loja",
          lot_code: "LOT-UN",
          unit_code: "un",
          physical_quantity: "4",
        }),
      ],
      [{ id: "lot-un", package_content_quantity: "25", package_content_unit: "kg" }],
    );
    expect(unconfirmedPackageNotice(declared)).toBeNull();
    expect(overviewAvailableNote(declared[0])).toBeNull();
    expect(overviewLotSituation(declared[0].lots[0])).toBe("livre e elegível para produção");
  });

  it("distingue trânsito desconhecido de vazio comprovado", () => {
    expect(overviewTransitCaption("unknown")).toBe(
      "Entradas em trânsito não são mostradas nesta posição. Consulte pedidos ou recebimentos.",
    );
    expect(overviewTransitCaption("empty")).toMatch(/Nenhuma entrada a caminho registrada/);
    expect(overviewTransitCaption("unavailable")).toMatch(/não significa que o saldo a caminho seja zero/);
  });
});

describe("visão geral do Estoque — prévia útil", () => {
  it("mostra posição por insumo, lotes e trânsito sem misturar unidades nem inventar zero", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/componentes/estoque");

    expect(await screen.findByRole("heading", { name: "Estoque" })).toBeInTheDocument();
    expect(screen.getByText("Posição atual")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver movimentos" })).toHaveAttribute(
      "href",
      "/componentes/estoque/movimentacoes",
    );
    expect(screen.getByRole("heading", { name: "O que está no estoque" })).toBeInTheDocument();
    expect(screen.getAllByText("Farinha de trigo tipo 1").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Embalagens").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Em trânsito" })).toBeInTheDocument();
    expect(screen.getByText(/Entradas em trânsito não são mostradas nesta posição/)).toBeInTheDocument();
    expect(screen.queryByText(/Nenhuma entrada a caminho registrada/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir pedidos" })).toHaveAttribute("href", "/gestao/compras/pedidos");
    expect(screen.getByRole("link", { name: "Abrir recebimentos" })).toHaveAttribute(
      "href",
      "/gestao/compras/recebimentos",
    );
    expect(document.body.textContent).not.toMatch(/1500\.000000/);
    expect(screen.getAllByText(formatOperationalQuantity("1500", "g")).length).toBeGreaterThan(0);
    expect(screen.getByText(/Há 120 embalagens sem conteúdo declarado/)).toBeInTheDocument();
    expect(screen.queryByText(/cuja receita usa/)).not.toBeInTheDocument();
  });

  it("não avisa embalagem quando o conteúdo está declarado", async () => {
    installApiMock({
      "/inventory/lots": () =>
        json({
          items: [
            {
              id: "lot-2",
              internal_lot_code: "LOT-000002",
              package_content_quantity: "25",
              package_content_unit: "kg",
              unit_code: "un",
            },
          ],
        }),
    });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/componentes/estoque");
    expect(await screen.findByRole("heading", { name: "Estoque" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Atenção sobre unidades" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Há \d+ embalagens sem conteúdo declarado/)).not.toBeInTheDocument();
  });

  it("expande lotes em lista legível sem alterar os valores da linha", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/componentes/estoque");
    const farinha = (await screen.findAllByText("Farinha de trigo tipo 1"))[0];
    const row = farinha.closest("tr");
    expect(row).not.toBeNull();
    const fisico = formatOperationalQuantity("3000", "g");
    expect(within(row as HTMLElement).getByText(fisico)).toBeInTheDocument();
    await user.click(within(row as HTMLElement).getByRole("button", { name: "Ver lotes" }));
    const detail = document.querySelector("#estoque-lotes-desktop-item-1-loc-1-g");
    expect(detail).not.toBeNull();
    expect(detail?.tagName).toBe("UL");
    expect(within(detail as HTMLElement).getByText("LOT-000001")).toBeInTheDocument();
    expect(within(detail as HTMLElement).getByText("LOT-000003")).toBeInTheDocument();
    expect(within(detail as HTMLElement).getAllByRole("listitem")).toHaveLength(2);
    expect(detail?.textContent).not.toMatch(/LOT-000001 · .* · LOT-000003/);
    expect(within(row as HTMLElement).getByRole("button", { name: "Ocultar lotes" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(within(row as HTMLElement).getByText(fisico)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Estoque" })).toBeInTheDocument();
  });

  it("oferece a mesma expansão de lotes no cartão em 390 px", async () => {
    stubViewport(390, 844);
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/componentes/estoque");
    expect(await screen.findByRole("heading", { name: "O que está no estoque" })).toBeInTheDocument();
    const mobile = document.querySelector(".estoque-util__mobile") as HTMLElement | null;
    expect(mobile).not.toBeNull();
    const card = within(mobile as HTMLElement).getAllByText("Farinha de trigo tipo 1")[0].closest("article");
    expect(card).not.toBeNull();
    const fisico = within(card as HTMLElement).getByText(/Físico/);
    const before = fisico.textContent;
    await user.click(within(card as HTMLElement).getByRole("button", { name: "Ver lotes" }));
    const list = document.querySelector("#estoque-lotes-mobile-item-1-loc-1-g");
    expect(list).not.toBeNull();
    expect(within(list as HTMLElement).getByText("LOT-000001")).toBeInTheDocument();
    expect(within(list as HTMLElement).getByText("LOT-000003")).toBeInTheDocument();
    expect(within(list as HTMLElement).getAllByText("Unidade g")).toHaveLength(2);
    expect(within(card as HTMLElement).getByRole("button", { name: "Ocultar lotes" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(fisico.textContent).toBe(before);
    expect(screen.getByRole("heading", { name: "Estoque" })).toBeInTheDocument();
  });
});

describe("orientação na visão geral do Estoque", () => {
  it("recolhe em /componentes/estoque sem tratar a rota como formulário", () => {
    stubViewport(1440, 900);
    expect(shouldStartCoachCollapsed("/componentes/estoque")).toBe(true);
    expect(shouldStartCoachCollapsed("/componentes/estoque/posicao")).toBe(false);
  });

  it("não abre o Gigio ao expandir lotes; só abre e fecha no acionador", async () => {
    stubViewport(390, 844);
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/componentes/estoque");
    expect(await screen.findByRole("heading", { name: "O que está no estoque" })).toBeInTheDocument();

    const coach = await screen.findByRole("complementary", { name: "Orientação do processo" });
    expect(coach).toHaveClass("is-collapsed");
    expect(coach).toHaveClass("flow-coach--form");
    expect(within(coach).queryByText(/Finalidade/)).not.toBeInTheDocument();

    const mobile = document.querySelector(".estoque-util__mobile") as HTMLElement;
    const card = within(mobile).getAllByText("Farinha de trigo tipo 1")[0].closest("article") as HTMLElement;
    await user.click(within(card).getByRole("button", { name: "Ver lotes" }));
    expect(within(card).getByRole("button", { name: "Ocultar lotes" })).toBeInTheDocument();
    expect(screen.getByText("LOT-000001")).toBeInTheDocument();
    expect(coach).toHaveClass("is-collapsed");
    expect(within(coach).queryByText(/Finalidade/)).not.toBeInTheDocument();

    const toggle = within(coach).getByRole("button", { name: "Abrir" });
    await user.click(toggle);
    expect(coach).toHaveClass("is-open");
    expect(within(coach).getByText(/Finalidade/)).toBeInTheDocument();
    expect(screen.getByText("LOT-000001")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(coach).toHaveClass("is-collapsed");
    expect(within(coach).getByRole("button", { name: "Abrir" })).toHaveFocus();
    expect(screen.getByText("LOT-000001")).toBeInTheDocument();
  });
});
