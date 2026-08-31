import { describe, expect, it } from "vitest";
import {
  buildCriticalPath,
  findCriticalPosition,
  productJourneyFromCard,
  stepApplicableForProduct,
} from "./fluxo/criticalPath";
import type { FlowEvidence } from "./fluxo/resolve";
import { productFixture, productPurchasedFixture } from "./api/fixtures";

const empty: FlowEvidence = {
  ingredientsTotal: null,
  recipesTotal: null,
  ordersTotal: null,
  inventoryItemsTotal: null,
  products: null,
  fiscal: null,
};

describe("R028-003 caminho crítico", () => {
  it("visão geral identifica preparação e não confunde foco com posição", () => {
    const path = buildCriticalPath({
      mode: "org",
      evidence: {
        ...empty,
        fiscal: {
          total: 0,
          awaiting_match: 0,
          awaiting_check: 0,
          partially_received: 0,
          divergent: 0,
          confirmed: 0,
        },
        ingredientsTotal: 18,
        products: {
          total: 12,
          active: 12,
          purchased: 1,
          intermediate: 0,
          produced_without_recipe: 2,
        },
        recipesTotal: 6,
        ordersTotal: 10,
      },
      hasPermission: () => true,
      focusId: 8,
      profileFocus: new Set([1, 2, 3, 4, 5, 6, 7, 8]),
      product: null,
    });
    expect(path.orgPreparationNote).toMatch(/preparação geral/i);
    expect(path.criticalPositionId).toBe(1);
    expect(path.steps.find((s) => s.def.id === 1)?.mapLabel).toBe("Você está aqui");
    expect(path.steps.find((s) => s.def.id === 8)?.isFocus).toBe(true);
    expect(path.steps.find((s) => s.def.id === 8)?.mapLabel).not.toBe("Você está aqui");
    expect(path.blockingPending).toMatch(/Nenhuma entrada/i);
    expect(path.blockingPending).not.toMatch(/^0 entrada/);
  });

  it("produto produzido sem receita bloqueia em Receitas", () => {
    const product = productJourneyFromCard(productFixture);
    expect(product.hasPublishedRecipe).toBe(false);
    const path = buildCriticalPath({
      mode: "product",
      evidence: {
        ...empty,
        fiscal: {
          total: 2,
          awaiting_match: 0,
          awaiting_check: 0,
          partially_received: 0,
          divergent: 0,
          confirmed: 2,
        },
        ingredientsTotal: 5,
        inventoryItemsTotal: 3,
      },
      hasPermission: () => true,
      focusId: 3,
      profileFocus: new Set([3, 4]),
      product,
    });
    expect(path.criticalPositionId).toBe(4);
    expect(path.steps.find((s) => s.def.id === 4)?.situation).toBe("Requer atenção");
    expect(path.steps.find((s) => s.def.id === 3)?.isFocus).toBe(true);
    expect(path.steps.find((s) => s.def.id === 3)?.isCriticalPosition).toBe(false);
  });

  it("produto produzido com receita e ordem fica pronto para execução", () => {
    const product = productJourneyFromCard({
      ...productFixture,
      has_published_recipe: true,
      recipe_status_label: "Com receita vigente",
      links: { recipes_count: 1, orders_count: 2 },
    });
    const path = buildCriticalPath({
      mode: "product",
      evidence: {
        ...empty,
        fiscal: {
          total: 1,
          awaiting_match: 0,
          awaiting_check: 0,
          partially_received: 0,
          divergent: 0,
          confirmed: 1,
        },
        ingredientsTotal: 4,
        inventoryItemsTotal: 2,
      },
      hasPermission: () => true,
      focusId: 6,
      profileFocus: new Set([5, 6]),
      product,
    });
    expect(path.steps.find((s) => s.def.id === 4)?.situation).toBe("Pronto");
    expect(path.steps.find((s) => s.def.id === 5)?.situation).toBe("Pronto");
    expect(path.criticalPositionId).toBe(6);
    expect(path.steps.find((s) => s.def.id === 6)?.mapLabel).toBe("Você está aqui");
  });

  it("comprado marca receita/planejamento/execução como não aplicável", () => {
    const product = productJourneyFromCard(productPurchasedFixture);
    expect(stepApplicableForProduct(4, product).applicable).toBe(false);
    const path = buildCriticalPath({
      mode: "product",
      evidence: {
        ...empty,
        fiscal: {
          total: 1,
          awaiting_match: 0,
          awaiting_check: 0,
          partially_received: 0,
          divergent: 0,
          confirmed: 1,
        },
        ingredientsTotal: 1,
        inventoryItemsTotal: 1,
      },
      hasPermission: () => true,
      focusId: 1,
      profileFocus: new Set([1, 2, 3]),
      product,
    });
    expect(path.steps.find((s) => s.def.id === 4)?.situation).toBe("Não se aplica");
    expect(path.steps.find((s) => s.def.id === 5)?.situation).toBe("Não se aplica");
    expect(path.steps.find((s) => s.def.id === 6)?.situation).toBe("Não se aplica");
    expect(path.modalityNote).toMatch(/comprado/i);
  });

  it("misto sem origem exige decisão", () => {
    const product = productJourneyFromCard({
      ...productFixture,
      supply_mode: "mixed",
      code: "MISTO-1",
    });
    const path = buildCriticalPath({
      mode: "product",
      evidence: {
        ...empty,
        fiscal: {
          total: 1,
          awaiting_match: 0,
          awaiting_check: 0,
          partially_received: 0,
          divergent: 0,
          confirmed: 1,
        },
        ingredientsTotal: 1,
      },
      hasPermission: () => true,
      focusId: 3,
      profileFocus: new Set([3]),
      product,
    });
    expect(path.criticalPositionId).toBe(4);
    expect(path.steps.find((s) => s.def.id === 4)?.pending).toMatch(/origem/i);
  });

  it("combo não trata receita", () => {
    const product = productJourneyFromCard({
      ...productFixture,
      supply_mode: "combo",
      code: "COMBO-1",
      has_published_recipe: false,
    });
    expect(stepApplicableForProduct(4, product).applicable).toBe(false);
  });

  it("intermediário não segue direto à vitrine", () => {
    const product = productJourneyFromCard({
      ...productFixture,
      purpose: "intermediate",
      supply_mode: "produced",
      code: "INT-1",
      has_published_recipe: true,
      links: { recipes_count: 1, orders_count: 0 },
    });
    // purpose intermediate with produced supply - use supply intermediate
    const asIntermediate = { ...product, supplyMode: "intermediate" };
    expect(stepApplicableForProduct(7, asIntermediate).applicable).toBe(false);
  });

  it("perfil sem custos oculta etapa 8", () => {
    const path = buildCriticalPath({
      mode: "org",
      evidence: empty,
      hasPermission: (code) => !code.startsWith("costing") && !code.startsWith("pricing"),
      focusId: 1,
      profileFocus: new Set([1, 2, 3, 4, 5, 6, 7]),
      product: null,
    });
    expect(path.steps.some((s) => s.def.id === 8)).toBe(false);
  });

  it("findCriticalPosition ignora prontos e não aplicáveis", () => {
    expect(
      findCriticalPosition([
        { id: 1, situation: "Pronto", applicable: true, hasAccess: true },
        { id: 4, situation: "Não se aplica", applicable: false, hasAccess: true },
        { id: 5, situation: "Não iniciado", applicable: true, hasAccess: true },
      ]),
    ).toBe(5);
  });
});
