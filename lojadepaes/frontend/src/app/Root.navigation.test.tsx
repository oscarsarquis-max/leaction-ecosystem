import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Root } from "./Root";

const INTERNAL = [
  "/receitas/sardinhas-e-homus",
  "/receitas",
  "/biblioteca/o-comeco",
  "/biblioteca/calculadora",
  "/paes/pao-da-casa",
  "/pedido/novo",
  "/pedido/LPTESTE",
  "/solicitacao/15bd4592-0000-4000-8000-000000000001",
  "/ativar/token-demo",
  "/admin/produtos",
  "/admin/produtos/receitas/nova",
  "/admin/pedidos",
  "/admin/agenda",
  "/admin/fidelidade",
];

describe("retorno à página principal", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 404,
        json: async () => ({}),
        text: async () => "",
      })),
    );
  });

  afterEach(() => {
    window.history.pushState({}, "", "/");
    vi.unstubAllGlobals();
  });

  it("na home Página principal é o item atual, sem faixa de retorno", async () => {
    window.history.pushState({}, "", "/");
    render(<Root />);
    const link = screen.getByRole("link", { name: "Página principal" });
    expect(link).toHaveAttribute("href", "#inicio");
    expect(link).toHaveAttribute("aria-current", "page");
    expect(document.querySelector(".home-return")).toBeNull();
    expect(await screen.findByLabelText("Usuário")).toBeInTheDocument();
  });

  it.each(INTERNAL)("em %s o retorno textual aponta para a home", (path) => {
    window.history.pushState({}, "", path);
    render(<Root />);
    const returns = [...document.querySelectorAll(".home-return a")];
    expect(returns.length).toBeGreaterThan(0);
    for (const link of returns) {
      expect(link).toHaveAttribute("href", "/");
      expect(link).toHaveTextContent("Página principal");
    }
    const menu = screen.queryByRole("navigation", { name: "Navegação principal" });
    if (menu) {
      expect(menu.querySelector('a[href="#paes"]')).toBeNull();
    }
  });

  it("na receita o menu leva às seções da home e preserva o acervo separado", () => {
    window.history.pushState({}, "", "/receitas/sardinhas-e-homus");
    render(<Root />);
    expect(screen.getByRole("link", { name: "Nossos pães" })).toHaveAttribute("href", "/#paes");
    expect(screen.getByRole("link", { name: "Crie seu pão" })).toHaveAttribute("href", "/#criacao");
    expect(screen.getByRole("link", { name: "À nossa mesa" })).toHaveAttribute("href", "/#mural");
    expect(screen.getByRole("link", { name: "Biblioteca do padeiro" })).toHaveAttribute("href", "/#biblioteca");
    expect(document.querySelector(".site-header .brand")).toHaveAttribute("href", "/");
    expect(document.querySelector(".home-return a")).toHaveAttribute("href", "/");
  });
});
