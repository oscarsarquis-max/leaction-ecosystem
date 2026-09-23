import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  FISCAL_DOCUMENT_ID,
  fiscalDocumentFixture,
  fiscalDocumentNoCostFixture,
  meFixture,
  ORG_A,
} from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

const UUID_RE = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/i;
const RAW_ENUM_RE =
  /\b(awaiting_match|awaiting_check|partially_received|divergent|confirmed|unmatched|matched|suggested)\b|access_key|row_version|cost_access/i;

/** Mesmos códigos que o backend consulta em `can_read_prices`. */
const COST_CODES = ["fiscal.price.read", "supplier.price.record"];

function meWithout(codes: string[]) {
  const drop = (list: string[]) => list.filter((code) => !codes.includes(code));
  return {
    ...meFixture,
    associations: meFixture.associations.map((row) =>
      row.organization_id === ORG_A ? { ...row, permissions: drop(row.permissions) } : row,
    ),
    permissions: drop(meFixture.permissions),
  };
}

describe("CURSOR-028-D entrada de mercadoria por documento fiscal", () => {
  it("lista entradas com fornecedor, andamento e situação em linguagem humana", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/gestao/compras/entradas");

    expect(await screen.findByRole("heading", { name: "Entradas fiscais" })).toBeInTheDocument();
    const table = within(
      await screen.findByRole("table", { name: "Entradas por documento fiscal" }),
    );
    expect(table.getByRole("link", { name: "Abrir Nota 104532 · série 1" })).toBeInTheDocument();
    expect(table.getByText("Moinho Demo")).toBeInTheDocument();
    expect(table.getByText("Aguardando conferência")).toBeInTheDocument();
    expect(table.getByText("Com divergência")).toBeInTheDocument();
    expect(table.getByText("Arquivo XML")).toBeInTheDocument();
    expect(
      within(screen.getByRole("main")).getByRole("link", { name: "Registrar entrada" }),
    ).toBeInTheDocument();
  });

  it("oferece as quatro formas de registrar entrada já visíveis na abertura", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/gestao/compras/entradas/nova");

    expect(await screen.findByRole("heading", { name: "Registrar entrada" })).toBeInTheDocument();
    for (const option of [
      "Preencher manualmente",
      "Importar XML",
      "Enviar PDF ou foto",
      "Buscar documentos da Fazenda",
    ]) {
      expect(screen.getByRole("heading", { name: option })).toBeInTheDocument();
      expect(screen.getByRole("region", { name: option })).toBeInTheDocument();
    }
    expect(screen.getByLabelText("Número da nota")).toBeInTheDocument();
    expect(screen.getByLabelText("Arquivo XML da nota")).toBeInTheDocument();
    expect(screen.getByLabelText("PDF ou foto do DANFE")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Consulta automática preparada, mas ainda não ativada para este estabelecimento.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Simulação — documentos fictícios/ }),
    ).toBeInTheDocument();
  });

  it("não expõe identificador técnico nem código de contrato na cópia operacional", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const list = await renderApp("/gestao/compras/entradas");
    expect(await screen.findByRole("heading", { name: "Entradas fiscais" })).toBeInTheDocument();
    const listText = screen.getByRole("main").textContent ?? "";
    expect(listText).not.toMatch(UUID_RE);
    expect(listText).not.toMatch(RAW_ENUM_RE);
    list.view.unmount();

    await renderApp("/gestao/compras/entradas/nova");
    expect(await screen.findByRole("heading", { name: "Registrar entrada" })).toBeInTheDocument();
    const newText = screen.getByRole("main").textContent ?? "";
    expect(newText).not.toMatch(UUID_RE);
    expect(newText).not.toMatch(RAW_ENUM_RE);
  });

  it("revisa a entrada respondendo documento, fornecedor, itens, conferência e estoque", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp(`/gestao/compras/entradas/${FISCAL_DOCUMENT_ID}`);

    expect(
      await screen.findByRole("heading", { name: "Nota 104532 · série 1" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Qual é o documento" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Quem forneceu" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Revisão da nota" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Entrada no estoque" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Onde guardar?" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "O estoque já foi atualizado" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Próxima ação" })).toBeInTheDocument();

    expect(screen.getByText("3526 0812 3456 7800 0190 5500 1000 1045 3212 3456 7890")).toBeInTheDocument();
    expect(screen.getByText("12.345.678/0001-90")).toBeInTheDocument();
    expect(screen.getByText("Estoque ainda não atualizado")).toBeInTheDocument();
    expect(
      screen.getByText("Grave a nota revisada. O estoque ainda não será lançado."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Confirmar recebimento")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Gravar nota revisada" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Confirmar entrada no estoque" })).toBeDisabled();
    expect(screen.queryByRole("heading", { name: "A ordem importa" })).not.toBeInTheDocument();

    const history = screen.getByText("Histórico e auditoria desta entrada").closest("details");
    expect(history).toBeInTheDocument();
    expect(history).not.toHaveAttribute("open");
  });

  it("mostra os valores do documento para quem tem permissão de custo", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp(`/gestao/compras/entradas/${FISCAL_DOCUMENT_ID}`);

    expect(await screen.findByRole("heading", { name: "Quanto custou" })).toBeInTheDocument();
    expect(screen.getAllByText("R$ 742,5").length).toBeGreaterThan(0);
    expect(
      screen.getByRole("table", { name: "Custo por item do documento" }),
    ).toBeInTheDocument();
  });

  it("oculta os valores do documento sem permissão de custo", async () => {
    // Sem a permissão a própria API deixa de mandar os valores; a tela segue esse aviso.
    installApiMock({
      "/api/v1/me": () => json(meWithout(COST_CODES)),
      [`/fiscal/documents/${FISCAL_DOCUMENT_ID}`]: () =>
        json({ data: fiscalDocumentNoCostFixture, row_version: 3 }),
    });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp(`/gestao/compras/entradas/${FISCAL_DOCUMENT_ID}`);

    expect(await screen.findByRole("heading", { name: "Quanto custou" })).toBeInTheDocument();
    expect(
      screen.getByText("Valores do documento ficam ocultos para o seu papel."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("table", { name: "Custo por item do documento" }),
    ).not.toBeInTheDocument();
    const main = screen.getByRole("main").textContent ?? "";
    expect(main).not.toMatch(/742,5|R\$/);
  });

  it("cliente sem insumo e sem local revisa a nota sem inventar quantidade nem fator", async () => {
    const entry = {
      ...fiscalDocumentFixture,
      establishment_id: "est-novo",
      establishment_name: "Loja Virtual",
      status: "awaiting_match",
      status_label: "Aguardando insumo de destino",
      matched_item_count: 0,
      checked_item_count: 0,
      stock_applied: false,
      pending_reasons: ["A revisão da nota ainda não foi gravada."],
      next_action: "save_review",
      next_action_label: "Gravar a nota revisada.",
      supplier: { id: null, display_name: "Emitente novo", tax_id: null, registered: false },
      items: [
        {
          id: "fi-new",
          sequence: 1,
          supplier_description: "Pao frances 250g",
          supplier_sku: null,
          invoiced_quantity: "1",
          unit_code: "UN",
          match: {
            status: "unmatched",
            target_kind: null,
            target_id: null,
            target_label: null,
            suggestion_reason: null,
          },
          physical: null,
          unit_cost: "4.50",
          total_cost: "4.50",
        },
      ],
    };
    installApiMock({
      [`/fiscal/documents/${FISCAL_DOCUMENT_ID}`]: () => json({ data: entry, row_version: 1 }),
      "/ingredients": () => json({ items: [], total: 0, limit: 200, offset: 0 }),
      "/inventory/locations": () => json({ items: [] }),
    });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp(`/gestao/compras/entradas/${FISCAL_DOCUMENT_ID}`);

    expect(await screen.findByRole("heading", { name: "Revisão da nota" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Entrada no estoque" })).toBeInTheDocument();
    expect(screen.getByText(/A nota diz: 1 unidade de Pao frances 250g/)).toBeInTheDocument();
    expect(screen.getByText(/Pista no nome do produto/)).toBeInTheDocument();
    expect(screen.getAllByText("Pao frances 250g").length).toBeGreaterThan(0);
    expect(screen.queryByText(/O que guardar/)).not.toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /Criar / })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Quantidade conferida")).toHaveValue("1");
    expect(screen.getByRole("radio", { name: "Em gramas" })).toBeChecked();
    await waitFor(() => {
      expect(screen.getByText("Estoque principal de Loja Virtual")).toBeInTheDocument();
    });
    expect(screen.getAllByText(/1 embalagem recebida/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/fator de conversão/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Gravar nota revisada" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Confirmar entrada no estoque" })).toBeDisabled();
    expect(screen.getByText(/Grave a nota revisada antes de lançar o estoque/)).toBeInTheDocument();
    expect(screen.queryByText("Confirmar recebimento")).not.toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText("Quantidade conferida"));
    await userEvent.type(screen.getByLabelText("Quantidade conferida"), "1 UN");
    expect(screen.getAllByText("Pao frances 250g").length).toBeGreaterThan(0);
    expect(screen.getByText("Estoque principal de Loja Virtual")).toBeInTheDocument();
    expect(screen.getByLabelText("Conteúdo de cada embalagem")).toHaveValue("250");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("grava a nota na mesma página e só então habilita a entrada no estoque", async () => {
    let saved = false;
    const entry = {
      ...fiscalDocumentFixture,
      establishment_id: "est-novo",
      establishment_name: "Loja Virtual",
      status: "awaiting_match",
      status_label: "Aguardando insumo de destino",
      review_saved: false,
      stock_pending: false,
      catalogs_created: false,
      stock_applied: false,
      next_action: "save_review",
      next_action_label: "Gravar a nota revisada.",
      items: [
        {
          id: "fi-new",
          sequence: 1,
          supplier_description: "Pao frances 250g",
          supplier_sku: null,
          invoiced_quantity: "1",
          unit_code: "UN",
          match: {
            status: "unmatched",
            target_kind: null,
            target_id: null,
            target_label: null,
            suggestion_reason: null,
          },
          physical: null,
          unit_cost: "4.50",
          total_cost: "4.50",
        },
      ],
    };
    const reviewed = {
      ...entry,
      status: "reviewed",
      status_label: "Nota gravada · estoque pendente",
      review_saved: true,
      stock_pending: true,
      catalogs_created: false,
      next_action: "confirm_stock",
      next_action_label: "Confirmar a entrada no estoque.",
      items: [
        {
          ...entry.items[0],
          review: {
            suggested_ingredient_name: "Pao frances 250g",
            suggested_ingredient_id: null,
            reviewed_quantity: "1",
            as_expected: true,
            issue: null,
            notes: null,
          },
        },
      ],
    };
    installApiMock({
      [`/fiscal/documents/${FISCAL_DOCUMENT_ID}/review`]: () => {
        saved = true;
        return json({ data: reviewed, row_version: 2 });
      },
      [`/fiscal/documents/${FISCAL_DOCUMENT_ID}`]: () =>
        json({ data: saved ? reviewed : entry, row_version: saved ? 2 : 1 }),
      "/ingredients": () => json({ items: [], total: 0, limit: 50, offset: 0 }),
      "/inventory/locations": () => json({ items: [] }),
    });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp(`/gestao/compras/entradas/${FISCAL_DOCUMENT_ID}`);

    expect(await screen.findByRole("button", { name: "Gravar nota revisada" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Confirmar entrada no estoque" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Gravar nota revisada" }));
    await waitFor(() => {
      expect(screen.getAllByText("Nota gravada · estoque pendente").length).toBeGreaterThan(0);
    });
    expect(screen.getByRole("heading", { name: "Entrada no estoque" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Revisão da nota" })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Confirmar entrada no estoque" })).toBeEnabled();
    });
    expect(screen.queryByText("Confirmar recebimento")).not.toBeInTheDocument();
  });

  it("abre a nota mesmo com o rascunho antigo guardado no navegador", async () => {
    sessionStorage.setItem(
      `panne-receipt:${FISCAL_DOCUMENT_ID}`,
      JSON.stringify({
        drafts: {
          "fi-1": {
            ingredientId: "",
            creating: true,
            newName: "Farinha",
            stockUnit: "g",
            factor: "",
            received: "1 UN",
            result: "ok",
            lot: "",
            expires: "",
            notes: "",
          },
        },
        locationId: "",
        newLocationName: "",
      }),
    );
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp(`/gestao/compras/entradas/${FISCAL_DOCUMENT_ID}`);

    expect(await screen.findByRole("heading", { name: "Revisão da nota" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Nota 104532 · série 1" })).toBeInTheDocument();
    expect(screen.getAllByLabelText("Quantidade conferida")[0]).toHaveValue("1 UN");
  });

  it("quem não confirma vê o próximo passo em vez de um botão inoperante", async () => {
    installApiMock({
      "/api/v1/me": () => json(meWithout(["fiscal.document.confirm", "procurement.receive"])),
    });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp(`/gestao/compras/entradas/${FISCAL_DOCUMENT_ID}`);

    expect(await screen.findByRole("heading", { name: "Revisão da nota" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Gravar nota revisada" })).toBeInTheDocument();
    expect(screen.getByText("A entrada no estoque cabe a quem pode atualizar o estoque.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirmar entrada no estoque" })).not.toBeInTheDocument();
    expect(screen.queryByText("Confirmar recebimento")).not.toBeInTheDocument();
  });

  it("etapa 1 do fluxo aponta para as entradas fiscais com os atalhos previstos", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/fluxo?etapa=1");

    expect(
      await screen.findByRole("heading", { name: /Etapa 1 · Compras e entradas/ }),
    ).toBeInTheDocument();
    const primaries = screen.getAllByRole("link", { name: "Registrar entrada" });
    expect(primaries.length).toBeGreaterThanOrEqual(1);
    expect(primaries[0]).toHaveAttribute("href", expect.stringContaining("/gestao/compras/entradas"));
    expect(screen.getByRole("link", { name: "Importar XML" })).toHaveAttribute(
      "href",
      expect.stringContaining("origem=xml"),
    );
    for (const label of [
      "Documentos aguardando conferência",
      "Recebimentos parciais",
      "Divergências",
      "Histórico",
    ]) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
    await waitFor(() => {
      expect(screen.getAllByText(/entrada\(s\) registrada\(s\)/).length).toBeGreaterThanOrEqual(1);
    });
  });

  it("mostra Entradas fiscais no submenu de compras", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/gestao/compras/entradas");

    expect(await screen.findByRole("heading", { name: "Entradas fiscais" })).toBeInTheDocument();
    const submenu = within(screen.getByRole("navigation", { name: "Submenu" }));
    expect(submenu.getByRole("link", { name: "Entradas fiscais" })).toBeInTheDocument();
  });
});
