import { afterEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { meFixture, ORG_B } from "./api/fixtures";
import { config } from "./config";
import {
  aggregateBalancesByUnit,
  demoExpiryReferenceNote,
  formatExpiryCaption,
  inventoryOperationalDate,
  positionLotHref,
  resolveInventoryAsOf,
} from "./language/inventory";
import { formatOperationalQuantity } from "./language/quantities";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
  config.demoMode = false;
  config.demoAnchorDate = "2026-08-24";
});

describe("R026-009 elegibilidade de estoque", () => {
  it("agrega não reservado, impedido e elegível sem misturar unidades", () => {
    const totals = aggregateBalancesByUnit([
      {
        physical_quantity: "1500",
        reserved_quantity: "0",
        unreserved_quantity: "1500",
        eligible_quantity: "0",
        impeded_quantity: "1500",
        unit_code: "g",
      },
      {
        physical_quantity: "3800",
        reserved_quantity: "0",
        unreserved_quantity: "3800",
        eligible_quantity: "3800",
        impeded_quantity: "0",
        unit_code: "g",
      },
      {
        physical_quantity: "120",
        reserved_quantity: "10",
        unreserved_quantity: "110",
        eligible_quantity: "110",
        impeded_quantity: "0",
        unit_code: "un",
      },
    ]);
    const g = totals.find((row) => row.unit === "g");
    expect(g?.unreserved).toBe(5300);
    expect(g?.impeded).toBe(1500);
    expect(g?.eligible).toBe(3800);
    expect(g?.available).toBe(5300);
    expect(totals.find((row) => row.unit === "un")?.eligible).toBe(110);
  });

  it("resolve as_of da API e formata relativos sem relógio do navegador", () => {
    expect(resolveInventoryAsOf("2026-08-24")).toBe("2026-08-24");
    expect(resolveInventoryAsOf("invalid")).toBeNull();
    expect(resolveInventoryAsOf(undefined)).toBeNull();
    expect(inventoryOperationalDate(true, "2026-08-24", "2026-08-27")).toBe("2026-08-24");
    expect(inventoryOperationalDate(false, "2026-08-24", "2026-08-27")).toBe("2026-08-27");
    expect(formatExpiryCaption("2026-08-24", "2026-08-24")).toBe("24/08/2026 · vence hoje");
    expect(formatExpiryCaption("2026-08-25", "2026-08-24")).toBe("25/08/2026 · vence em 1 dia");
    expect(formatExpiryCaption("2026-08-27", "2026-08-24")).toBe("27/08/2026 · vence em 3 dias");
    expect(formatExpiryCaption("2026-08-23", "2026-08-24")).toBe("23/08/2026 · vencido há 1 dia");
    expect(formatExpiryCaption("2026-08-20", "2026-08-24")).toBe("20/08/2026 · vencido há 4 dias");
    expect(formatExpiryCaption(null, "2026-08-24")).toBe("Validade ausente");
    expect(formatExpiryCaption("2026-08-27", null)).toBe("27/08/2026");
    expect(demoExpiryReferenceNote(true, "2026-08-24")).toMatch(/Referência da demonstração: 24\/08\/2026/);
    expect(demoExpiryReferenceNote(false, "2026-08-24")).toBeNull();
    expect(positionLotHref("LOT-000004")).toBe("/componentes/estoque/posicao?lot=LOT-000004");
  });

  it("visão geral mostra não reservado, impedido e disponível para produção", async () => {
    installApiMock();
    await renderApp("/componentes/estoque");
    expect(await screen.findByRole("heading", { name: "Estoque" })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "Não reservado" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("heading", { name: "Impedido" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("heading", { name: "Disponível para produção" }).length).toBeGreaterThan(0);
    expect(screen.queryByRole("heading", { name: "Disponível" })).not.toBeInTheDocument();
  });

  it("posição marca lote bloqueado como impedido com elegível zero", async () => {
    installApiMock();
    await renderApp("/componentes/estoque/posicao");
    expect(await screen.findByText("LOT-000003")).toBeInTheDocument();
    expect(document.body.textContent).toMatch(/Impedido · Bloqueado/);
    expect(screen.getAllByText(formatOperationalQuantity("0", "g")).length).toBeGreaterThan(0);
  });

  it("demo usa as_of do payload na nota e LOT-000002 vence em 3 dias", async () => {
    config.demoMode = true;
    config.demoAnchorDate = "2099-01-01"; // âncora FE local divergente — UI deve ignorar
    installApiMock();
    await renderApp("/componentes/lotes");
    expect(await screen.findByRole("heading", { name: "Lotes e validade" })).toBeInTheDocument();
    expect(
      screen.getByText(/Referência da demonstração: 24\/08\/2026\. Os indicadores/),
    ).toBeInTheDocument();
    expect(document.body.textContent).toMatch(/27\/08\/2026 · vence em 3 dias/);
    const link001 = screen.getByRole("link", { name: /Abrir posição relacionada ao lote LOT-000001/ });
    const link003 = screen.getByRole("link", { name: /Abrir posição relacionada ao lote LOT-000003/ });
    expect(link001).toHaveAttribute("href", "/componentes/estoque/posicao?lot=LOT-000001");
    expect(link003).toHaveAttribute("href", "/componentes/estoque/posicao?lot=LOT-000003");
  });

  it("fora do demo não menciona data-âncora, mas ainda usa as_of da API nos relativos", async () => {
    config.demoMode = false;
    installApiMock();
    await renderApp("/componentes/lotes");
    expect(await screen.findByRole("heading", { name: "Lotes e validade" })).toBeInTheDocument();
    expect(screen.queryByText(/Referência da demonstração/)).not.toBeInTheDocument();
    expect(document.body.textContent).toMatch(/27\/08\/2026 · vence em 3 dias/);
  });

  it("URL ?lot= filtra, é visível e limpa", async () => {
    installApiMock();
    await renderApp("/componentes/estoque/posicao?lot=LOT-000003");
    expect(await screen.findByText(/Filtro: lote/)).toBeInTheDocument();
    expect(screen.getByText(/Filtro: lote/)).toHaveTextContent("LOT-000003");
    expect(screen.getByRole("caption")).toHaveTextContent("Posição do lote LOT-000003");
    expect(screen.queryByText("LOT-000001")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Limpar filtro" })).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Limpar filtro" }));
    expect(await screen.findByText("LOT-000001")).toBeInTheDocument();
    expect(screen.getAllByText("LOT-000003").length).toBeGreaterThan(0);
    expect(screen.queryByText(/Filtro: lote/)).not.toBeInTheDocument();
  });

  it("lote inexistente mostra vazio humano sem listar outros", async () => {
    installApiMock();
    await renderApp("/componentes/estoque/posicao?lot=LOT-INEXISTENTE");
    expect(await screen.findByText(/Lote LOT-INEXISTENTE não encontrado nesta organização/)).toBeInTheDocument();
    expect(screen.queryByText("LOT-000001")).not.toBeInTheDocument();
    expect(screen.queryByText("LOT-000003")).not.toBeInTheDocument();
  });

  it("isolamento Panne filtrado → Horizonte → Panne sem cruzamento", async () => {
    installApiMock({
      "/api/v1/me": () =>
        json({
          ...meFixture,
          associations: meFixture.associations.map((item) =>
            item.organization_id === ORG_B
              ? { ...item, permissions: [...item.permissions, "inventory.read"] }
              : item,
          ),
        }),
      [ORG_B]: (url, request) => {
        if (url.pathname.includes("/inventory/") && request.method === "GET") {
          return json({ items: [], as_of: "2026-08-24", timezone: "America/Sao_Paulo" });
        }
        return json({ data: [] });
      },
    });
    await renderApp("/componentes/estoque/posicao?lot=LOT-000003");
    expect(await screen.findByText(/Filtro: lote/)).toBeInTheDocument();
    expect(screen.getByText(/Filtro: lote/)).toHaveTextContent("LOT-000003");
    expect(screen.queryByText("LOT-000001")).not.toBeInTheDocument();

    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    expect(await screen.findByText(/Não há registros nesta organização/)).toBeInTheDocument();
    expect(screen.queryByText("LOT-000003")).not.toBeInTheDocument();
    expect(screen.queryByText(/Filtro: lote/)).not.toBeInTheDocument();

    const orgA = meFixture.associations[0].organization_id;
    await user.selectOptions(screen.getByLabelText("Organização ativa"), orgA);
    expect(await screen.findByText("LOT-000001")).toBeInTheDocument();
    expect(screen.getAllByText("LOT-000003").length).toBeGreaterThan(0);
    expect(screen.queryByText(/Filtro: lote/)).not.toBeInTheDocument();
  });

  it("lote de outra org na query não revela dados Panne", async () => {
    installApiMock({
      "/api/v1/me": () =>
        json({
          ...meFixture,
          associations: meFixture.associations.map((item) =>
            item.organization_id === ORG_B
              ? { ...item, permissions: [...item.permissions, "inventory.read"] }
              : item,
          ),
        }),
      [ORG_B]: (url, request) => {
        if (url.pathname.includes("/inventory/balances") && request.method === "GET") {
          return json({
            as_of: "2026-08-24",
            timezone: "America/Sao_Paulo",
            items: [
              {
                id: "bal-h",
                lot_code: "LOT-HORIZONTE",
                item_label: "Sal Horizonte",
                location_label: "Depósito H",
                lot_status: "available",
                physical_quantity: "10",
                reserved_quantity: "0",
                available_quantity: "10",
                unreserved_quantity: "10",
                eligible_quantity: "10",
                impeded_quantity: "0",
                production_eligible: true,
                unit_code: "g",
              },
            ],
          });
        }
        if (url.pathname.includes("/inventory/") && request.method === "GET") {
          return json({ items: [], as_of: "2026-08-24" });
        }
        return json({ data: [] });
      },
    });
    await renderApp("/componentes/estoque/posicao?lot=LOT-000003");
    expect(await screen.findByText(/Filtro: lote/)).toBeInTheDocument();

    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    expect(await screen.findByText("LOT-HORIZONTE")).toBeInTheDocument();
    expect(screen.queryByText("LOT-000003")).not.toBeInTheDocument();
    expect(screen.queryByText(/Filtro: lote/)).not.toBeInTheDocument();
  });
});
