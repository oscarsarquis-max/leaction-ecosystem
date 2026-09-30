import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchBuilderCatalog } from "../features/bread-builder/builderApi";
import { fetchProduct } from "./catalogApi";
import {
  addToSelection,
  additionMessage,
  applyProductAddition,
  countItems,
  packDescription,
  readSelection,
  removeLine,
  resolveSelection,
  SELECTION_KEY,
  setLineAdaptation,
  setLineQuantity,
  storefrontItemsFromLines,
  writeSelection,
} from "./selection";
import type { PublicProduct } from "./types";

vi.mock("./catalogApi", () => ({
  fetchProduct: vi.fn(),
}));
vi.mock("../features/bread-builder/builderApi", () => ({
  fetchBuilderCatalog: vi.fn(),
}));

const product: PublicProduct = {
  name: "Pão da casa",
  slug: "pao-da-casa",
  short_description: "Crosta firme",
  image_url: "/api/v1/catalog/media/1",
  image_alt: "Pão",
  is_available: true,
  from_price: { cents: 2490, currency: "BRL" },
  price_is_from: true,
  variants: [
    {
      id: "v500",
      display_name: "500 g",
      presentation_type: "weight",
      net_weight_grams: 500,
      units_per_pack: null,
      pack_label: null,
      price: { cents: 2490, currency: "BRL" },
    },
    {
      id: "v800",
      display_name: "800 g",
      presentation_type: "weight",
      net_weight_grams: 800,
      units_per_pack: null,
      pack_label: null,
      price: { cents: 3200, currency: "BRL" },
    },
  ],
};

