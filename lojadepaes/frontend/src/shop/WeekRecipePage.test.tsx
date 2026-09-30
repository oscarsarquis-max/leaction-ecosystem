import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { WeekRecipePage } from "./WeekRecipePage";

const recipe = {
  title: "Torrada da casa",
  slug: "torrada-da-casa",
  summary: "Fatias com azeite.",
  image_url: "/api/v1/catalog/media/demo",
  image_alt: "Torrada",
  image_caption: "",
  image_focus: "50% 50%",
  prep_time: "10 min",
  yield_text: "2 pessoas",
  ingredients: ["2 fatias de pão"],
  steps: ["Tostar"],
  breads: [{ name: "Pão da casa", slug: "pao-da-casa", href: "/paes/pao-da-casa" }],
  href: "/receitas/torrada-da-casa",
};

describe("página da receita", () => {
  afterEach(() => {
    sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("mostra leitura editorial e volta à vitrine, sem compra", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => recipe,
      })),
    );
    render(<WeekRecipePage slug="torrada-da-casa" />);
    expect(await screen.findByRole("heading", { name: "Torrada da casa" })).toBeInTheDocument();
    expect(screen.getByText("Receita em destaque")).toBeInTheDocument();
    expect(screen.getByText("2 fatias de pão")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Pão da casa" })).toHaveAttribute("href", "/paes/pao-da-casa");
    expect(screen.getByRole("link", { name: "Voltar à vitrine" })).toHaveAttribute("href", "/#paes");
    expect(screen.queryByText("Escolher meu pão")).not.toBeInTheDocument();
    expect(screen.queryByText(/R\$/)).not.toBeInTheDocument();
  });

  it("volta aos resultados da busca do acervo", async () => {
    sessionStorage.setItem(
      "lojadepaes_recipe_search",
      JSON.stringify({ q: "azeite", page: 2, from: "archive" }),
    );
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => recipe,
      })),
    );
    render(<WeekRecipePage slug="torrada-da-casa" />);
    expect(await screen.findByRole("link", { name: "Voltar aos resultados" })).toHaveAttribute(
      "href",
      "/receitas?q=azeite&page=2",
    );
  });
});
