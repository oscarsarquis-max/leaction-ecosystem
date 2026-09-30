import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CatalogTabs } from "./CatalogTabs";

describe("abas de produtos", () => {
  it("separa cadastro comercial e receitas da semana", () => {
    render(<CatalogTabs current="recipes" />);
    expect(screen.getByRole("link", { name: "Receitas da semana" })).toHaveAttribute(
      "href",
      "/admin/produtos/receitas",
    );
    expect(screen.getByRole("link", { name: "Receitas da semana" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Vitrine e cadastro" })).toHaveAttribute("href", "/admin/produtos");
  });
});
