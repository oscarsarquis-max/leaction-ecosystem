import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AdminSidebar } from "./shell/AdminSidebar";

describe("abas de produtos", () => {
  it("separa cadastro comercial e receitas da semana no menu", () => {
    render(
      <AdminSidebar
        path="/admin/produtos/receitas"
        open
        onNavigate={() => {}}
        noticesOpen={false}
        onToggleNotices={() => {}}
        sidebarRef={{ current: null }}
      />,
    );
    expect(screen.getByRole("link", { name: "Receitas da semana" })).toHaveAttribute(
      "href",
      "/admin/produtos/receitas",
    );
    expect(screen.getByRole("link", { name: "Receitas da semana" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Produtos" })).toHaveAttribute("href", "/admin/produtos");
    expect(screen.getByRole("link", { name: "Gigio" })).toHaveAttribute("href", "/admin/produtos/gigio");
    expect(screen.getByRole("link", { name: "Harmonizações" })).toHaveAttribute(
      "href",
      "/admin/produtos/gigio/harmonizacoes",
    );
    expect(screen.getByRole("link", { name: "Complementos" })).toHaveAttribute("href", "/admin/produtos/complementos");
  });
});
