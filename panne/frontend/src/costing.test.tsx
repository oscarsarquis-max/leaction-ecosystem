import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { CALC_ID, ORDER_ID, operatorMeFixture } from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("custos e preços", () => {
  it("mostra Gestão com subáreas e vocabulário distinto", async () => {
    installApiMock();
    const { view } = await renderApp("/gestao/custos");
    expect(await screen.findByRole("heading", { name: "Custos e preços" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Gestão" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Políticas de custeio" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Custos previstos" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Custos realizados" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Simulações" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Preços praticados" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Cadastros" })).not.toBeInTheDocument();
    expect(document.body.textContent).toMatch(/Markup não é margem bruta/);
    expect(await axe(view.container)).toEqual(expect.objectContaining({ violations: [] }));
  });

  it("lista políticas, vazio, carregamento e erro", async () => {
    installApiMock();
    await renderApp("/gestao/custos/politicas");
    expect(await screen.findByRole("heading", { name: "Políticas de custeio" })).toBeInTheDocument();
    expect(screen.getByText("Custeio padrão")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Criar política" })).toBeInTheDocument();

    installApiMock({
      "/costing/policies": () => json({ items: [] }),
    });
    await renderApp("/gestao/custos/politicas");
    expect(await screen.findByText("Não há políticas nesta organização.")).toBeInTheDocument();

    installApiMock({
      "/costing/policies": () => json({ code: "indisponivel", message: "API fora" }, 503),
    });
    await renderApp("/gestao/custos/politicas");
    expect(await screen.findByRole("alert")).toHaveTextContent("API fora");
  });

  it("mostra cálculo parcial, lacunas e composição", async () => {
    installApiMock();
    const { view } = await renderApp(`/gestao/custos/calculos/${CALC_ID}`);
    expect(await screen.findByRole("heading", { name: "Cálculo de custo" })).toBeInTheDocument();
    expect(screen.getByText("parcial")).toBeInTheDocument();
    expect(screen.getByText(/Sem rendimento vendável confiável/)).toBeInTheDocument();
    expect(screen.getAllByText(/ingredient/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Ausência não é zero/)).toBeInTheDocument();
    expect(await axe(view.container)).toEqual(expect.objectContaining({ violations: [] }));
  });

  it("simula markup, margem e compara canais", async () => {
    installApiMock();
    await renderApp("/gestao/custos/simulacoes");
    const user = userEvent.setup();
    expect(await screen.findByRole("heading", { name: "Simulações" })).toBeInTheDocument();
    expect(screen.getAllByText(/Markup incide sobre o custo/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("balcão próprio").length).toBeGreaterThan(0);
    await user.selectOptions(screen.getByLabelText("Fórmula"), "gross_margin");
    await user.selectOptions(screen.getByLabelText("Canal"), "wholesale");
    await user.click(screen.getByRole("button", { name: "Calcular simulação" }));
    await waitFor(() => {
      expect(
        vi.mocked(fetch).mock.calls.some(([input]) => String(input).includes("/simulations")),
      ).toBe(true);
    });
  });

  it("exige confirmação humana e recarrega em 409", async () => {
    installApiMock({
      "/decide": () => json({ code: "conflito", message: "versão em conflito" }, 409),
    });
    await renderApp("/gestao/custos/precos");
    const user = userEvent.setup();
    expect(await screen.findByRole("heading", { name: "Preços praticados" })).toBeInTheDocument();
    await user.click(screen.getByRole("checkbox", { name: /Confirmação reforçada/ }));
    await user.click(screen.getByRole("button", { name: "Confirmar publicação" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/versão mudou|Recarregue/i);
  });

  it("nega custos ao padeiro e não mostra valores no quadro operacional", async () => {
    installApiMock({
      "/api/v1/me": () => json(operatorMeFixture),
    });
    await renderApp("/gestao/custos");
    expect(await screen.findByRole("alert")).toHaveTextContent(/permissão/i);
    expect(screen.queryByRole("heading", { name: "Custos e preços" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Gestão" })).not.toBeInTheDocument();

    await renderApp(`/producao/ordens/${ORDER_ID}/executar`);
    expect(await screen.findByRole("heading", { name: /Executar/ })).toBeInTheDocument();
    expect(document.body.textContent?.toLowerCase()).not.toMatch(/custo previsto|preço sugerido|margem bruta/);
  });
});
