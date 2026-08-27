import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ORG_A, ORG_B, RECIPE_ID, RECIPE_VERSION_ID } from "./api/fixtures";
import {
  formatBakersPercentage,
  formatScaleFactor,
  formatYieldSummary,
  recipeIdentityLabel,
  recipeTrialLabel,
} from "./language/recipes";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

function notFound() {
  return json({ code: "nao_encontrado", message: "Recurso não encontrado" }, 404);
}

describe("R026-007 receitas operacionais", () => {
  it("catálogo de estados e formatação operacional", () => {
    expect(recipeIdentityLabel("active")).toBe("Ativa");
    expect(recipeIdentityLabel("development")).toBe("Em desenvolvimento");
    expect(recipeIdentityLabel("retired")).toBe("Aposentada");
    expect(recipeTrialLabel("completed")).toBe("Concluído");
    expect(formatBakersPercentage("100")).toBe("100%");
    expect(formatBakersPercentage("65.00")).toBe("65%");
    expect(formatBakersPercentage("1.500")).toBe("1,5%");
    expect(formatScaleFactor("1.9584569733", 4)).toBe("1,9585");
    expect(formatYieldSummary({ yieldUnits: null, unitWeightG: null, lossRate: null })).toBe(
      "Rendimento não informado. Peso por unidade não informado. Perda não informada.",
    );
  });

  it("rendimento ausente não vira traços nem zero", async () => {
    installApiMock({
      "/recipes/": () =>
        json({
          data: {
            id: RECIPE_ID,
            code: "F-PAO-FR",
            display_name: "Pão francês (Demo)",
            status: "active",
            technical_product_id: "tp-1",
            row_version: 2,
            versions: [
              {
                id: RECIPE_VERSION_ID,
                formulation_id: RECIPE_ID,
                version_number: 1,
                status: "published",
                yield_units: null,
                target_unit_weight_g: null,
                expected_bake_loss_rate: null,
                notes: null,
                published_at: "2026-08-23T12:00:00Z",
                row_version: 2,
              },
            ],
            identity: {
              id: RECIPE_ID,
              code: "F-PAO-FR",
              display_name: "Pão francês (Demo)",
              status: "active",
              technical_product_id: "tp-1",
              row_version: 2,
              current_version: { id: RECIPE_VERSION_ID, version_number: 1, status: "published" },
            },
            version: {
              id: RECIPE_VERSION_ID,
              formulation_id: RECIPE_ID,
              version_number: 1,
              status: "published",
              yield_units: null,
              target_unit_weight_g: null,
              expected_bake_loss_rate: null,
              notes: null,
              published_at: "2026-08-23T12:00:00Z",
              row_version: 2,
            },
            items: [],
            steps: [],
            bakers: { flour_mass: null, explained_absence: true, items: [] },
            yield: {
              base_net_mass: null,
              yield_units: null,
              target_unit_weight_g: null,
              expected_bake_loss_rate: null,
              expected_final_mass_g: null,
              portion_mass_g: null,
            },
            completeness: { ready_to_publish: false, complete_dossier: false, items: [] },
          },
          row_version: 2,
        }),
      [`/recipes/${RECIPE_ID}/versions/${RECIPE_VERSION_ID}/scales`]: () => json({ data: [] }),
      [`/recipes/${RECIPE_ID}/versions/${RECIPE_VERSION_ID}/trials`]: () => json({ data: [] }),
    });
    await renderApp(`/receitas/${RECIPE_ID}`);
    expect(await screen.findByText(/Rendimento não informado/)).toBeInTheDocument();
    expect(screen.getByText(/Peso por unidade não informado/)).toBeInTheDocument();
    expect(screen.getByText(/Perda não informada/)).toBeInTheDocument();
    expect(screen.queryByText(/— unidades de — g/)).not.toBeInTheDocument();
  });

  it("troca de organização limpa a lista imediatamente", async () => {
    installApiMock({
      "/recipes": (url, request) => {
        if (!(url.pathname.endsWith("/recipes") && request.method === "GET")) {
          return notFound();
        }
        if (url.pathname.includes(ORG_B)) {
          return json({ items: [], total: 0, limit: 20, offset: 0 });
        }
        return json({
          items: [
            {
              id: RECIPE_ID,
              code: "F-PAO-FR",
              display_name: "Pão francês (Demo)",
              status: "active",
              technical_product_id: "tp-1",
              row_version: 1,
              current_version: { id: RECIPE_VERSION_ID, version_number: 1, status: "published" },
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
        });
      },
    });
    const user = userEvent.setup();
    await renderApp("/receitas");
    expect(await screen.findByText("Pão francês (Demo)")).toBeInTheDocument();
    expect(screen.getAllByText("Ativa").length).toBeGreaterThan(0);
    expect(screen.queryByText(/^active$/)).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    expect(await screen.findByText(/Nenhuma receita nesta organização/)).toBeInTheDocument();
    expect(screen.queryByText("Pão francês (Demo)")).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_A);
    expect(await screen.findByText("Pão francês (Demo)")).toBeInTheDocument();
  });

  it("detalhe limpa ao trocar de organização", async () => {
    const dossier = {
      data: {
        id: RECIPE_ID,
        code: "F-PAO-FR",
        display_name: "Pão francês (Demo)",
        status: "active",
        technical_product_id: "tp-1",
        row_version: 1,
        versions: [
          {
            id: RECIPE_VERSION_ID,
            formulation_id: RECIPE_ID,
            version_number: 1,
            status: "published",
            yield_units: 10,
            target_unit_weight_g: "50",
            expected_bake_loss_rate: "0.12",
            notes: null,
            published_at: "2026-08-23T12:00:00Z",
            row_version: 1,
          },
        ],
        identity: {
          id: RECIPE_ID,
          code: "F-PAO-FR",
          display_name: "Pão francês (Demo)",
          status: "active",
          technical_product_id: "tp-1",
          row_version: 1,
          current_version: { id: RECIPE_VERSION_ID, version_number: 1, status: "published" },
        },
        version: {
          id: RECIPE_VERSION_ID,
          formulation_id: RECIPE_ID,
          version_number: 1,
          status: "published",
          yield_units: 10,
          target_unit_weight_g: "50",
          expected_bake_loss_rate: "0.12",
          notes: null,
          published_at: "2026-08-23T12:00:00Z",
          row_version: 1,
        },
        items: [
          {
            id: "ri1",
            ingredient_version_id: "iv1",
            sequence: 1,
            net_quantity: "1000",
            gross_quantity: "1000",
            measurement_unit_id: "u1",
            correction_factor: "1",
            is_flour_basis: true,
            role: "ingredient",
            notes: null,
            bakers_percentage: "100",
            ingredient: {
              id: "ing1",
              code: "FAR-TRIGO",
              display_name: "Farinha de trigo tipo 1 (Demo)",
              version_id: "iv1",
              version_number: 1,
            },
            unit: { id: "u1", code: "g", symbol: "g", dimension: "mass" },
          },
        ],
        steps: [],
        bakers: { flour_mass: "1000", explained_absence: false, items: [] },
        yield: {
          base_net_mass: "1000",
          yield_units: 10,
          target_unit_weight_g: "50",
          expected_bake_loss_rate: "0.12",
          expected_final_mass_g: "500",
          portion_mass_g: null,
        },
        completeness: { ready_to_publish: true, complete_dossier: true, items: [] },
      },
      row_version: 1,
    };
    installApiMock({
      [`/recipes/${RECIPE_ID}`]: (url) => {
        if (url.pathname.includes(ORG_B)) return notFound();
        if (url.pathname.endsWith("/trials") || url.pathname.endsWith("/approvals") || url.pathname.endsWith("/references")) {
          return json({ data: [] });
        }
        if (url.pathname.endsWith("/scales")) return json({ data: [] });
        if (url.pathname.endsWith("/nutrition")) return json({ data: null });
        return json(dossier);
      },
    });
    const user = userEvent.setup();
    await renderApp(`/receitas/${RECIPE_ID}`);
    expect(await screen.findByRole("heading", { name: "Pão francês (Demo)" })).toBeInTheDocument();
    expect(document.body.textContent).toMatch(/Farinha de trigo tipo 1 \(Demo\)/);
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    await waitFor(() => {
      expect(document.body.textContent ?? "").not.toMatch(/Farinha de trigo tipo 1 \(Demo\)/);
    });
    expect(await screen.findByRole("heading", { name: /Não foi possível carregar|Falha/i })).toBeInTheDocument();
  });
});
