import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { meFixture, ORG_A, PRODUCT_ID, PRODUCT_READY_ID } from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

function meWithout(codes: string[]) {
  return {
    ...meFixture,
    associations: meFixture.associations.map((row) =>
      row.organization_id === ORG_A
        ? { ...row, permissions: row.permissions.filter((code) => !codes.includes(code)) }
        : row,
    ),
    permissions: meFixture.permissions.filter((code) => !codes.includes(code)),
  };
}

describe("Produto operacional", () => {
  it("lista densa com busca, modalidade, família e situação reais", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/produtos");

    const table = within(await screen.findByRole("table", { name: "Produtos da organização" }));
    expect(table.getByText("Pão francês (Demo)")).toBeInTheDocument();
    expect(table.getByText("Pronto para produzir")).toBeInTheDocument();
    expect(table.getByText("Produção bloqueada")).toBeInTheDocument();
    expect(table.getByText("Sem receita vigente")).toBeInTheDocument();
    expect(table.getByRole("link", { name: "Abrir detalhe de Pão tradicional" })).toBeInTheDocument();

    await user.type(screen.getByLabelText("Pesquisa"), "PAO-FR");
    await user.selectOptions(screen.getByLabelText("Modalidade"), "produced");
    await user.selectOptions(screen.getByLabelText("Família"), "Pães");
    await user.selectOptions(screen.getByLabelText("Situação"), "active");
    await user.click(screen.getByRole("button", { name: "Filtrar" }));

    expect(await screen.findByText("Pão francês (Demo)")).toBeInTheDocument();
    expect(screen.queryByText("Refrigerante de cola")).not.toBeInTheDocument();
    expect(screen.queryByText("Custo parcial")).not.toBeInTheDocument();
  });

  it("mostra o detalhe produzido com receita, componentes e preparo reais", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp(`/produtos/${PRODUCT_READY_ID}`);

    expect(await screen.findByRole("heading", { name: "Pão francês (Demo)" })).toBeInTheDocument();
    expect(screen.getByText("3.300 g de massa")).toBeInTheDocument();
    expect(screen.getByText("Farinha de trigo tipo 1")).toBeInTheDocument();
    expect(screen.getByText("1.000 g")).toBeInTheDocument();
    expect(screen.getByText("650 g")).toBeInTheDocument();
    expect(screen.getAllByText(/Misturar/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/~66/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir produção deste produto" })).toHaveAttribute(
      "href",
      `/producao?product_id=${PRODUCT_READY_ID}`,
    );
    expect(screen.getByRole("link", { name: "Abrir receita" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Imprimir ficha operacional" })).toBeInTheDocument();
    expect(screen.getByText("Publicado em")).toBeInTheDocument();
    expect(screen.queryByText("Vigência")).not.toBeInTheDocument();
  });

  it("explica produzido sem receita vigente e não inventa percentual", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp(`/produtos/${PRODUCT_ID}`);

    expect(await screen.findByRole("heading", { name: "Pão tradicional" })).toBeInTheDocument();
    expect(screen.getByText(/produção fica bloqueada até haver receita vigente/i)).toBeInTheDocument();
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Abrir produção deste produto" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Imprimir ficha operacional" })).not.toBeInTheDocument();
  });

  it("volta do produto à lista preservando busca e filtros", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/produtos?q=PAO-FR&supply_mode=produced");

    await user.click(await screen.findByRole("link", { name: "Abrir detalhe de Pão francês (Demo)" }));
    expect(await screen.findByRole("heading", { name: "Pão francês (Demo)" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voltar" })).toHaveAttribute(
      "href",
      "/produtos?q=PAO-FR&supply_mode=produced",
    );
    expect(
      screen
        .getAllByRole("link", { name: "Voltar ao fluxo produtivo" })
        .some((link) => link.getAttribute("href") === "/fluxo"),
    ).toBe(true);

    await user.click(screen.getByRole("link", { name: "Voltar" }));
    expect(await screen.findByRole("heading", { name: "Produtos" })).toBeInTheDocument();
    expect(screen.getByLabelText("Pesquisa")).toHaveValue("PAO-FR");
  });

  it("volta do ingrediente ao mesmo produto", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp(`/produtos/${PRODUCT_READY_ID}`);

    const ingredientLinks = await screen.findAllByRole("link", { name: "Abrir ingrediente" });
    await user.click(ingredientLinks[0]);
    expect(await screen.findByRole("link", { name: "Voltar ao produto" })).toHaveAttribute(
      "href",
      `/produtos/${PRODUCT_READY_ID}`,
    );
  });

  it("oculta ações sem permissão", async () => {
    installApiMock({ "/api/v1/me": () => json(meWithout(["costing.read", "product.update", "labeling.read"])) });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp(`/produtos/${PRODUCT_READY_ID}`);

    expect(await screen.findByRole("heading", { name: "Pão francês (Demo)" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Analisar custos" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Editar dados do produto" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ver prévia da rotulagem" })).not.toBeInTheDocument();
  });

  it("no recorte estreito empilha identidade e mantém a próxima ação", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: (query: string) => ({
        matches: query.includes("720"),
        media: query,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
        addListener: () => undefined,
        removeListener: () => undefined,
      }),
    });
    await renderApp(`/produtos/${PRODUCT_READY_ID}`);

    expect(await screen.findByRole("heading", { name: "Pão francês (Demo)" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir produção deste produto" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abrir Gigio" })).toBeInTheDocument();
  });

  it("mostra prévia humana da rotulagem sem enums crus", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp(`/produtos/${PRODUCT_READY_ID}`);

    await user.click(await screen.findByRole("button", { name: "Ver prévia da rotulagem" }));
    const dialog = screen.getByRole("dialog", { name: "Prévia da rotulagem" });
    expect(dialog).toHaveTextContent("Prévia para revisão — não aprovada");
    expect(dialog).toHaveTextContent("Valor energético");
    expect(dialog).not.toHaveTextContent("energy_kcal");
    expect(dialog).not.toHaveTextContent("total_sugars");
    expect(dialog).toHaveTextContent("Completar dossiê");
  });

  it("unifica o catálogo no menu e não mostra a trilha nas telas de produto", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/produtos");

    expect(await screen.findByRole("heading", { name: "Produtos" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Panne" })).toHaveAttribute("href", "/inicio");
    expect(screen.getByRole("navigation", { name: "Principal" })).toHaveTextContent("Produtos e receitas");
    expect(screen.getByRole("navigation", { name: "Principal" })).toHaveTextContent("Estoque e insumos");
    expect(screen.getByRole("navigation", { name: "Submenu" })).toHaveTextContent("Ingredientes e componentes");
    expect(screen.getByRole("navigation", { name: "Submenu" })).toHaveTextContent("Receitas técnicas");
    expect(screen.queryByRole("link", { name: "Próxima etapa" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Anterior" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abrir Gigio" })).toBeInTheDocument();
  });
});
