import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "./api/errors";
import { ORG_B } from "./api/fixtures";
import {
  allergenPresenceLabel,
  formatAllergenLine,
  formatMoneyAmount,
  formatNutrientLine,
  formatPackageQuantity,
  globalSourcesSummary,
  ingredientIdentityLabel,
  ingredientTypeLabel,
  ingredientVersionLabel,
  nutrientStatusLabel,
} from "./language/ingredients";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

describe("R026-008 ingredientes operacionais", () => {
  it("catálogos humanos e formatação", () => {
    expect(ingredientIdentityLabel("active")).toBe("Ativa");
    expect(ingredientVersionLabel("published")).toBe("Publicada");
    expect(ingredientTypeLabel("simple")).toBe("Simples");
    expect(nutrientStatusLabel("measured")).toBe("Medido");
    expect(nutrientStatusLabel("below_loq")).toBe("Abaixo do limite de quantificação");
    expect(allergenPresenceLabel("contains")).toBe("Contém");
    expect(allergenPresenceLabel("may_contain")).toBe("Pode conter");
    expect(allergenPresenceLabel("not_declared")).toBe("Ausência conhecida");
    expect(
      formatNutrientLine({
        value: "10",
        value_status: "measured",
        nutrient: { name: "Proteína", code: "protein" },
        unit: { code: "g", symbol: "g" },
      }),
    ).toBe("Proteína: 10 g por 100 g · Medido");
    expect(
      formatNutrientLine({
        value: null,
        value_status: "below_loq",
        limit_of_quantification: "0.1",
        nutrient: { name: "Proteína", code: "protein" },
        unit: { code: "g", symbol: "g" },
        loq_unit: { code: "g", symbol: "g" },
      }),
    ).toContain("Abaixo do limite de quantificação");
    expect(
      formatAllergenLine({
        presence: "contains",
        evidence_note: "Fonte sintética de demonstração.",
        allergen: { name: "Glúten", code: "gluten" },
      }),
    ).toBe("Glúten · Contém · Fonte sintética de demonstração.");
    expect(formatPackageQuantity("25", { code: "kg", symbol: "kg" })).toBe("25 kg");
    expect(formatMoneyAmount("13.00", "BRL")).toMatch(/R\$\s*13,00/);
    expect(formatMoneyAmount("13.10", "BRL")).toMatch(/R\$\s*13,10/);
    expect(globalSourcesSummary(0)).toBe("Nenhuma fonte global disponível");
    expect(globalSourcesSummary(1)).toBe("1 fonte global disponível");
    expect(globalSourcesSummary(3)).toBe("3 fontes globais disponíveis");
  });

  it("lista com links e Detalhe; cancelamento não vira alerta", async () => {
    installApiMock();
    await renderApp("/componentes/ingredientes");
    expect(
      await screen.findByRole("link", { name: "Abrir detalhe de Farinha de trigo tipo 1" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Detalhe de Farinha de trigo tipo 1" })).toBeInTheDocument();
    expect(screen.queryByText("A consulta anterior foi substituída.")).not.toBeInTheDocument();
  });

  it("detalhe legível e origem técnica só na auditoria", async () => {
    installApiMock();
    await renderApp("/componentes/ingredientes/eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee");
    expect(await screen.findByText(/Proteína: Abaixo do limite/)).toBeInTheDocument();
    expect(screen.getByText(/Glúten · Contém/)).toBeInTheDocument();
    expect(screen.getByText("Versão sem fonte técnica associada.")).toBeInTheDocument();
    const completeness = screen.getByRole("heading", { name: "Completude" }).closest(".panel");
    expect(completeness?.textContent).not.toMatch(/origem:/i);
    expect(completeness?.textContent).not.toContain("ingredient_version.data_source_id");
    const audit = screen.getByText("Detalhes técnicos de auditoria").closest("details");
    expect(audit).toBeTruthy();
    expect(audit?.textContent).toContain("ingredient_version.data_source_id");
  });

  it("erro real continua visível; cancelamento é ignorado no alerta", async () => {
    installApiMock({
      "/ingredients/eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee": () => {
        throw new ApiError("cancelado", "A consulta anterior foi substituída.", 0);
      },
    });
    await renderApp("/componentes/ingredientes/eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee");
    await waitFor(() => {
      expect(screen.queryByText("A consulta anterior foi substituída.")).not.toBeInTheDocument();
    });
  });

  it("isolamento Panne → Horizonte limpa lista", async () => {
    installApiMock({
      [ORG_B]: (url, request) => {
        if (url.pathname.endsWith("/ingredients") && request.method === "GET") {
          return json({ items: [], total: 0, limit: 20, offset: 0 });
        }
        return json({ data: [] });
      },
    });
    await renderApp("/componentes/ingredientes");
    expect(await screen.findByText(/Farinha de trigo tipo 1/)).toBeInTheDocument();
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    expect(await screen.findByText("Não há ingredientes neste recorte.")).toBeInTheDocument();
  });

  it("isolamento no detalhe: Horizonte não herda nutrição/alergênico/compra", async () => {
    installApiMock({
      [ORG_B]: () => json({ code: "nao_encontrado", message: "Recurso não encontrado" }, 404),
    });
    await renderApp("/componentes/ingredientes/eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee");
    expect(await screen.findByText(/Proteína/)).toBeInTheDocument();
    expect(screen.getByText(/Glúten/)).toBeInTheDocument();
    expect(document.body.textContent).toContain("SKU-1");
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    expect(await screen.findByRole("heading", { name: /Não foi possível carregar|Recurso/i })).toBeInTheDocument();
    expect(screen.queryByText(/Glúten · Contém/)).not.toBeInTheDocument();
    expect(document.body.textContent).not.toContain("SKU-1");
  });
});
