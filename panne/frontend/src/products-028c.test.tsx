import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { meFixture, ORG_A } from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

const UUID_RE = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/i;
// "combo" é palavra da cópia humana ("Combo de produtos"); os demais só existiriam como enum cru.
const RAW_ENUM_RE = /\b(produced|purchased|mixed|intermediate|active|inactive)\b|supply_mode|row_version/i;

function meWithRoles(roles: string[]) {
  return {
    ...meFixture,
    associations: meFixture.associations.map((row) =>
      row.organization_id === ORG_A ? { ...row, roles } : row,
    ),
    roles,
  };
}

describe("CURSOR-028-C produtos", () => {
  it("lista produtos com situação, abastecimento e receita em linguagem humana", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/produtos");

    expect(await screen.findByRole("heading", { name: "Produtos" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Abrir detalhe de Pão tradicional" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir detalhe de Refrigerante de cola" })).toBeInTheDocument();
    const table = within(screen.getByRole("table", { name: "Produtos da organização" }));
    expect(table.getByText("Produzido na casa")).toBeInTheDocument();
    expect(table.getByText("Comprado pronto")).toBeInTheDocument();
    expect(table.getByText("Sem receita vigente")).toBeInTheDocument();
    expect(table.getByText("Não se aplica")).toBeInTheDocument();
    expect(
      within(screen.getByRole("main")).getByRole("link", { name: "Novo produto" }),
    ).toBeInTheDocument();
  });

  it("cadastra produto comprado pronto, sem exigir receita", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/produtos/novo");

    expect(await screen.findByRole("heading", { name: "Novo produto" })).toBeInTheDocument();
    await user.type(screen.getByLabelText(/^Código/), "REF-COLA");
    await user.type(screen.getByLabelText(/^Nome/), "Refrigerante de cola");
    await user.selectOptions(screen.getByLabelText("Abastecimento"), "purchased");
    await user.click(screen.getByRole("button", { name: "Criar produto" }));

    expect(
      await screen.findByRole("heading", { name: "Refrigerante de cola" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Não se aplica").length).toBeGreaterThan(0);
    expect(screen.getByText(/não gera ordem de produção/i)).toBeInTheDocument();
  });

  it("cadastra produto produzido sem receita e explica o bloqueio de produção", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/produtos/novo");

    expect(await screen.findByRole("heading", { name: "Novo produto" })).toBeInTheDocument();
    await user.type(screen.getByLabelText(/^Código/), "PAO-TRAD");
    await user.type(screen.getByLabelText(/^Nome/), "Pão tradicional");
    await user.click(screen.getByRole("button", { name: "Criar produto" }));

    expect(await screen.findByRole("heading", { name: "Pão tradicional" })).toBeInTheDocument();
    expect(screen.getAllByText("Sem receita vigente").length).toBeGreaterThan(0);
    expect(screen.getByText(/produção fica bloqueada até haver receita vigente/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Editar produto" })).toBeInTheDocument();
  });

  it("cria família e mostra na lista de famílias", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/produtos/familias");

    expect(await screen.findByRole("heading", { name: "Famílias de produto" })).toBeInTheDocument();
    expect(await screen.findByText("Pães")).toBeInTheDocument();
    await user.type(screen.getByLabelText(/^Código/), "FAM-DOCES");
    await user.type(screen.getByLabelText(/^Nome/), "Doces");
    await user.click(screen.getByRole("button", { name: "Guardar família" }));
    expect(await screen.findByRole("heading", { name: "Famílias de produto" })).toBeInTheDocument();
  });

  it("etapa 3 do fluxo abre produtos com contagem da organização", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/fluxo?etapa=3");

    expect(await screen.findByRole("heading", { name: /Etapa 3 · Produtos/ })).toBeInTheDocument();
    expect(screen.getAllByText(/produto\(s\) ativo\(s\)/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/produzido\(s\) sem receita vigente/).length).toBeGreaterThanOrEqual(1);
    await user.click(screen.getAllByRole("link", { name: "Abrir produtos" })[0]);
    expect(await screen.findByRole("heading", { name: "Produtos" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Voltar ao fluxo" }).length).toBeGreaterThanOrEqual(1);
  });

  it("não expõe identificador técnico nem código de contrato na lista", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/produtos");

    expect(await screen.findByRole("heading", { name: "Produtos" })).toBeInTheDocument();
    const main = screen.getByRole("main").textContent ?? "";
    expect(main).not.toMatch(UUID_RE);
    expect(main).not.toMatch(RAW_ENUM_RE);
  });

  it("traduz o papel do usuário no menu da conta", async () => {
    installApiMock({ "/api/v1/me": () => json(meWithRoles(["owner"])) });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/produtos");

    expect(await screen.findByRole("heading", { name: "Produtos" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Abrir menu do usuário" }));
    const menu = screen.getByRole("menu", { name: "Menu do usuário" });
    expect(within(menu).getByText("Proprietário")).toBeInTheDocument();
    expect(screen.queryByText("owner")).not.toBeInTheDocument();
  });

  it("liga o produto da ordem ao cadastro quando há permissão de leitura", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/ordens");

    const link = await screen.findByRole("link", { name: "Abrir produto Pão tradicional" });
    expect(link).toHaveAttribute("href", "/produtos/prod-1");
  });
});
