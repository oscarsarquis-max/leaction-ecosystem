import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchProduct } from "./catalogApi";
import {
  addToSelection,
  countItems,
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
});
