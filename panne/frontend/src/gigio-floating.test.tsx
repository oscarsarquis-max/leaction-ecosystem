import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ORG_A } from "./api/fixtures";
import { installApiMock } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

const pages = [
  ["/inicio", "Hoje na Panne"],
  ["/produtos", "Produtos"],
  ["/receitas", "Minhas receitas"],
  ["/componentes/ingredientes", "Ingredientes"],
  ["/gestao/custos", "Custos, preços e margem"],
] as const;

describe("CURSOR-028-R2 Gigio flutuante", () => {
  it("é o único Gigio nas telas autenticadas e abre no máximo três pontos", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    for (const [path, heading] of pages) {
      const { view } = await renderApp(path);
      expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
      expect(screen.queryByRole("complementary", { name: /Orientação do processo/i })).not.toBeInTheDocument();
      expect(document.querySelector(".flow-gigio")).toBeNull();
      expect(document.querySelector(".product-gigio-fab")).toBeNull();
      const open = screen.getByRole("button", { name: "Abrir Gigio" });
      await user.click(open);
      const dialog = await screen.findByRole("dialog", { name: "Gigio" });
      expect(dialog).toHaveTextContent(/Situação/);
      expect(dialog).toHaveTextContent(/Principal pendência/);
      expect(dialog).toHaveTextContent(/Próxima ação/);
      expect(dialog).not.toHaveTextContent("Ir para");
      expect(dialog).not.toHaveTextContent("Glossário");
      await user.click(screen.getByRole("button", { name: "Fechar" }));
      expect(screen.queryByRole("dialog", { name: "Gigio" })).not.toBeInTheDocument();
      view.unmount();
    }
  });

  it("mantém ajuda de login no avatar público", async () => {
    installApiMock();
    const user = userEvent.setup();
    await renderApp("/entrar", { signedIn: false });
    await user.click(screen.getByRole("button", { name: "Abrir Gigio" }));
    const dialog = await screen.findByRole("dialog", { name: "Gigio" });
    expect(dialog).toHaveTextContent(/login|entrar|demonstração/i);
    expect(dialog).not.toHaveTextContent("Padaria Central");
  });
});
