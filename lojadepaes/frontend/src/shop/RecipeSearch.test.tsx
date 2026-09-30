import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RecipeSearch } from "./RecipeSearch";

describe("busca de receitas", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("pesquisa o acervo e abre o resultado", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo) => {
        const url = String(input);
        expect(url).toContain("/catalog/week-recipes");
        expect(url).toContain("q=azeite");
        return {
          ok: true,
          json: async () => ({
            q: "azeite",
            page: 1,
            page_size: 5,
            total: 1,
            items: [
              {
                title: "Torrada da casa",
                slug: "torrada-da-casa",
                summary: "Fatias com azeite.",
                href: "/receitas/torrada-da-casa",
                image_url: null,
              },
            ],
          }),
        };
      }),
    );
    render(<RecipeSearch compact />);
    expect(screen.getByLabelText("Buscar receitas")).toBeInTheDocument();
    await user.type(screen.getByPlaceholderText("Receita ou ingrediente…"), "azeite");
    await user.click(screen.getByRole("button", { name: "Buscar" }));
    expect(await screen.findByRole("link", { name: "Torrada da casa" })).toHaveAttribute(
      "href",
      "/receitas/torrada-da-casa",
    );
    expect(screen.getByText("Fatias com azeite.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver o acervo de receitas" })).toHaveAttribute("href", "/receitas");
    vi.unstubAllGlobals();
  });

  it("mostra ausência e erro recuperável", async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ q: "limão", page: 1, page_size: 5, total: 0, items: [] }),
      })
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          q: "limão",
          page: 1,
          page_size: 5,
          total: 1,
          items: [{ title: "Torrada", slug: "torrada", summary: "", href: "/receitas/torrada", image_url: null }],
        }),
      });
    vi.stubGlobal("fetch", fetchMock);
    render(<RecipeSearch compact />);
    await user.type(screen.getByPlaceholderText("Receita ou ingrediente…"), "limão");
    await user.click(screen.getByRole("button", { name: "Buscar" }));
    expect(await screen.findByText("Nenhuma receita encontrada.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Buscar" }));
    expect(await screen.findByText(/Não foi possível buscar receitas agora/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByRole("link", { name: "Torrada" })).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
