import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ORG_A } from "./api/fixtures";
import { groupBalancesForOverview, overviewContextLabel } from "./language/inventory";
import { formatOperationalQuantity } from "./language/quantities";
import { installApiMock } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

describe("agrupamento da visão geral", () => {
  it("não soma unidades diferentes e marca embalagem sem conteúdo", () => {
    const groups = groupBalancesForOverview(
      [
        {
          inventory_item_id: "a",
          inventory_location_id: "l",
          inventory_lot_id: "1",
          item_label: "Farinha",
          location_label: "Loja",
          lot_code: "LOT-1",
          unit_code: "g",
          physical_quantity: "250",
          reserved_quantity: "0",
          impeded_quantity: "0",
          eligible_quantity: "250",
          production_eligible: true,
        },
        {
          inventory_item_id: "b",
          inventory_location_id: "l",
          inventory_lot_id: "2",
          item_label: "Farinha Caputo",
          location_label: "Loja",
          lot_code: "LOT-2",
          unit_code: "un",
          physical_quantity: "4",
          reserved_quantity: "0",
          impeded_quantity: "0",
          eligible_quantity: "4",
          production_eligible: true,
        },
      ],
      [{ id: "2", package_content_quantity: null }],
    );
    expect(groups).toHaveLength(2);
    expect(groups.find((row) => row.unit === "g")?.physical).toBe(250);
    expect(groups.find((row) => row.unit === "un")?.packageMissing).toBe(true);
    expect(overviewContextLabel(groups)).toBe("2 insumos em 2 lotes");
  });
});

describe("visão geral do Estoque — prévia útil", () => {
  it("mostra posição por insumo, lotes e em trânsito sem misturar unidades", async () => {
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
    expect(document.body.textContent).not.toMatch(/1500\.000000/);
    expect(screen.getAllByText(formatOperationalQuantity("1500", "g")).length).toBeGreaterThan(0);
  });

  it("expande lotes sem alterar os valores da linha", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/componentes/estoque");
    const farinha = (await screen.findAllByText("Farinha de trigo tipo 1"))[0];
    const row = farinha.closest("tr");
    expect(row).not.toBeNull();
    await user.click(within(row as HTMLElement).getByRole("button", { name: "Ver lotes" }));
    expect(screen.getByText(/LOT-000001/)).toBeInTheDocument();
    expect(within(row as HTMLElement).getByRole("button", { name: "Ocultar lotes" })).toBeInTheDocument();
    expect(screen.getAllByText("Farinha de trigo tipo 1").length).toBeGreaterThan(0);
  });
});
