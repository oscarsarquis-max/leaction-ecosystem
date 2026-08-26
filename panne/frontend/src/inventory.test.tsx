import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { operatorMeFixture } from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("estoque e compras", () => {
  it("mostra Componentes com Estoque e Lotes e Gestão com Compras", async () => {
    installApiMock();
    const { view } = await renderApp("/componentes/estoque");
    expect(await screen.findByRole("heading", { name: "Estoque" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Componentes" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Posição" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Reservas" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Movimentações" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Validades" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Separação" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Gestão" })).toBeInTheDocument();
    expect(await axe(view.container)).toEqual(expect.objectContaining({ violations: [] }));
  });

  it("mostra posição, lotes, reservas e validade", async () => {
    installApiMock();
    const position = await renderApp("/componentes/estoque/posicao");
    expect(await screen.findByRole("heading", { name: "Posição de estoque" })).toBeInTheDocument();
    expect(screen.getByText("800")).toBeInTheDocument();
    expect(screen.getByText("Farinha de trigo tipo 1")).toBeInTheDocument();
    position.view.unmount();
    await renderApp("/componentes/lotes");
    expect(await screen.findByRole("heading", { name: "Lotes e validade" })).toBeInTheDocument();
    expect(screen.getByText("LOT-000001")).toBeInTheDocument();
    await renderApp("/componentes/estoque/reservas");
    expect(await screen.findByText(/adoção histórica/)).toBeInTheDocument();
  });

  it("mostra inventário, necessidades, cotações e pedidos", async () => {
    installApiMock();
    await renderApp("/gestao/inventarios");
    expect(await screen.findByRole("heading", { name: "Inventários" })).toBeInTheDocument();
    expect(screen.getByText(/divergência -10/)).toBeInTheDocument();
    await renderApp("/gestao/compras/necessidades");
    expect(await screen.findByRole("heading", { name: "Necessidades" })).toBeInTheDocument();
    expect(screen.getByText(/Assistente de reposição/)).toBeInTheDocument();
    await renderApp("/gestao/compras/cotacoes");
    const user = userEvent.setup();
    expect(await screen.findByRole("heading", { name: "Cotações" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Comparar" }));
    expect(await screen.findByText("não")).toBeInTheDocument();
    await renderApp("/gestao/compras/pedidos");
    expect(await screen.findByRole("heading", { name: "Pedidos" })).toBeInTheDocument();
    await renderApp("/gestao/compras/recebimentos");
    expect(await screen.findByRole("heading", { name: "Recebimentos" })).toBeInTheDocument();
    await renderApp("/gestao/compras/devolucoes");
    expect(await screen.findByRole("heading", { name: "Devoluções" })).toBeInTheDocument();
  });

  it("recarrega em 409 e oculta preço do padeiro", async () => {
    installApiMock({
      "/inventory/balances": () => json({ code: "conflito", message: "versão em conflito" }, 409),
    });
    await renderApp("/componentes/estoque/posicao");
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    installApiMock({
      "/api/v1/me": () => json(operatorMeFixture),
    });
    await renderApp("/gestao/compras/pedidos");
    expect(screen.queryByRole("heading", { name: "Pedidos" })).not.toBeInTheDocument();
    expect(screen.queryByText("0.02")).not.toBeInTheDocument();
  });
});
