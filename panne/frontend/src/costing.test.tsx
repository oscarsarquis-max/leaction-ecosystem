import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { CALC_ID, ORDER_ID, PRODUCT_ID, costingCalculationFixture, operatorMeFixture } from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("custos e preços", () => {
  it("mostra dashboard econômico com navegação interna", async () => {
    installApiMock();
    const { view } = await renderApp("/gestao/custos");
    expect(await screen.findByRole("heading", { name: "Custos, preços e margem" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Gestão" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Visão geral" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Formação do custo" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Previsto vs realizado" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Políticas e premissas" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Preços e histórico" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Calculadora" }).length).toBeGreaterThan(0);
    expect(screen.queryByRole("link", { name: "Cadastros" })).not.toBeInTheDocument();
    expect(document.body.textContent).toMatch(/Quanto custa|preço está vigente|Simulação não grava/);
  });

  it("lista políticas, vazio, carregamento e erro", async () => {
    installApiMock();
    await renderApp("/gestao/custos/politicas");
    expect(await screen.findByRole("heading", { name: "Políticas e premissas" })).toBeInTheDocument();
    expect(await screen.findByText("Markup organização")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ver histórico" })).toBeInTheDocument();

    installApiMock({
      "/pricing/markup-policies": (_url, request) => {
        if (request.method === "GET") {
          return json({ code: "indisponivel", message: "API fora" }, 503);
        }
        return json({ detail: "nao_encontrado" }, 404);
      },
    });
    await renderApp("/gestao/custos/politicas");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/API indisponível/i);
    expect(alert).toHaveTextContent(/API fora/i);
  });

  it("mostra cálculo parcial, lacunas e composição humana com calculadora", async () => {
    installApiMock();
    const { view } = await renderApp(`/gestao/custos/calculos/${CALC_ID}`);
    expect(await screen.findByRole("heading", { name: "Pão tradicional" })).toBeInTheDocument();
    expect(screen.getAllByText(/parcial|Custo de ingredientes/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Sem rendimento vendável|Sem preço vigente|Composição conhecida|Farinha/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Farinha de trigo tipo 1/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Sal refinado/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/\bingredient\b/)).not.toBeInTheDocument();
    expect(screen.queryByText(/\bcurrent_price\b/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Simular markup 2x/i })).not.toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "Calculadora de preço" }).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Simulação sobre custo parcial|Total parcial|custo parcial/i).length).toBeGreaterThan(0);
    expect(document.body.textContent).toMatch(/Ausência não é zero|ausente|Sem informação/i);
    expect(await axe(view.container)).toEqual(expect.objectContaining({ violations: [] }));
  });

  it("calculadora bidirecional na decisão sem persistir", async () => {
    installApiMock();
    const user = userEvent.setup();
    await renderApp(`/gestao/custos/decisao?calculo=${CALC_ID}`);
    expect(await screen.findByRole("heading", { name: "Pão tradicional" })).toBeInTheDocument();
    expect(screen.getAllByText(/Margem sobre o custo conhecido/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/dados insuficientes/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Margem bruta$/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Cards resumem/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/cascata omitida/i)).not.toBeInTheDocument();
    expect(document.body.textContent).toMatch(/Analise a formação do custo/);
    const markupInputs = screen.getAllByLabelText(/Markup \(fator\)/);
    await user.clear(markupInputs[0]);
    await user.type(markupInputs[0], "3");
    expect(screen.getAllByText(/R\$\s*37,50/).length).toBeGreaterThan(0);
    const priceInputs = screen.getAllByLabelText(/Preço desejado/);
    await user.clear(priceInputs[0]);
    await user.type(priceInputs[0], "30");
    expect(screen.getAllByText(/2,40×|2,4×/).length).toBeGreaterThan(0);
    expect(
      vi.mocked(fetch).mock.calls.some(([input]) => String(input).includes("/simulations")),
    ).toBe(false);
  });

  it("simula markup, margem e compara canais", async () => {
    installApiMock();
    await renderApp("/gestao/custos/simulacoes");
    const user = userEvent.setup();
    expect(await screen.findByRole("heading", { name: "Simulações persistidas" })).toBeInTheDocument();
    expect(screen.getAllByText(/Markup incide sobre o custo|calculadora da formação/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Balcão próprio/i).length).toBeGreaterThan(0);
    await user.selectOptions(screen.getByLabelText("Fórmula"), "gross_margin");
    await user.selectOptions(screen.getByLabelText("Canal"), "wholesale");
    await user.click(screen.getByRole("button", { name: "Calcular e gravar simulação" }));
    await waitFor(() => {
      expect(
        vi.mocked(fetch).mock.calls.some(([input]) => String(input).includes("/simulations")),
      ).toBe(true);
    });
  });

  it("exige confirmação humana e recarrega em 409", async () => {
    const completeCalc = {
      ...costingCalculationFixture,
      completeness: "complete",
      total_is_partial: false,
      sellable_unit_amount: "6.00",
      technical_product_id: PRODUCT_ID,
      cost_base: {
        ...costingCalculationFixture.cost_base,
        amount: "6.00",
        incomplete: false,
        origin: "sellable_unit",
        origin_label: "Custo por unidade vendável",
      },
      cost_scope: {
        ...costingCalculationFixture.cost_scope,
        ingredients_complete: true,
        production_complete: true,
        price_definitive_allowed: true,
        completeness_label: "Custo total de produção completo",
      },
    };
    installApiMock({
      [`/costing/calculations/${CALC_ID}`]: () => json({ data: completeCalc }),
      "/pricing/practiced": (url, request) => {
        if (url.pathname.includes("/decide")) {
          return json(
            { code: "versao_conflito", message: "A versão do recurso mudou. Recarregue e tente de novo." },
            409,
          );
        }
        if (request.method === "GET") {
          return json({
            items: [
              {
                id: "price-active-1",
                technical_product_id: PRODUCT_ID,
                channel: "own_counter",
                amount: "15.00",
                status: "active",
                row_version: 3,
              },
            ],
          });
        }
        return json({
          data: {
            id: "price-draft-new",
            technical_product_id: PRODUCT_ID,
            channel: "own_counter",
            amount: "12.00",
            status: "draft",
            row_version: 1,
          },
          row_version: 1,
        });
      },
    });
    const user = userEvent.setup();
    await renderApp(`/gestao/custos/decisao?calculo=${CALC_ID}`);
    expect(await screen.findByRole("heading", { name: "Pão tradicional" })).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: "Aplicar novo preço…" }));
    expect(await screen.findByRole("dialog", { name: "Confirmar aplicação de preço" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Confirmar e criar decisão" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/Conflito|recarregado|não foi repetida/i);
  });

  it("nega custos ao padeiro e não mostra valores no quadro operacional", async () => {
    installApiMock({
      "/api/v1/me": () => json(operatorMeFixture),
    });
    await renderApp("/gestao/custos");
    expect(await screen.findByRole("alert")).toHaveTextContent(/permissão/i);
    expect(screen.queryByRole("heading", { name: "Custos, preços e margem" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Gestão" })).not.toBeInTheDocument();

    await renderApp(`/producao/ordens/${ORDER_ID}/executar`);
    expect(await screen.findByRole("heading", { name: /Executar/ })).toBeInTheDocument();
    expect(document.body.textContent?.toLowerCase()).not.toMatch(/custo previsto|preço sugerido|margem bruta/);
  });
});
