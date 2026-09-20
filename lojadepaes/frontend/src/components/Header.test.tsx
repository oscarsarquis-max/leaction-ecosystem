import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { CartProvider } from "../shop/CartContext";
import { Header } from "./Header";

function renderHeader() {
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
    expect(screen.getByRole("button", { name: "Abrir carrinho", hidden: true })).toHaveAttribute("aria-haspopup", "dialog");
    const logo = screen.getByRole("img", { name: "Loja de Pães — Boulangerie", hidden: true });
    expect(logo).toHaveAttribute("src", "/images/lojadepaeslogo.png");
    expect(logo.closest(".logo-window")).toBeTruthy();
    expect(await screen.findByLabelText("Usuário")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Entrar" })).not.toBeInTheDocument();

    await user.click(toggle);
    expect(screen.getByRole("button", { name: "Fechar menu", hidden: true })).toHaveAttribute("aria-expanded", "true");
    await user.click(screen.getByRole("link", { name: "Crie seu pão", hidden: true }));
    expect(screen.getByRole("button", { name: "Menu", hidden: true })).toHaveAttribute("aria-expanded", "false");

    await user.click(screen.getByRole("button", { name: "Menu", hidden: true }));
    await user.keyboard("{Escape}");
    expect(screen.getByRole("button", { name: "Menu", hidden: true })).toHaveAttribute("aria-expanded", "false");
  });
});
