import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ORG_A, ORG_B, PLAN_ID, planDetailFixture, plansFixture } from "./api/fixtures";
import { formatProcessingOrder, PROCESSING_ORDER_HELP } from "./format";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

const UUID_RE = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

describe("R026-006 lista e detalhe de planejamento", () => {
  it("formatProcessingOrder explica a escala sem inventar faixas", () => {
    expect(formatProcessingOrder(50)).toBe("50 · relativa (1–99; padrão 50)");
    expect(formatProcessingOrder(null)).toBe("—");
  });

  it("lista com links reais, resumo operacional e Detalhe", async () => {
    installApiMock({
      "/production/plans": (url) => {
        if (url.pathname.includes(`/plans/${PLAN_ID}`)) return json(planDetailFixture);
        return json({
          items: [
            {
              ...plansFixture.items[0],
              public_code: "PLN-20260824-0004",
              items_summary: "Pão francês (Demo)",
              item_count: 1,
            },
            {
              ...plansFixture.items[0],
              id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2",
              public_code: "PLN-MULTI",
              items_summary: "Pão francês (Demo) e mais 1",
              item_count: 2,
            },
            {
              ...plansFixture.items[0],
              id: "cccccccc-cccc-cccc-cccc-ccccccccccc3",
              public_code: "PLN-EMPTY",
              items_summary: "Nenhum item planejado",
              item_count: 0,
            },
          ],
          next_cursor: null,
        });
      },
    });
    await renderApp("/planejamento");
    const user = userEvent.setup();

    expect(await screen.findByRole("heading", { name: "Planos" })).toBeInTheDocument();
    expect(await screen.findByText("Pão francês (Demo) e mais 1")).toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(within(table).getByText("Pão francês (Demo)")).toBeInTheDocument();
    expect(within(table).getByText("Nenhum item planejado")).toBeInTheDocument();
    expect(table.textContent).not.toMatch(UUID_RE);

    const code = screen.getByRole("link", { name: "Abrir detalhe do plano PLN-20260824-0004" });
    expect(code).toHaveAttribute("href", `/planejamento/${PLAN_ID}`);
    expect(screen.getByRole("link", { name: "Detalhe do plano PLN-20260824-0004" })).toHaveAttribute(
      "href",
      `/planejamento/${PLAN_ID}`,
    );

    code.focus();
    expect(code).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(await screen.findByRole("heading", { name: "PL-2026-0008" })).toBeInTheDocument();
    expect(screen.getAllByText("Pão francês").length).toBeGreaterThan(0);
    expect(screen.getByText("PAO-FR")).toBeInTheDocument();
    expect(screen.getByText("Massa")).toBeInTheDocument();
    expect(screen.getByText("12.000 g")).toBeInTheDocument();
    expect(screen.getByText("50 · relativa (1–99; padrão 50)")).toBeInTheDocument();
    expect(screen.getByText(PROCESSING_ORDER_HELP)).toBeInTheDocument();
  });

  it("ação Detalhe abre o plano sem depender do clique da linha", async () => {
    installApiMock();
    await renderApp("/planejamento");
    const user = userEvent.setup();
    const detail = await screen.findByRole("link", { name: `Detalhe do plano PL-2026-0008` });
    await user.click(detail);
    expect(await screen.findByRole("heading", { name: "PL-2026-0008" })).toBeInTheDocument();
  });

  it("troca de organização não mantém planos da org anterior", async () => {
    installApiMock({
      "/production/plans": (url) => {
        if (url.pathname.includes(`/plans/${PLAN_ID}`)) return json(planDetailFixture);
        if (url.pathname.includes(ORG_B)) return json({ items: [], next_cursor: null });
        return json(plansFixture);
      },
    });
    await renderApp("/planejamento");
    const user = userEvent.setup();
    expect(await screen.findByText("Pão francês")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    expect(await screen.findByText(/Nenhum plano nesta organização/)).toBeInTheDocument();
    expect(screen.queryByText("Pão francês")).not.toBeInTheDocument();
    expect(screen.queryByText("PL-2026-0008")).not.toBeInTheDocument();
  });

  it("detalhe enriquecido permanece legível após isolamento", async () => {
    installApiMock({
      [`/plans/${PLAN_ID}`]: (url) => {
        if (url.pathname.includes(ORG_B)) {
          return json({ code: "nao_encontrado", message: "Plano indisponivel." }, 404);
        }
        return json({
          ...planDetailFixture,
          data: {
            ...planDetailFixture.data,
            public_code: "PLN-20260824-0004",
            items: [
              {
                ...planDetailFixture.data.items[0],
                target_quantity: "3300",
                product: {
                  id: "prod-1",
                  code: "PAO-FR",
                  display_name: "Pão francês (Demo)",
                },
              },
            ],
          },
        });
      },
    });
    const user = userEvent.setup();
    await renderApp(`/planejamento/${PLAN_ID}`);
    expect((await screen.findAllByText("Pão francês (Demo)")).length).toBeGreaterThan(0);
    expect(screen.getByText("3.300 g")).toBeInTheDocument();
    expect(screen.getByText("50 · relativa (1–99; padrão 50)")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    expect(await screen.findByRole("heading", { name: /Não foi possível carregar/ })).toBeInTheDocument();
    expect(screen.queryByText("Pão francês (Demo)")).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_A);
    expect((await screen.findAllByText("Pão francês (Demo)")).length).toBeGreaterThan(0);
  });
});
