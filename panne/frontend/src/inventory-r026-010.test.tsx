import { afterEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { meFixture, ORG_B } from "./api/fixtures";
import {
  formatSignedMovementQuantity,
  historicalAdoptionCaption,
  movementOriginLabel,
  movementTypeLabel,
} from "./language/inventory";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

describe("R026-010 reservas, movimentos e separação", () => {
  it("traduz tipos/origens e formata sinal da quantidade", () => {
    expect(movementTypeLabel("opening")).toBe("Abertura de saldo");
    expect(movementTypeLabel("supplier_return")).toBe("Devolução ao fornecedor");
    expect(movementOriginLabel("procurement_receipt")).toBe("Recebimento de compra");
    expect(movementOriginLabel("procurement_return")).toBe("Devolução de compra");
    expect(formatSignedMovementQuantity("4000", 1, "g")).toMatch(/^\+/);
    expect(formatSignedMovementQuantity("200", -1, "g")).toMatch(/^−/);
    expect(historicalAdoptionCaption(true)).toMatch(/histórico incorporado/i);
  });

  it("reservas: cada alocação tem link de posição distinto", async () => {
    installApiMock();
    await renderApp("/componentes/estoque/reservas");
    expect(await screen.findByRole("heading", { name: "Reservas" })).toBeInTheDocument();
    expect(screen.getAllByText("ORD-20260824-0004").length).toBeGreaterThan(0);
    expect(document.body.textContent).toMatch(/68\.500/);
    expect(screen.getAllByText(/Registro histórico incorporado/).length).toBeGreaterThan(0);
    const links002 = screen.getAllByRole("link", { name: /Abrir posição do lote LOT-000002/ });
    const links001 = screen.getAllByRole("link", { name: /Abrir posição do lote LOT-000001/ });
    expect(links002.length).toBeGreaterThan(0);
    expect(links001.length).toBeGreaterThan(0);
    expect(links002[0]).toHaveAttribute("href", "/componentes/estoque/posicao?lot=LOT-000002");
    expect(links001[0]).toHaveAttribute("href", "/componentes/estoque/posicao?lot=LOT-000001");
  });

  it("movimentos identificam item, lote, sinal e origem humana", async () => {
    installApiMock();
    await renderApp("/componentes/estoque/movimentacoes");
    expect(await screen.findByRole("heading", { name: "Movimentações" })).toBeInTheDocument();
    expect(screen.getAllByText("Farinha de trigo tipo 1").length).toBeGreaterThan(0);
    expect(screen.getAllByText("LOT-000001").length).toBeGreaterThan(0);
    expect(document.body.textContent).toMatch(/Abertura de saldo/);
    expect(document.body.textContent).toMatch(/Devolução ao fornecedor/);
    expect(document.body.textContent).toMatch(/Recebimento de compra/);
    expect(document.body.textContent).not.toMatch(/procurement receipt/i);
    expect(document.body.textContent).not.toMatch(/supplier return/i);
  });

  it("separação é leitura/impressão sem ação enganosa de confirmação", async () => {
    installApiMock();
    await renderApp("/componentes/estoque/separacao");
    expect(await screen.findByRole("heading", { name: "Separação" })).toBeInTheDocument();
    expect(
      screen.getByText(
        /Nesta demonstração, você pode consultar e imprimir separações já confirmadas/,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/ainda não está disponível nesta tela/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Confirmar separação/i })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Ordem \(código público\)/)).not.toBeInTheDocument();
    expect(screen.getAllByText("PICK-000001").length).toBeGreaterThan(0);
    expect(screen.getAllByText("ORD-20260824-0004").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Pão francês (Demo)").length).toBeGreaterThan(0);
    const printArea = document.querySelector(".pick-print-area");
    expect(printArea).toBeTruthy();
    expect(printArea?.textContent).toMatch(/PICK-000001/);
    expect(printArea?.textContent).toMatch(/ORD-20260824-0004/);
    expect(printArea?.textContent).toMatch(/Pão francês \(Demo\)/);
    expect(printArea?.textContent).toMatch(/Farinha de trigo tipo 1/);
    expect(printArea?.textContent).toMatch(/LOT-000001/);
    expect(printArea?.textContent).toMatch(/Almoxarifado Central/);
    expect(printArea?.textContent).toMatch(/Sugerido/);
    expect(printArea?.textContent).toMatch(/Conferência humana/);
    expect(screen.getByRole("button", { name: /Imprimir lista/i })).toBeInTheDocument();

    const surface = document.querySelector(".stage")?.textContent ?? "";
    for (const banned of [
      "POST",
      "/inventory/",
      "Idempotency-Key",
      "status=",
      "backend",
      "frontend",
      "payload",
      "UUID",
      "snake_case",
    ]) {
      expect(surface).not.toContain(banned);
    }
  });

  it("isolamento Panne → Horizonte limpa reservas", async () => {
    installApiMock({
      "/api/v1/me": () =>
        json({
          ...meFixture,
          associations: meFixture.associations.map((item) =>
            item.organization_id === ORG_B
              ? { ...item, permissions: [...item.permissions, "inventory.read", "inventory.separate"] }
              : item,
          ),
        }),
      [ORG_B]: (url, request) => {
        if (url.pathname.includes("/inventory/") && request.method === "GET") {
          return json({ items: [] });
        }
        return json({ data: [], items: [] });
      },
    });
    await renderApp("/componentes/estoque/reservas");
    expect(await screen.findByRole("heading", { name: "Reservas" })).toBeInTheDocument();
    expect(screen.getAllByText("ORD-20260824-0004").length).toBeGreaterThan(0);
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    expect(await screen.findByText(/Não há registros nesta organização/)).toBeInTheDocument();
    expect(screen.queryByText("ORD-20260824-0004")).not.toBeInTheDocument();
  });

  it("isolamento limpa separação e área de impressão", async () => {
    installApiMock({
      "/api/v1/me": () =>
        json({
          ...meFixture,
          associations: meFixture.associations.map((item) =>
            item.organization_id === ORG_B
              ? { ...item, permissions: [...item.permissions, "inventory.read", "inventory.separate"] }
              : item,
          ),
        }),
      [ORG_B]: (url, request) => {
        if (url.pathname.includes("/inventory/") && request.method === "GET") {
          return json({ items: [] });
        }
        return json({ data: [], items: [] });
      },
    });
    await renderApp("/componentes/estoque/separacao");
    expect(await screen.findByRole("heading", { name: "Separação" })).toBeInTheDocument();
    expect(screen.getAllByText("PICK-000001").length).toBeGreaterThan(0);
    expect(document.querySelector(".pick-print-area")).toBeTruthy();
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    expect(await screen.findByText(/Não há listas de separação/)).toBeInTheDocument();
    expect(screen.queryByText("PICK-000001")).not.toBeInTheDocument();
    expect(document.querySelector(".pick-print-area")).toBeNull();
  });
});
