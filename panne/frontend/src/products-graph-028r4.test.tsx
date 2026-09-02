import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ORG_A,
  ORG_B,
  PRODUCT_ID,
  PRODUCT_PURCHASED_ID,
  PRODUCT_READY_ID,
  RECIPE_ID,
  productReadyFixture,
} from "./api/fixtures";
import { describeProductStructure, graphItemKind, graphItemKindLabel } from "./products/productStructureModel";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

function extraRecipeItems(count: number) {
  return Array.from({ length: count }, (_, index) => ({
    ingredient_id: `eeeeeeee-eeee-eeee-eeee-${String(index).padStart(12, "0")}`,
    code: `CMP-${index + 1}`,
    display_name: `Componente extra ${index + 1}`,
    quantity: "10",
    unit: "g",
    role: index === 0 ? "component" : "ingredient",
    is_flour_basis: false,
  }));
}

describe("CURSOR-028-R4 grafo de produtos", () => {
  it("mostra prévia exemplificativa sem seleção e sem links", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/produtos");

    expect(
      await screen.findByRole("heading", { name: "Como a estrutura de um produto aparece" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Exemplo ilustrativo")).toBeInTheDocument();
    expect(
      screen.getByText("Selecione um produto na tabela para substituir esta prévia pela estrutura cadastrada."),
    ).toBeInTheDocument();

    const preview = screen.getByRole("heading", { name: "Como a estrutura de um produto aparece" }).closest(
      "section",
    );
    expect(preview).toBeTruthy();
    expect(within(preview as HTMLElement).queryAllByRole("link")).toHaveLength(0);
    expect(within(preview as HTMLElement).queryByText(/versão/i)).not.toBeInTheDocument();
    expect(within(preview as HTMLElement).queryByText(/\d+\s*g/)).not.toBeInTheDocument();

    const radios = await screen.findAllByRole("radio", { name: /Visualizar estrutura de / });
    expect(radios.length).toBeGreaterThan(0);
    for (const radio of radios) {
      expect(radio).not.toBeChecked();
    }
  });

  it("substitui a prévia pela estrutura real ao selecionar um produto produzido", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/produtos");

    await user.click(await screen.findByRole("radio", { name: "Visualizar estrutura de Pão francês (Demo)" }));

    expect(await screen.findByRole("heading", { name: "Estrutura cadastrada" })).toBeInTheDocument();
    expect(screen.queryByText("Exemplo ilustrativo")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Produtos" })).toBeInTheDocument();

    const graph = screen.getByRole("heading", { name: "Estrutura cadastrada" }).closest("section") as HTMLElement;
    expect(within(graph).getByText("Farinha de trigo tipo 1")).toBeInTheDocument();
    expect(within(graph).getByText("1.000 g")).toBeInTheDocument();
    expect(within(graph).getByText("Versão 1")).toBeInTheDocument();
    expect(within(graph).getByText("Ativa · Publicada")).toBeInTheDocument();
    expect(within(graph).queryByText(/\b(published|produced|ingredient)\b/i)).not.toBeInTheDocument();

    expect(within(graph).getByRole("link", { name: "Produto Pão francês (Demo)" })).toHaveAttribute(
      "href",
      `/produtos/${PRODUCT_READY_ID}`,
    );
    expect(within(graph).getByRole("link", { name: "Receita técnica Pão francês (Demo)" })).toHaveAttribute(
      "href",
      expect.stringContaining(`/receitas/${RECIPE_ID}`),
    );
    expect(within(graph).getByRole("link", { name: "Ingrediente Farinha de trigo tipo 1" })).toHaveAttribute(
      "href",
      expect.stringContaining("/componentes/ingredientes/eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
    );
  });

  it("troca o grafo ao mudar o produto e restaura a prévia quando o filtro remove a seleção", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/produtos");

    await user.click(await screen.findByRole("radio", { name: "Visualizar estrutura de Pão francês (Demo)" }));
    expect(await screen.findByText("Farinha de trigo tipo 1")).toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: "Visualizar estrutura de Pão tradicional" }));
    expect(await screen.findByText("Receita técnica não cadastrada.")).toBeInTheDocument();
    expect(screen.queryByText("Farinha de trigo tipo 1")).not.toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: "Visualizar estrutura de Refrigerante de cola" }));
    expect(await screen.findByText("Produção não se aplica a produto comprado.")).toBeInTheDocument();
    expect(screen.queryByText("Receita técnica não cadastrada.")).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Modalidade"), "produced");
    await user.click(screen.getByRole("button", { name: "Filtrar" }));

    expect(
      await screen.findByRole("heading", { name: "Como a estrutura de um produto aparece" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Produção não se aplica a produto comprado.")).not.toBeInTheDocument();
    expect(screen.queryByText("Refrigerante de cola")).not.toBeInTheDocument();
    for (const radio of screen.getAllByRole("radio", { name: /Visualizar estrutura de / })) {
      expect(radio).not.toBeChecked();
    }
  });

  it("restaura a prévia ao trocar de organização", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/produtos");

    await user.click(await screen.findByRole("radio", { name: "Visualizar estrutura de Pão francês (Demo)" }));
    expect(await screen.findByText("Farinha de trigo tipo 1")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    expect(
      await screen.findByRole("heading", { name: "Como a estrutura de um produto aparece" }),
    ).toBeInTheDocument();
  });

  it("mostra modo de preparo ausente sem tratar o produto como pronto", async () => {
    installApiMock({
      [`/products/${PRODUCT_READY_ID}`]: () =>
        json({
          data: {
            ...productReadyFixture,
            current_recipe: { ...productReadyFixture.current_recipe, steps: [] },
          },
          row_version: 1,
        }),
    });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/produtos");

    await user.click(await screen.findByRole("radio", { name: "Visualizar estrutura de Pão francês (Demo)" }));
    expect(await screen.findByText("Modo de preparo ainda não registrado.")).toBeInTheDocument();
    const graph = screen.getByRole("heading", { name: "Estrutura cadastrada" }).closest("section") as HTMLElement;
    expect(within(graph).queryByText("Pronto para produzir")).not.toBeInTheDocument();
    expect(within(graph).getByText("Farinha de trigo tipo 1")).toBeInTheDocument();
  });

  it("limita componentes visíveis e aponta o restante para a receita", async () => {
    const items = [...(productReadyFixture.current_recipe?.items ?? []), ...extraRecipeItems(6)];
    installApiMock({
      [`/products/${PRODUCT_READY_ID}`]: () =>
        json({
          data: { ...productReadyFixture, current_recipe: { ...productReadyFixture.current_recipe, items } },
          row_version: 1,
        }),
    });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/produtos");

    await user.click(await screen.findByRole("radio", { name: "Visualizar estrutura de Pão francês (Demo)" }));
    expect(await screen.findByRole("link", { name: "+ 2 componentes na receita" })).toHaveAttribute(
      "href",
      expect.stringContaining(`/receitas/${RECIPE_ID}`),
    );
    expect(screen.queryByText("Componente extra 6")).not.toBeInTheDocument();
  });

  it("mantém a tabela utilizável quando a estrutura falha", async () => {
    let fail = true;
    installApiMock({
      [`/products/${PRODUCT_READY_ID}`]: () => {
        if (fail) return json({ message: "falha temporária" }, 500);
        return json({ data: productReadyFixture, row_version: 1 });
      },
    });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/produtos");

    await user.click(await screen.findByRole("radio", { name: "Visualizar estrutura de Pão francês (Demo)" }));
    expect(await screen.findByText("Não foi possível carregar a estrutura deste produto.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir produto" })).toHaveAttribute(
      "href",
      `/produtos/${PRODUCT_READY_ID}`,
    );
    expect(screen.getByRole("link", { name: "Abrir detalhe de Pão tradicional" })).toBeInTheDocument();

    fail = false;
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Farinha de trigo tipo 1")).toBeInTheDocument();
  });
});

describe("modelo do grafo de produtos", () => {
  it("não inventa receita para produto comprado", () => {
    const view = describeProductStructure({
      ...productReadyFixture,
      supply_mode: "purchased",
      current_recipe: productReadyFixture.current_recipe,
    });
    expect(view.kind).toBe("purchased");
  });

  it("usa só a receita retornada pela API", () => {
    const gap = describeProductStructure({
      id: PRODUCT_ID,
      display_name: "Pão tradicional",
      code: "PAO-TRAD",
      supply_mode: "produced",
      current_recipe: null,
    } as never);
    expect(gap.kind).toBe("produced_gap");
    expect(graphItemKindLabel(graphItemKind({ role: "ingredient" }))).toBe("Ingrediente");
    expect(graphItemKindLabel(graphItemKind({ role: "component" }))).toBe("Componente");
  });
});