describe("seleção de compra", () => {
  beforeEach(() => {
    vi.mocked(fetchProduct).mockResolvedValue(product);
    vi.mocked(fetchBuilderCatalog).mockResolvedValue({
      price_cents: 7000,
      weight_grams: 500,
      currency: "BRL",
      fulfillment: "pickup",
      doughs: [{ id: "prep-1", name: "Sovada (Kneaded dough)", description: "", assistant_role: undefined }],
      flours: [{ id: "flour-1", name: "Branca (Strong white)", description: "", assistant_role: "flour" }],
      ingredients: [],
      shapes: [],
    });
    localStorage.clear();
  });

  it("agrupa pela variação e remove linhas", () => {
    let lines = addToSelection([], "pao-da-casa", "v500", 1);
    lines = addToSelection(lines, "pao-da-casa", "v500", 2);
    lines = addToSelection(lines, "pao-da-casa", "v800", 1);
    expect(lines).toHaveLength(2);
    expect(countItems(lines)).toBe(4);
    const keep = lines.find((line) => line.variantId === "v500");
    const drop = lines.find((line) => line.variantId === "v800");
    expect(keep && drop).toBeTruthy();
    lines = setLineQuantity(lines, keep!.key, 1);
    lines = removeLine(lines, drop!.key);
    expect(lines).toMatchObject([{ slug: "pao-da-casa", variantId: "v500", quantity: 1 }]);
  });

  it("mantém linhas distintas da mesma variação com adaptações diferentes", () => {
    let lines = addToSelection([], "pao-da-casa", "v500", 1);
    lines = addToSelection(lines, "pao-da-casa", "v500", 1, {
      text: "sem gergelim",
      reason: "preference",
    });
    expect(lines).toHaveLength(2);
    expect(countItems(lines)).toBe(2);
    expect(storefrontItemsFromLines(lines)).toEqual([
      { variant_id: "v500", quantity: 1, adaptation_text: undefined, adaptation_reason: undefined },
      {
        variant_id: "v500",
        quantity: 1,
        adaptation_text: "sem gergelim",
        adaptation_reason: "preference",
      },
    ]);
  });

  it("edita e remove adaptação sem criar outro produto e restaura o carrinho", () => {
    let lines = addToSelection([], "pao-da-casa", "v500", 2, {
      text: "sem gergelim",
      reason: "dietary_restriction",
    });
    writeSelection(lines);
    const restored = readSelection();
    expect(restored[0]?.adaptation?.text).toBe("sem gergelim");
    expect(localStorage.getItem(SELECTION_KEY)).toContain("sem gergelim");
    lines = setLineAdaptation(restored, restored[0]!.key, { text: "sem nozes", reason: "preference" });
    expect(lines).toHaveLength(1);
    expect(lines[0]?.adaptation?.text).toBe("sem nozes");
    lines = setLineAdaptation(lines, lines[0]!.key, null);
    expect(lines[0]?.adaptation).toBeNull();
    expect(lines[0]?.variantId).toBe("v500");
  });

  it("revalida preço e disponibilidade pelo catálogo", async () => {
    const ok = await resolveSelection([{ key: "k1", slug: "pao-da-casa", variantId: "v500", quantity: 2 }]);
    expect(ok.totalCents).toBe(4980);
    vi.mocked(fetchProduct).mockResolvedValue({
      ...product,
      is_available: false,
      variants: [{ ...product.variants[0], price: { cents: 3000, currency: "BRL" } }],
    });
    const blocked = await resolveSelection([{ key: "k1", slug: "pao-da-casa", variantId: "v500", quantity: 2 }]);
    expect(blocked.totalCents).toBe(0);
    expect(blocked.lines[0]?.notice).toMatch(/indisponível/i);
  });

  it("uma inclusão em carrinho vazio permanece em 1 e a segunda avisa a soma", () => {
    const first = applyProductAddition([], "pao-da-casa", "v500", 1);
    expect(first.lines).toMatchObject([{ quantity: 1 }]);
    expect(first.message).toBe("Adicionado 1 pão.");
    writeSelection(first.lines);
    const restored = readSelection();
    expect(restored).toMatchObject([{ quantity: 1 }]);
    const second = applyProductAddition(restored, "pao-da-casa", "v500", 1);
    expect(second.lines).toMatchObject([{ quantity: 2 }]);
    expect(second.message).toBe(additionMessage(1, 1));
    expect(second.message).toBe("Adicionado 1 pão. Você tem 2 deste pão no carrinho.");
    const edited = setLineQuantity(second.lines, second.lines[0]!.key, 1);
    expect(edited).toMatchObject([{ quantity: 1 }]);
    expect(storefrontItemsFromLines(edited)).toEqual([
      { variant_id: "v500", quantity: 1, adaptation_text: undefined, adaptation_reason: undefined },
    ]);
  });

  it("não repete 500 g quando o nome da opção já é o peso", async () => {
    expect(packDescription(product, "v500")).toBeNull();
    const resolved = await resolveSelection([{ key: "k1", slug: "pao-da-casa", variantId: "v500", quantity: 1 }]);
    expect(resolved.lines[0]?.variantName).toBe("500 g");
    expect(resolved.lines[0]?.packLabel).toBeNull();
    expect(resolved.totalCents).toBe(2490);
    const packed = {
      ...product,
      variants: [
        {
          ...product.variants[0],
          id: "pack",
          display_name: "Pacote",
          presentation_type: "pack" as const,
          net_weight_grams: null,
          units_per_pack: 6,
          pack_label: "pacote com 6 unidades",
          price: { cents: 7000, currency: "BRL" as const },
        },
      ],
    };
    expect(packDescription(packed, "pack")).toBe("pacote com 6 unidades");
  });

  it("pede revisão só do preparo antigo e mantém complementos no rascunho", async () => {
    const resolved = await resolveSelection([
      {
        key: "old",
        slug: "pao-personalizado",
        variantId: "",
        quantity: 1,
        adaptation: { text: "pepperoni", reason: "preference" },
        custom: {
          doughTypeId: "old-integral",
          breadShapeId: "shape-1",
          ingredientIds: ["flour-old", "nuts"],
          doughName: "Integral",
          shapeName: "Pão de forma",
          ingredientNames: ["Farinha branca italiana", "Nozes"],
          flourId: "flour-old",
          flourName: "Farinha branca italiana",
          weightGrams: 500,
          unitCents: 7000,
        },
      },
    ]);
    expect(resolved.totalCents).toBe(0);
    expect(resolved.lines[0]?.available).toBe(false);
    expect(resolved.lines[0]?.reviewTarget).toBe("preparation");
    expect(resolved.lines[0]?.notice).toMatch(/preparo desta seleção/i);
    expect(resolved.lines[0]?.custom?.ingredientNames).toContain("Nozes");
    expect(resolved.lines[0]?.adaptation?.text).toBe("pepperoni");
  });
});
