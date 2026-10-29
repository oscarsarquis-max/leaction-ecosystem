import { describe, expect, it } from "vitest";
import type { AccompanimentCard, AccompanimentsCatalog } from "./accompanimentsApi";
import {
  ACC_PAGE_SIZE,
  clampPage,
  flattenCatalogItems,
  groupPageStories,
  pageCount,
  slicePage,
} from "./accompanimentsPaging";

function card(id: string, occasion = "Mesa", extras: Partial<AccompanimentCard> = {}): AccompanimentCard {
  return {
    id,
    name: id,
    description: "",
    image_url: null,
    occasion,
    story_title: occasion,
    story_lead: "",
    why_pairs: "",
    serving_tip: "",
    price_label: "R$ 10,00",
    price_fresh: true,
    price_as_of: null,
    outbound_href: "https://www.mercadolivre.com.br/p/X",
    outbound_label: "Ver no Mercado Livre",
    marketplace: "Mercado Livre",
    story_href: `/acompanhar#${id}`,
    related_product_slugs: [],
    related_breads: [],
    related_recipes: [],
    ...extras,
  };
}

describe("paginação da vitrine de complementos", () => {
  it("usa a lista plana quando ela existe", () => {
    const catalog = {
      enabled: true,
      title: "Para acompanhar seu pão",
      intro: "",
      source_status: "hub",
      commission_note: null,
      external_notice: null,
      delivery_help: { mode: "manual", text: "" },
      attribution_ready: true,
      items: [card("a"), card("b")],
      stories: [{ occasion: "Mesa", title: "Mesa", lead: "", items: [card("story-only")] }],
    } as AccompanimentsCatalog;
    expect(flattenCatalogItems(catalog).map((item) => item.id)).toEqual(["a", "b"]);
  });

  it("cai nas histórias quando a lista plana está vazia", () => {
    const catalog = {
      enabled: true,
      title: "Para acompanhar seu pão",
      intro: "",
      source_status: "hub",
      commission_note: null,
      external_notice: null,
      delivery_help: { mode: "manual", text: "" },
      attribution_ready: true,
      items: [],
      stories: [
        { occasion: "Café", title: "Café", lead: "", items: [card("c1", "Café")] },
        { occasion: "Mesa", title: "Mesa", lead: "", items: [card("m1")] },
      ],
    } as AccompanimentsCatalog;
    expect(flattenCatalogItems(catalog).map((item) => item.id)).toEqual(["c1", "m1"]);
  });

  it("não repete nem pula itens entre páginas", () => {
    const items = Array.from({ length: 13 }, (_, index) => `item-${index + 1}`);
    expect(slicePage(items, 1)).toEqual(items.slice(0, 12));
    expect(slicePage(items, 2)).toEqual(["item-13"]);
    expect([...slicePage(items, 1), ...slicePage(items, 2)]).toEqual(items);
  });

  it("trata página inválida de modo previsível", () => {
    expect(pageCount(32)).toBe(3);
    expect(pageCount(0)).toBe(1);
    expect(clampPage(0, 13)).toBe(1);
    expect(clampPage(99, 13)).toBe(2);
    expect(clampPage(Number.NaN, 13)).toBe(1);
    expect(slicePage(["a"], 9)).toEqual(["a"]);
    expect(ACC_PAGE_SIZE).toBe(12);
  });

  it("agrupa a página corrente sem quebrar a ordem", () => {
    const grouped = groupPageStories([
      card("v1", "Vinhos"),
      card("v2", "Vinhos"),
      card("q1", "Queijos"),
      card("v3", "Vinhos"),
    ]);
    expect(grouped.map((story) => [story.occasion, story.items.map((item) => item.id)])).toEqual([
      ["Vinhos", ["v1", "v2"]],
      ["Queijos", ["q1"]],
      ["Vinhos", ["v3"]],
    ]);
  });
});
