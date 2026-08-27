import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ORDER_ID, ORG_B, meFixture, operatorMeFixture, ordersFixture, PLAN_ID } from "./api/fixtures";
import { formatTargetQuantity } from "./format";
import { canOfferFloorExecution, floorExecutionHint, FLOOR_EXECUTION_STATUSES } from "./orderListActions";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

const UUID_RE = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

const ownerMe = {
  ...meFixture,
  associations: meFixture.associations.map((item, index) =>
    index === 0
      ? {
          ...item,
          roles: ["owner", "production_manager"],
          permissions: [
            ...item.permissions,
            "production.weighing.record",
            "production.step.execute",
            "production.consumption.record",
          ],
        }
      : item,
  ),
  permissions: [
    ...meFixture.permissions,
    "production.weighing.record",
    "production.step.execute",
    "production.consumption.record",
  ],
};

describe("R026-003 lista de ordens legível", () => {
  it("formatTargetQuantity inclui unidade", () => {
    expect(formatTargetQuantity("3300", "mass")).toBe("3.300 g");
    expect(formatTargetQuantity("12", "units")).toBe("12 un");
  });

  it("matriz estado × Executar alinhada ao chão de fábrica", () => {
    const allow = () => true;
    const deny = () => false;
    expect([...FLOOR_EXECUTION_STATUSES].sort()).toEqual(
      ["in_progress", "in_weighing", "on_hold", "ready", "released"].sort(),
    );
    expect(canOfferFloorExecution("released", allow)).toBe(true);
    expect(canOfferFloorExecution("in_weighing", allow)).toBe(true);
    expect(canOfferFloorExecution("ready", allow)).toBe(true);
    expect(canOfferFloorExecution("in_progress", allow)).toBe(true);
    expect(canOfferFloorExecution("on_hold", allow)).toBe(true);
    expect(canOfferFloorExecution("draft", allow)).toBe(false);
    expect(canOfferFloorExecution("scheduled", allow)).toBe(false);
    expect(canOfferFloorExecution("completed", allow)).toBe(false);
    expect(canOfferFloorExecution("cancelled", allow)).toBe(false);
    expect(canOfferFloorExecution("short_closed", allow)).toBe(false);
    expect(canOfferFloorExecution("in_weighing", deny)).toBe(false);
    expect(floorExecutionHint("draft")).toBe("Aguardando programação");
    expect(floorExecutionHint("scheduled")).toBe("Aguardando liberação");
    expect(floorExecutionHint("completed")).toBe("Execução encerrada");
  });

  it("mostra nomes legíveis, unidade, links e execução para o proprietário", async () => {
    installApiMock({
      "/api/v1/me": () => json(ownerMe),
    });
    await renderApp("/ordens");
    const user = userEvent.setup();

    expect(await screen.findByRole("heading", { name: "Ordens" })).toBeInTheDocument();
    expect(await screen.findByText("Pão tradicional")).toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(within(table).getByText("Pão tradicional")).toBeInTheDocument();
    expect(within(table).getByText("PL-2026-0008")).toBeInTheDocument();
    expect(within(table).getByText("12.000 g")).toBeInTheDocument();
    expect(within(table).queryByText(PLAN_ID)).not.toBeInTheDocument();
    expect(table.textContent).not.toMatch(UUID_RE);

    const detail = screen.getByRole("link", { name: `Abrir detalhe da ordem OP-2026-0001` });
    expect(detail).toHaveAttribute("href", `/ordens/${ORDER_ID}`);
    expect(screen.getByRole("link", { name: `Executar ordem OP-2026-0001` })).toHaveAttribute(
      "href",
      `/producao/ordens/${ORDER_ID}/executar`,
    );

    detail.focus();
    expect(detail).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(await screen.findByRole("heading", { name: "OP-2026-0001" })).toBeInTheDocument();
    expect(screen.getByText(/Pão tradicional/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "← Ordens" })).toHaveAttribute("href", "/ordens");
  });

  it("rascunho não oferece Executar; pesagem oferece", async () => {
    installApiMock({
      "/api/v1/me": () => json(ownerMe),
      "/production/orders": (url) => {
        if (url.pathname.endsWith("/orders")) {
          return json({
            items: [
              { ...ordersFixture.items[0], status: "draft", public_code: "ORD-DRAFT" },
              {
                ...ordersFixture.items[0],
                id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2",
                status: "in_weighing",
                public_code: "ORD-WEIGH",
              },
            ],
            next_cursor: null,
          });
        }
        return json({ data: ordersFixture.items[0], row_version: 4 });
      },
    });
    await renderApp("/ordens");
    expect(await screen.findByText("ORD-DRAFT")).toBeInTheDocument();
    expect(screen.getByText(/Aguardando programação/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Executar ordem ORD-DRAFT/ })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Executar ordem ORD-WEIGH/ })).toBeInTheDocument();
  });

  it("preserva filtro de estado ao voltar do detalhe", async () => {
    installApiMock({
      "/api/v1/me": () => json(ownerMe),
    });
    await renderApp("/ordens?status=in_progress");
    const user = userEvent.setup();
    const detail = await screen.findByRole("link", { name: `Abrir detalhe da ordem OP-2026-0001` });
    expect(detail).toHaveAttribute("href", `/ordens/${ORDER_ID}?from_status=in_progress`);
    await user.click(detail);
    expect(await screen.findByRole("link", { name: "← Ordens" })).toHaveAttribute(
      "href",
      "/ordens?status=in_progress",
    );
  });

  it("padeiro vê execução e não recebe custo na lista", async () => {
    installApiMock({
      "/api/v1/me": () => json(operatorMeFixture),
    });
    await renderApp("/ordens");
    expect(await screen.findByText("Pão tradicional")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: `Executar ordem OP-2026-0001` })).toBeInTheDocument();
    expect(document.body.textContent?.toLowerCase()).not.toMatch(/custo|preço|preco|margem/);
  });

  it("somente leitura não oferece Executar", async () => {
    installApiMock({
      "/api/v1/me": () =>
        json({
          ...meFixture,
          associations: meFixture.associations.map((item) => ({
            ...item,
            permissions: item.permissions.filter(
              (code) =>
                !code.startsWith("production.weighing") &&
                !code.startsWith("production.step") &&
                !code.startsWith("production.consumption") &&
                !code.startsWith("production.order.complete") &&
                !code.startsWith("production.order.short"),
            ),
          })),
          permissions: meFixture.permissions.filter(
            (code) =>
              !code.startsWith("production.weighing") &&
              !code.startsWith("production.step") &&
              !code.startsWith("production.consumption") &&
              !code.startsWith("production.order.complete") &&
              !code.startsWith("production.order.short"),
          ),
        }),
    });
    await renderApp("/ordens");
    expect(await screen.findByText("Pão tradicional")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: `Abrir detalhe da ordem OP-2026-0001` })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Executar ordem/ })).not.toBeInTheDocument();
    expect(screen.getByText(/Sem permissão para executar/)).toBeInTheDocument();
  });

  it("troca de organização não mostra ordens da org anterior", async () => {
    installApiMock({
      "/production/orders": (url) => {
        if (url.pathname.includes(ORG_B)) return json({ items: [], next_cursor: null });
        return json(ordersFixture);
      },
    });
    await renderApp("/ordens");
    const user = userEvent.setup();
    expect(await screen.findByText("Pão tradicional")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    expect(await screen.findByText(/Nenhuma ordem nesta organização/)).toBeInTheDocument();
    expect(screen.queryByText("Pão tradicional")).not.toBeInTheDocument();
    expect(screen.queryByText("OP-2026-0001")).not.toBeInTheDocument();
  });
});
