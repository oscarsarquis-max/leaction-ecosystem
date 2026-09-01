import { afterEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import {
  assertCostingSurfaceLanguage,
  COSTING_SURFACE_FORBIDDEN_ENUMS,
  isPurchasedCalc,
  practicedStatusLabel,
  productComparisonScope,
  supplyModeSurfaceLabel,
  varianceSignal,
} from "./language/costing";
import { CALC_ID, costingCalculationFixture } from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

const purchasedCalc = {
  ...costingCalculationFixture,
  id: "c9c9c9c9-c9c9-c9c9-c9c9-c9c9c9c9c9c9",
  completeness: "complete",
  total_amount: "18.00",
  sellable_unit_amount: "18.00",
  sellable_quantity: "1",
  total_is_partial: false,
  technical_product_id: "tp-manteiga",
  subject: {
    product_display_name: "Manteiga tablete (Demo — comprado)",
    formulation_display_name: null,
    supply_mode: "purchased",
    kind: "planned",
    kind_label: "previsto",
    commercial_presentation: {
      defined: true,
      yield_units: 1,
      target_unit_weight_g: null,
      action_label: null,
      action_hint: null,
    },
  },
  cost_base: {
    amount: "18.00",
    origin: "sellable_unit",
    origin_label: "Custo de aquisição por unidade",
    unit_label: "R$ / unidade",
    usable: true,
    incomplete: false,
  },
  cost_scope: {
    mode: "purchased",
    scope_label: "Custo de aquisição completo",
    completeness_label: "Custo de aquisição completo",
    margin_label: "Margem sobre o custo de aquisição",
    comparison_scope_label: "Mercadoria comprada",
    ingredients_complete: true,
    acquisition_complete: true,
    production_complete: false,
    price_definitive_allowed: true,
    included_categories: [],
    excluded_categories: [],
    categories: [
      {
        code: "ingredient",
        label: "Valor de compra",
        state: "valued",
        state_label: "Valorizado",
        amount: "18.00",
      },
      {
        code: "labor",
        label: "Mão de obra",
        state: "not_applicable",
        state_label: "Não se aplica",
      },
      {
        code: "energy",
        label: "Energia/processo",
        state: "not_applicable",
        state_label: "Não se aplica",
      },
    ],
    hint: "Escopo de aquisição: valor de compra conhecido.",
  },
  analytics: {
    ...costingCalculationFixture.analytics,
    composition_title: "Composição do custo de aquisição",
    formation_title: "Formação do custo por categoria",
    use_waterfall: false,
    known_total: "18.00",
    missing_count: 0,
    valued_count: 1,
    missing_names: [],
    category_bars: [
      {
        category: "ingredient",
        category_label: "Valor de compra",
        amount: "18.00",
        missing_count: 0,
        valued_count: 1,
        share_of_known_percent: "100",
        state: "confirmado",
      },
    ],
    component_bars: [
      {
        id: "comp-1",
        label: "Manteiga tablete (Demo)",
        amount: "18.00",
        share_of_known_percent: "100",
        state: "confirmado",
        quality_label: "Preço vigente",
      },
    ],
  },
  components: [
    {
      id: "comp-1",
      display_name: "Manteiga tablete (Demo)",
      category: "ingredient",
      category_label: "Valor de compra",
      amount: "18.00",
      quantity: "1",
      unit_code: "un",
      quality: "current_price",
      quality_label: "Preço vigente",
      share_percent: "100",
      price_missing: false,
      memory: [],
    },
  ],
  gaps: [],
};

describe("gate custos — semântica e linguagem", () => {
  it("rendimento menor é desfavorável; custo igual é neutro; custo maior é desfavorável", () => {
    expect(varianceSignal("yield", "8", "7").label).toBe("desfavorável");
    expect(varianceSignal("cost", "3.16", "3.61").label).toBe("desfavorável");
    expect(varianceSignal("cost", "25.24", "25.24").label).toBe("neutro");
    expect(varianceSignal("cost", "10", "9").label).toBe("favorável");
    expect(varianceSignal("yield", "7", "8").label).toBe("favorável");
  });

  it("traduz modalidade e escopo sem enum técnico", () => {
    expect(practicedStatusLabel("active")).toBe("Ativo");
    expect(supplyModeSurfaceLabel("purchased")).toBe("Comprado");
    expect(supplyModeSurfaceLabel("produced")).toBe("Produzido");
    expect(
      isPurchasedCalc({
        subject: { supply_mode: "purchased", product_display_name: "Manteiga" },
      }),
    ).toBe(true);
    expect(
      productComparisonScope({
        subject: { product_display_name: "Manteiga tablete (Demo — comprado)" },
      }),
    ).toBe("Mercadoria comprada");
    expect(
      productComparisonScope({
        completeness: "complete",
        subject: { product_display_name: "Pão francês (Demo)" },
        cost_scope: { ingredients_complete: true },
      }),
    ).toBe("Ingredientes — demais custos de produção não configurados");
  });
});

describe("superfície de custos — sem enums técnicos", () => {
  it("decisão de mercadoria comprada não exibe purchased/active/ingredient/current_price", async () => {
    installApiMock({
      [`/costing/calculations/${purchasedCalc.id}`]: () => json({ data: purchasedCalc }),
      "/costing/calculations": (_url, request) => {
        if (request.method !== "GET") return json({ data: purchasedCalc });
        return json({
          items: [
            {
              ...costingCalculationFixture,
              subject: {
                ...costingCalculationFixture.subject,
                product_display_name: "Pão francês (Demo)",
                supply_mode: "produced",
              },
              sellable_unit_amount: "0.46",
              sellable_quantity: "60",
              cost_scope: {
                ...costingCalculationFixture.cost_scope,
                mode: "produced",
                comparison_scope_label: "Ingredientes — demais custos de produção não configurados",
              },
            },
            purchasedCalc,
          ],
        });
      },
      "/pricing/practiced": () =>
        json({
          items: [
            {
              id: "price-1",
              technical_product_id: "tp-manteiga",
              channel: "own_counter",
              amount: "22.00",
              status: "active",
              valid_from: "2026-08-04T12:00:00+00:00",
              row_version: 1,
              justification: "demo",
            },
            {
              id: "price-2",
              technical_product_id: "tp-manteiga",
              channel: "own_counter",
              amount: "23.50",
              status: "active",
              valid_from: "2026-08-17T12:00:00+00:00",
              row_version: 1,
              justification: "demo",
            },
            {
              id: "price-3",
              technical_product_id: "tp-manteiga",
              channel: "own_counter",
              amount: "24.90",
              status: "active",
              valid_from: "2026-08-24T12:00:00+00:00",
              row_version: 1,
              justification: "demo",
            },
          ],
        }),
    });

    await renderApp(`/gestao/custos/decisao?calculo=${purchasedCalc.id}`);
    expect(await screen.findByRole("heading", { name: /Manteiga tablete/ })).toBeInTheDocument();
    expect(screen.getByText("Custo de aquisição completo")).toBeInTheDocument();
    expect(screen.getByText("Mercadoria comprada · OP não se aplica")).toBeInTheDocument();
    expect(screen.getAllByText("Não se aplica").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Ativo").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Balcão próprio").length).toBeGreaterThan(0);

    const surface = document.body.textContent ?? "";
    expect(surface).not.toMatch(COSTING_SURFACE_FORBIDDEN_ENUMS);
    expect(() => assertCostingSurfaceLanguage(surface)).not.toThrow();
    expect(surface).toMatch(/Custo de aquisição/);
    expect(surface).toMatch(/Mercadoria comprada/);
    expect(surface).toMatch(/Valor de compra/);
  });

  it("cálculo parcial produzido também limpa enums na decisão", async () => {
    installApiMock();
    await renderApp(`/gestao/custos/decisao?calculo=${CALC_ID}`);
    expect(await screen.findByRole("heading", { name: "Pão tradicional" })).toBeInTheDocument();
    const surface = document.body.textContent ?? "";
    expect(surface).not.toMatch(COSTING_SURFACE_FORBIDDEN_ENUMS);
  });
});
