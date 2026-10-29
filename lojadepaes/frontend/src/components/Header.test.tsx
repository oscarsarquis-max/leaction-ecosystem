import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CartProvider } from "../shop/CartContext";
import { Header } from "./Header";

function renderHeader() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo) => {
      if (String(input).includes("/api/v1/conta/situacao")) {
        return { ok: true, json: async () => ({ identified: false, assinatura: { status: "unidentified", status_label: "Identifique-se" } }) };
      }
      if (String(input).includes("/api/v1/admin/")) {
        return { ok: false, status: 401, json: async () => ({}) };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    }),
  );
  return render(
    <CartProvider>
      <Header />
    </CartProvider>,
  );
}

describe("cabeçalho", () => {
  it("abre e fecha o menu por toque, atalho e Escape", async () => {
    const user = userEvent.setup();
    renderHeader();

    const toggle = screen.getByRole("button", { name: "Menu", hidden: true });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(toggle).toHaveAttribute("aria-controls");
    expect(screen.getByRole("button", { name: "Carrinho", hidden: true })).toHaveAttribute("aria-haspopup", "dialog");
    const logo = screen.getByRole("img", { name: "Loja de Pães — Boulangerie", hidden: true });
    expect(logo).toHaveAttribute("src", "/images/lojadepaeslogo.png");
    expect(logo.closest(".logo-window")).toBeTruthy();
    expect(await screen.findByLabelText("Usuário")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Entrar" })).not.toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Identifique-se", hidden: true })).toBeInTheDocument();
    expect(screen.queryByText(/Assinatura ativa/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Sem assinatura/i)).not.toBeInTheDocument();
    const home = screen.getByRole("link", { name: "Página principal", hidden: true });
    expect(home).toHaveAttribute("href", "#inicio");
    expect(home).toHaveAttribute("aria-current", "page");

    await user.click(toggle);
    expect(screen.getByRole("button", { name: "Fechar menu", hidden: true })).toHaveAttribute("aria-expanded", "true");
    await user.click(screen.getByRole("link", { name: "Crie seu pão", hidden: true }));
    expect(screen.getByRole("button", { name: "Menu", hidden: true })).toHaveAttribute("aria-expanded", "false");

    await user.click(screen.getByRole("button", { name: "Menu", hidden: true }));
    await user.keyboard("{Escape}");
    expect(screen.getByRole("button", { name: "Menu", hidden: true })).toHaveAttribute("aria-expanded", "false");
  });

  it("na página da receita leva o menu à home, não a âncoras inexistentes", () => {
    window.history.pushState({}, "", "/receitas/sardinhas-e-homus");
    renderHeader();
    expect(screen.getByRole("link", { name: "Nossos pães", hidden: true })).toHaveAttribute("href", "/#paes");
    expect(screen.getByRole("link", { name: "Crie seu pão", hidden: true })).toHaveAttribute("href", "/#criacao");
    expect(screen.getByRole("link", { name: "À nossa mesa", hidden: true })).toHaveAttribute("href", "/#mural");
    expect(screen.getByRole("link", { name: "Biblioteca do padeiro", hidden: true })).toHaveAttribute(
      "href",
      "/#biblioteca",
    );
    expect(screen.getByRole("img", { name: "Loja de Pães — Boulangerie", hidden: true }).closest("a")).toHaveAttribute(
      "href",
      "/",
    );
  });

  it("só mostra Para acompanhar quando a vitrine pública está visível", () => {
    render(
      <CartProvider>
        <Header />
      </CartProvider>,
    );
    expect(screen.queryByRole("link", { name: "Para acompanhar", hidden: true })).not.toBeInTheDocument();
    render(
      <CartProvider>
        <Header accompanimentsVisible />
      </CartProvider>,
    );
    expect(screen.getByRole("link", { name: "Para acompanhar", hidden: true })).toHaveAttribute("href", "/acompanhar");
  });
});

afterEach(() => {
  window.history.pushState({}, "", "/");
  vi.unstubAllGlobals();
});
