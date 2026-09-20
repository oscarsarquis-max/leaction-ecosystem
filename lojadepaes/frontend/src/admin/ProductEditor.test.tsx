import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ProductEditor } from "./ProductEditor";

describe("editor de produtos", () => {
  it("mostra salvar rascunho e publicar, com variações em português", () => {
    render(<ProductEditor productId={null} onBack={() => undefined} onSaved={() => undefined} />);
    expect(screen.getByRole("heading", { name: "Novo produto" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salvar rascunho" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Publicar produto" })).toBeInTheDocument();
    expect(screen.getByText(/duas unidades de 500 g/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Preço (ex.: 24,90)")).toBeInTheDocument();
  });

  it("reordena ingredientes com controles acessíveis", async () => {
    const user = userEvent.setup();
    render(<ProductEditor productId={null} onBack={() => undefined} onSaved={() => undefined} />);
    await user.click(screen.getByRole("button", { name: "Descer Farinha de trigo" }));
    const flour = screen.getByDisplayValue("Farinha de trigo");
    const water = screen.getByDisplayValue("Água");
    expect(water.compareDocumentPosition(flour) & Node.DOCUMENT_POSITION_FOLLOWING).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Subir Farinha de trigo" })).toBeEnabled();
  });
});
