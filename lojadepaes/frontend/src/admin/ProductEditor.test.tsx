import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ProductEditor } from "./ProductEditor";

describe("editor de produtos", () => {
  it("mostra salvar rascunho e publicar, com variações em português", () => {
    render(<ProductEditor productId={null} onBack={() => undefined} onSaved={() => undefined} onDeleted={() => undefined} />);
    expect(screen.getByRole("heading", { name: "Novo produto" })).toBeInTheDocument();
    const name = screen.getByRole("textbox", { name: "Nome do pão" });
    const summary = screen.getByRole("textbox", { name: /Descrição curta da vitrine/ });
    expect(name.compareDocumentPosition(summary) & Node.DOCUMENT_POSITION_FOLLOWING).toBeGreaterThan(0);
    expect(
      screen.getByText("Apresente o sabor, a textura e as características do seu pão. Este texto aparece abaixo do nome na vitrine."),
    ).toBeInTheDocument();
    expect(screen.getByText("0/280")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Configuração de produção" })).toBeInTheDocument();
    expect(screen.getByLabelText("Tipo de pão da fornada")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /Texto alternativo da imagem/ })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /Legenda da foto — aparece na vitrine/ })).toBeInTheDocument();
    expect(screen.getByText("Ainda não há legenda visível na vitrine.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Usar também como legenda" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Sem vínculo — revisar depois/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /gerenciar receitas/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salvar rascunho" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Publicar produto" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apagar rascunho" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apagar" })).not.toBeInTheDocument();
    expect(screen.getByText(/quantidade de pães físicos só entra na capacidade/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Pães físicos por unidade comercial")).toBeInTheDocument();
    expect(screen.getByLabelText("Preço (ex.: 24,90)")).toBeInTheDocument();
  });

  it("atualiza o contador da descrição curta da vitrine", async () => {
    const user = userEvent.setup();
    render(<ProductEditor productId={null} onBack={() => undefined} onSaved={() => undefined} onDeleted={() => undefined} />);
    await user.type(
      screen.getByRole("textbox", { name: /Descrição curta da vitrine/ }),
      "Miolo úmido e crosta dourada.",
    );
    expect(screen.getByText("29/280")).toBeInTheDocument();
  });

  it("copia o texto alternativo para a legenda só quando o administrador pede", async () => {
    const user = userEvent.setup();
    render(<ProductEditor productId={null} onBack={() => undefined} onSaved={() => undefined} onDeleted={() => undefined} />);
    await user.type(
      screen.getByRole("textbox", { name: /Texto alternativo da imagem/ }),
      "Pão rústico sobre pano de linho",
    );
    expect(screen.getByRole("button", { name: "Usar também como legenda" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /Legenda da foto — aparece na vitrine/ })).toHaveValue("");
    await user.click(screen.getByRole("button", { name: "Usar também como legenda" }));
    expect(screen.getByRole("textbox", { name: /Legenda da foto — aparece na vitrine/ })).toHaveValue(
      "Pão rústico sobre pano de linho",
    );
    expect(screen.queryByText("Ainda não há legenda visível na vitrine.")).not.toBeInTheDocument();
  });

  it("reordena ingredientes com controles acessíveis", async () => {
    const user = userEvent.setup();
    render(<ProductEditor productId={null} onBack={() => undefined} onSaved={() => undefined} onDeleted={() => undefined} />);
    await user.click(screen.getByRole("button", { name: "Descer Farinha de trigo" }));
    const flour = screen.getByDisplayValue("Farinha de trigo");
    const water = screen.getByDisplayValue("Água");
    expect(water.compareDocumentPosition(flour) & Node.DOCUMENT_POSITION_FOLLOWING).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Subir Farinha de trigo" })).toBeEnabled();
  });
});
