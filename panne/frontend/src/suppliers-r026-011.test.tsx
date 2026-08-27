import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  activeItemsSummary,
  priceSourceLabel,
  supplierItemStatusLabel,
  supplierStatusLabel,
} from "./language/suppliers";
import { formatMoneyAmount, formatPackageQuantity } from "./language/ingredients";
import { ORG_B } from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

describe("R026-011 fornecedores, itens e preços", () => {
  it("catálogos humanos de situação e origem", () => {
    expect(supplierStatusLabel("active")).toBe("Ativo");
    expect(supplierStatusLabel("inactive")).toBe("Inativo");
    expect(supplierItemStatusLabel("active")).toBe("Ativo");
    expect(activeItemsSummary(0)).toBe("Nenhum item ativo");
    expect(activeItemsSummary(1)).toBe("1 item ativo");
    expect(activeItemsSummary(3)).toBe("3 itens ativos");
    expect(priceSourceLabel("seed-demo")).toBe("Cadastro de demonstração");
    expect(priceSourceLabel("receipt:abc")).toBe("Recebimento");
    expect(priceSourceLabel(null)).toBe("Origem não informada");
    expect(formatPackageQuantity("25", { code: "kg", symbol: "kg" })).toBe("25 kg");
    expect(formatMoneyAmount("13.00", "BRL")).toMatch(/R\$\s*13,00/);
  });

  it("lista com links, Detalhe, situação humana e contagem", async () => {
    installApiMock();
    await renderApp("/componentes/fornecedores");
    expect(await screen.findByRole("heading", { name: "Fornecedores e itens" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Abrir detalhe de Moinho Demo" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir detalhe do código FOR-MOINHO" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Detalhe de Moinho Demo" })).toBeInTheDocument();
    expect(screen.getAllByText("Ativo").length).toBeGreaterThan(0);
    expect(screen.getByText("Nenhum item ativo")).toBeInTheDocument();
    expect(screen.getByText(/Os preços pertencem aos itens/)).toBeInTheDocument();
    expect(screen.queryByText(/\bBRL\b/)).not.toBeInTheDocument();
  });

  it("abre Moinho Demo com SKU-FAR-25, embalagem e último preço", async () => {
    installApiMock();
    const user = userEvent.setup();
    await renderApp("/componentes/fornecedores");
    await user.click(await screen.findByRole("link", { name: "Detalhe de Moinho Demo" }));
    expect(await screen.findByRole("heading", { name: "Moinho Demo" })).toBeInTheDocument();
    expect(screen.getByText("SKU-FAR-25")).toBeInTheDocument();
    expect(screen.getByText("Farinha de trigo tipo 1 (Demo)")).toBeInTheDocument();
    expect(screen.getByText("25 kg")).toBeInTheDocument();
    expect(screen.getByText(/R\$\s*13,00/)).toBeInTheDocument();
    expect(screen.queryByText(/\bBRL\b/)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Histórico" }));
    const history = await screen.findByLabelText("Histórico de preços");
    expect(within(history).getByText(/R\$\s*13,00/)).toBeInTheDocument();
    expect(within(history).getByText(/R\$\s*13,10/)).toBeInTheDocument();
    expect(within(history).getByText(/R\$\s*12,50/)).toBeInTheDocument();
    expect(within(history).getByText("Mais recente")).toBeInTheDocument();
    expect(within(history).getByText("Recebimento")).toBeInTheDocument();
    expect(within(history).getAllByText("Cadastro de demonstração").length).toBe(2);
  });

  it("troca de organização limpa o detalhe do fornecedor", async () => {
    installApiMock({
      [ORG_B]: () => json({ code: "nao_encontrado", message: "Recurso não encontrado" }, 404),
    });
    await renderApp("/componentes/fornecedores/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb");
    expect(await screen.findByRole("heading", { name: "Moinho Demo" })).toBeInTheDocument();
    expect(screen.getByText("SKU-FAR-25")).toBeInTheDocument();
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    expect(
      await screen.findByRole("heading", { name: /Não foi possível carregar|Recurso/i }),
    ).toBeInTheDocument();
    expect(screen.queryByText("SKU-FAR-25")).not.toBeInTheDocument();
    expect(screen.queryByText(/R\$\s*13,00/)).not.toBeInTheDocument();
  });
});
