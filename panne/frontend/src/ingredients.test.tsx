import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { meFixture, ORG_B } from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("componentes e shell", () => {
  it("mostra logo depois do login e não cria links mortos", async () => {
    installApiMock();
    await renderApp("/producao");
    expect(await screen.findByRole("heading", { name: "Quadro de produção" })).toBeInTheDocument();
    const brand = screen.getByRole("link", { name: "Panne" });
    expect(brand).toBeInTheDocument();
    expect(brand.querySelector("img.horizontal")).toHaveAttribute(
      "src",
      expect.stringContaining("horizontal"),
    );
    expect(screen.getByRole("link", { name: "Produção" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Componentes" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Receitas" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Cadastros" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Gestão" })).toBeInTheDocument();
  });

  it("lista ingredientes, filtros e assistente", async () => {
    installApiMock();
    const { view } = await renderApp("/componentes/ingredientes");
    expect(await screen.findByRole("heading", { name: "Ingredientes" })).toBeInTheDocument();
    expect(
      await screen.findByRole("link", { name: "Abrir detalhe de Farinha de trigo tipo 1" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir detalhe do código FAR-1" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Detalhe de Farinha de trigo tipo 1" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Novo ingrediente" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ingredientes" })).toBeInTheDocument();
    expect(screen.getByText(/Rascunho v1/)).toBeInTheDocument();
    expect(document.body.textContent).toContain("Ativa");
    expect(screen.getByLabelText("Pesquisa")).toBeInTheDocument();
    const results = await axe(view.container);
    expect(results.violations).toEqual([]);
  });

  it("cria rascunho e publica", async () => {
    installApiMock();
    await renderApp("/componentes/ingredientes/novo");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Código"), "FAR-9");
    await user.type(screen.getByLabelText("Nome"), "Farinha nova");
    await user.click(screen.getByRole("button", { name: "Criar rascunho" }));
    await waitFor(() => {
      expect(vi.mocked(fetch).mock.calls.some(([input]) => String(input).includes("/ingredients"))).toBe(
        true,
      );
    });
  });

  it("edita rascunho com composição, nutrição, alergênicos e fontes", async () => {
    installApiMock();
    await renderApp("/componentes/ingredientes/eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee");
    expect(await screen.findByRole("heading", { name: "Farinha de trigo tipo 1" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Composição" })).toBeInTheDocument();
    expect(document.body.textContent).toContain("Constituinte");
    expect(screen.getByRole("heading", { name: "Nutrição por 100 g" })).toBeInTheDocument();
    expect(screen.getByText(/Proteína: Abaixo do limite de quantificação/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Alergênicos" })).toBeInTheDocument();
    expect(screen.getByText(/Glúten · Contém · rótulo/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Fontes e evidências" })).toBeInTheDocument();
    expect(screen.getByText(/Nenhuma fonte global disponível/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Fornecedores e valores de compra" })).toBeInTheDocument();
    expect(document.body.textContent).toContain("SKU-1");
    expect(document.body.textContent).toMatch(/Embalagem:\s*25 kg/);
    expect(document.body.textContent).toMatch(/Último valor:/);
    expect(screen.getByText("Versão sem fonte técnica associada.")).toBeInTheDocument();
    const completeness = screen.getByRole("heading", { name: "Completude" }).closest(".panel");
    expect(completeness?.textContent).not.toMatch(/origem:/i);
    expect(completeness?.textContent).not.toContain("ingredient_version.data_source_id");
    expect(screen.getByRole("dialog", { name: "Assistente de ingrediente" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Publicar versão" })).toBeInTheDocument();
  });

  it("trata versão publicada como imutável e oferece nova versão", async () => {
    installApiMock({
      "/versions/": () =>
        json({
          data: {
            identity: { display_name: "Farinha de trigo tipo 1" },
            version: {
              id: "ffffffff-ffff-ffff-ffff-ffffffffffff",
              ingredient_id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
              version_number: 1,
              status: "published",
              data_source_id: null,
              notes: null,
              row_version: 2,
              nutrition_basis_unit_id: "u1",
            },
            composition: [],
            nutrients: [],
            allergens: [],
            completeness: { ready_to_publish: true, complete_dossier: true, items: [] },
          },
          row_version: 2,
        }),
    });
    await renderApp("/componentes/ingredientes/eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee");
    expect(await screen.findByText(/Versão publicada é imutável/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Criar nova versão" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Guardar nutriente" })).not.toBeInTheDocument();
  });

  it("mostra conflito HTTP 409", async () => {
    installApiMock({
      "/publish": () =>
        json(
          { code: "versao_conflito", message: "A versão do recurso mudou. Recarregue e tente de novo." },
          409,
        ),
    });
    await renderApp("/componentes/ingredientes/eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Publicar versão" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/estado mudou|versão do recurso/i);
  });

  it("limpa o recorte ao trocar de organização", async () => {
    installApiMock({
      [ORG_B]: (url, request) => {
        if (url.pathname.endsWith("/ingredients") && request.method === "GET") {
          return json({ items: [], total: 0, limit: 20, offset: 0 });
        }
        return json({ data: [] });
      },
    });
    await renderApp("/componentes/ingredientes");
    expect(await screen.findByText("Farinha de trigo tipo 1")).toBeInTheDocument();
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    expect(await screen.findByText("Não há ingredientes neste recorte.")).toBeInTheDocument();
  });

  it("esconde componentes sem permissão", async () => {
    installApiMock({
      "/api/v1/me": () =>
        json({
          ...meFixture,
          associations: meFixture.associations.map((item) => ({
            ...item,
            permissions: item.permissions.filter(
              (code) =>
                !code.startsWith("ingredient") &&
                !code.startsWith("supplier") &&
                !code.startsWith("inventory"),
            ),
          })),
          permissions: meFixture.permissions.filter(
            (code) =>
              !code.startsWith("ingredient") &&
              !code.startsWith("supplier") &&
              !code.startsWith("inventory"),
          ),
        }),
    });
    await renderApp("/producao");
    expect(await screen.findByRole("link", { name: "Produção" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Componentes" })).not.toBeInTheDocument();
  });

  it("abre fornecedores e catálogos sem links mortos", async () => {
    installApiMock();
    await renderApp("/componentes/fornecedores");
    expect(await screen.findByRole("heading", { name: "Fornecedores e itens" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir detalhe de Moinho Demo" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Detalhe de Moinho Demo" })).toBeInTheDocument();
  });
});
