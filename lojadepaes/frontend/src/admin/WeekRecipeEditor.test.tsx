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

  it("salva o rascunho com alt vazio e não chama publicação", async () => {
    const saved = {
      ...existing,
      id: "rec-1",
      image_url: "/api/v1/admin/media/foto",
      featured_image_id: "media-1",
      method_text: "Asse 25 minutos.",
      ingredients: ["pão", "azeite"],
      publish_gaps: ["o texto alternativo da foto"],
    };
    vi.mocked(adminRequest).mockImplementation(async (path: string, init?: RequestInit) => {
      if (path.includes("/products")) {
        return { items: [] };
      }
      if (path === "/api/v1/admin/week-recipes/rec-1" && init?.method === "PUT") {
        return saved;
      }
      if (String(path).includes("/publish")) {
        throw new Error("não deveria publicar");
      }
      return saved;
    });
    const user = userEvent.setup();
    render(<WeekRecipeEditor recipeId="rec-1" onBack={() => undefined} onSaved={() => undefined} />);
    expect(await screen.findByLabelText("Texto alternativo da foto")).toHaveValue("");
    await user.click(screen.getAllByRole("button", { name: "Publicar e destacar na home" })[0]);
    expect(await screen.findByText("Rascunho salvo. A publicação não foi feita.")).toBeInTheDocument();
    expect(screen.getByText(/Ainda não dá para publicar. Complete: o texto alternativo da foto/)).toBeInTheDocument();
    expect(screen.getAllByText("Rascunho salvo · não publicado").length).toBeGreaterThan(0);
    expect(screen.queryByText("Erro ao salvar")).not.toBeInTheDocument();
    expect(adminRequest).not.toHaveBeenCalledWith(expect.stringContaining("/publish"), expect.anything());
    await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText("Texto alternativo da foto")));
  });

  it("cancelar a saída com alterações não salvas conserva o texto", async () => {
    vi.mocked(adminRequest).mockImplementation(async (path: string) => {
      if (path.includes("/products")) {
        return { items: [] };
      }
      return existing;
    });
    const onBack = vi.fn();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    render(<WeekRecipeEditor recipeId="rec-1" onBack={onBack} onSaved={() => undefined} />);
    const title = await screen.findByLabelText("Título da receita");
    await user.clear(title);
    await user.type(title, "Texto que deve permanecer");
    await user.click(screen.getByRole("button", { name: "Voltar à lista" }));
    expect(confirm).toHaveBeenCalled();
    expect(onBack).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Título da receita")).toHaveValue("Texto que deve permanecer");
    confirm.mockRestore();
  });
});
