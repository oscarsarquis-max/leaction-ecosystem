import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { RECIPE_ID, RECIPE_VERSION_ID } from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("receitas", () => {
  it("mostra o menu Receitas sem links mortos", async () => {
    installApiMock();
    await renderApp("/producao");
    expect(await screen.findByRole("heading", { name: "Quadro de produção" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Receitas" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Produção" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Componentes" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Cadastros" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Gestão" })).not.toBeInTheDocument();
  });

  it("lista receitas com pesquisa, filtros e paginação na URL", async () => {
    installApiMock();
    const { view } = await renderApp("/receitas");
    expect(await screen.findByRole("heading", { name: "Minhas receitas" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Nova receita" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Minhas receitas" })).toBeInTheDocument();
    expect(await screen.findByText("Pão francês")).toBeInTheDocument();
    expect(screen.getAllByText("rascunho").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Pesquisa")).toBeInTheDocument();
    const results = await axe(view.container);
    expect(results.violations).toEqual([]);
  });

  it("cria receita atômica", async () => {
    installApiMock();
    await renderApp("/receitas/novo");
    const user = userEvent.setup();
    expect(await screen.findByRole("heading", { name: "Nova receita" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("Código"), "PAO-9");
    await user.type(screen.getByLabelText("Nome"), "Pão novo");
    await user.click(screen.getByRole("button", { name: "Criar rascunho" }));
    await waitFor(() => {
      expect(vi.mocked(fetch).mock.calls.some(([input]) => String(input).includes("/recipes"))).toBe(
        true,
      );
    });
  });

  it("abre o atelier com componentes, percentual, processo e assistente", async () => {
    installApiMock();
    const { view } = await renderApp(`/receitas/${RECIPE_ID}`);
    expect(await screen.findByRole("heading", { name: "Pão francês" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Componentes" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Percentual do padeiro" })).toBeInTheDocument();
    expect(screen.getByText(/Total de farinha/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Processo" })).toBeInTheDocument();
    expect(screen.getByText(/Mistura/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Rendimento e porção" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Escala" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ensaios" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Nutrição técnica" })).toBeInTheDocument();
    expect(screen.getByText(/Prévia técnica incompleta e não validada regulatoriamente/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Referências" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Revisão e aprovação" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Histórico" })).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Assistente de receita" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Publicar versão" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aprovar" })).toBeInTheDocument();
    expect(screen.getByText("nutrição incompleta")).toBeInTheDocument();
    const results = await axe(view.container);
    expect(results.violations).toEqual([]);
  });

  it("trata versão publicada como imutável e oferece nova versão", async () => {
    installApiMock({
      "/recipes/": () =>
        json({
          data: {
            id: RECIPE_ID,
            code: "PAO-1",
            display_name: "Pão francês",
            status: "active",
            technical_product_id: "tp-1",
            row_version: 2,
            versions: [
              {
                id: RECIPE_VERSION_ID,
                formulation_id: RECIPE_ID,
                version_number: 1,
                status: "published",
                yield_units: 10,
                target_unit_weight_g: "50",
                expected_bake_loss_rate: "0.12",
                notes: null,
                published_at: "2026-08-23T12:00:00Z",
                row_version: 2,
              },
            ],
            identity: {
              id: RECIPE_ID,
              display_name: "Pão francês",
              code: "PAO-1",
              status: "active",
              technical_product_id: "tp-1",
              row_version: 2,
              current_version: { id: RECIPE_VERSION_ID, version_number: 1, status: "published" },
            },
            version: {
              id: RECIPE_VERSION_ID,
              formulation_id: RECIPE_ID,
              version_number: 1,
              status: "published",
              yield_units: 10,
              target_unit_weight_g: "50",
              expected_bake_loss_rate: "0.12",
              notes: null,
              published_at: "2026-08-23T12:00:00Z",
              row_version: 2,
            },
            items: [],
            steps: [],
            bakers: { flour_mass: null, explained_absence: true, items: [] },
            yield: {
              base_net_mass: null,
              yield_units: 10,
              target_unit_weight_g: "50",
              expected_bake_loss_rate: "0.12",
              expected_final_mass_g: "500",
              portion_mass_g: null,
            },
            completeness: { ready_to_publish: false, complete_dossier: false, items: [] },
          },
          row_version: 2,
        }),
    });
    await renderApp(`/receitas/${RECIPE_ID}`);
    expect((await screen.findAllByText("publicado")).length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "Incluir componente" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Criar nova versão" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aposentar" })).toBeInTheDocument();
  });

  it("mostra ficha A4 a partir do payload carregado", async () => {
    installApiMock();
    await renderApp(`/receitas/${RECIPE_ID}/versoes/${RECIPE_VERSION_ID}/ficha`);
    expect(await screen.findByRole("heading", { name: "Ficha técnica" })).toBeInTheDocument();
    expect(screen.getByText(/Prévia técnica incompleta/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Imprimir A4" })).toBeInTheDocument();
    expect(screen.getByText(/Farinha/)).toBeInTheDocument();
  });

  it("mostra conflito quando a versão mudou", async () => {
    installApiMock({
      "/publish": () =>
        json({ code: "versao_conflito", message: "A versão do recurso mudou. Recarregue e tente de novo." }, 409),
    });
    await renderApp(`/receitas/${RECIPE_ID}`);
    const user = userEvent.setup();
    expect(await screen.findByRole("heading", { name: "Pão francês" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Publicar versão" }));
    expect(await screen.findByText(/versão do recurso mudou/i)).toBeInTheDocument();
  });
});
