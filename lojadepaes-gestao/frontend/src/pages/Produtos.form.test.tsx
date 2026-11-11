import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FormProduto } from "./Produtos";

const inicial = {
  nome: "Levain",
  modalidade: "produzido" as const,
  uso_venda: true,
  uso_componente: true,
  cultura_viva: true,
  familia_id: null,
  unidade_venda: "kg" as const,
  unidade_base: "g" as const,
};

describe("formulário do produto", () => {
  it("só componente esconde a unidade de venda e desmarcar componente esconde a cultura viva sem apagar o valor", async () => {
    const usuario = userEvent.setup();
    render(
      <FormProduto
        titulo="Editar produto"
        modalidadeFixa="produzido"
        inicial={inicial}
        familias={[]}
        enviando={false}
        erro={null}
        parecidos={[]}
        onCancelar={vi.fn()}
        onEnviar={vi.fn()}
      />,
    );

    expect(screen.getByRole("checkbox", { name: /Cultura viva/ })).toBeChecked();
    expect(screen.getByText("Levain, massa madre, PFF")).toBeInTheDocument();
    expect(screen.getByText("Unidade de venda")).toBeInTheDocument();

    await usuario.click(screen.getByRole("checkbox", { name: "Venda" }));
    expect(screen.queryByText("Unidade de venda")).not.toBeInTheDocument();

    await usuario.click(screen.getByRole("checkbox", { name: "Componente" }));
    expect(screen.queryByRole("checkbox", { name: /Cultura viva/ })).not.toBeInTheDocument();

    await usuario.click(screen.getByRole("checkbox", { name: "Componente" }));
    expect(screen.getByRole("checkbox", { name: /Cultura viva/ })).toBeChecked();
    await usuario.click(screen.getByRole("checkbox", { name: "Venda" }));
    expect(screen.getByDisplayValue("kg")).toBeInTheDocument();
  });
});
