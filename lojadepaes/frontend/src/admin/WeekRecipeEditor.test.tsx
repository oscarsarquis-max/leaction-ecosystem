import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { WeekRecipeEditor } from "./WeekRecipeEditor";
import { adminRequest } from "./api";

vi.mock("./api", () => ({
  AdminApiError: class AdminApiError extends Error {
    status = 400;
  },
  adminRequest: vi.fn(),
  actionErrorMessage: (_error: unknown, fallback: string) => fallback,
}));

const existing = {
  id: "rec-1",
  title: "Torrada antiga",
  slug: "torrada-antiga",
  summary: "Fatias com azeite.",
  image_url: null,
  image_alt: "",
  image_caption: "",
  image_focus: "50% 50%",
  prep_time: "10 min",
  yield_text: "2 pessoas",
  ingredients: ["2 fatias de pão", "azeite"],
  method_text: "1. Toste o pão\n\n2. Regue com azeite",
  steps: ["1. Toste o pão", "2. Regue com azeite"],
  breads: [],
  href: "/receitas/torrada-antiga",
  editorial_status: "draft",
  is_featured: false,
  featured_image_id: null,
  featured_image_alt: "",
  featured_image_caption: "",
  image_focus_x: 50,
  image_focus_y: 50,
  prep_time_text: "10 min",
  product_ids: [],
  publish_gaps: ["a foto de destaque", "o texto alternativo da foto"],
};

describe("editor de receita da semana", () => {
  it("abre receita antiga num único campo e não mostra passos", async () => {
    vi.mocked(adminRequest).mockImplementation(async (path: string) => {
      if (path.includes("/products")) {
        return { items: [] };
      }
      return existing;
    });
    render(<WeekRecipeEditor recipeId="rec-1" onBack={() => undefined} onSaved={() => undefined} />);
    expect(await screen.findByLabelText("Modo de preparo")).toHaveValue("1. Toste o pão\n\n2. Regue com azeite");
    expect(screen.getByLabelText("Ingredientes")).toHaveValue("2 fatias de pão\nazeite");
    expect(screen.queryByRole("button", { name: "Adicionar passo" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Subir" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remover passo" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Editar receita" })).toBeInTheDocument();
    expect(screen.queryByText("Ajustar enquadramento")).not.toBeInTheDocument();
    expect(screen.queryByText("Horizontal")).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Publicar e destacar na home" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "Publicar sem destacar" }).length).toBeGreaterThan(0);
  });

  it("salva o texto colado sem exigir cliques por passo", async () => {
    vi.mocked(adminRequest).mockImplementation(async (path: string, init?: RequestInit) => {
      if (path.includes("/products")) {
        return { items: [] };
      }
      if (path === "/api/v1/admin/week-recipes" && init?.method === "POST") {
        const body = JSON.parse(String(init.body));
        expect(body.method_text).toContain("Aqueça o forno");
        expect(body.steps).toBeUndefined();
        expect(body.ingredients).toEqual(["água", "farinha"]);
        return { ...existing, id: "rec-new", method_text: body.method_text, ingredients: body.ingredients };
      }
      return { items: [] };
    });
    const user = userEvent.setup();
    render(<WeekRecipeEditor recipeId={null} onBack={() => undefined} onSaved={() => undefined} />);
    await user.type(screen.getByLabelText("Título da receita"), "Nova");
    await user.type(screen.getByLabelText("Ingredientes"), "água{enter}farinha");
    await user.type(screen.getByLabelText("Modo de preparo"), "Aqueça o forno.{enter}{enter}Asse.");
    await user.click(screen.getAllByRole("button", { name: "Salvar rascunho" })[0]);
    await waitFor(() => expect(adminRequest).toHaveBeenCalledWith("/api/v1/admin/week-recipes", expect.objectContaining({ method: "POST" })));
  });
});
