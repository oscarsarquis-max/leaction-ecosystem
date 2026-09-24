import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
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

const entryCss = readFileSync(
  path.resolve(path.dirname(fileURLToPath(import.meta.url)), "styles/app.css"),
  "utf8",
);

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

  it("oferece chave/dados e XML na abertura, sem leitura de foto", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/gestao/compras/entradas/nova");

    expect(await screen.findByRole("heading", { name: "Registrar entrada" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Preencher nota" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Guardar foto ou PDF como referência" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Buscar documentos da Fazenda" })).toBeInTheDocument();
    expect(screen.getByLabelText("Número da nota")).toBeInTheDocument();
    expect(screen.getByLabelText("Chave de acesso")).toBeInTheDocument();
    expect(screen.queryByLabelText("PDF ou foto do DANFE")).not.toBeInTheDocument();
    expect(
      screen.getByText("O arquivo não é lido nem valida a nota. Você pode concluir sem anexá-lo."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Simulação — documentos fictícios/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/captura é assistida/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Consultar esta chave no portal da Fazenda" })).not.toBeInTheDocument();
    expect(screen.getByText(/consulta pública é no portal da Fazenda/i)).toBeInTheDocument();
  });

  it("ação principal de entrada usa espresso/creme no .entry-page, não --manual-brown órfão", async () => {
    const user = userEvent.setup();
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/gestao/compras/entradas/nova");
    expect(await screen.findByRole("button", { name: "Revisar e gravar" })).toHaveClass("primary", "manual-primary");

    const scoped = entryCss.match(/\.entry-page\s*\{[\s\S]*?\n\}/)?.[0] ?? "";
    expect(scoped).toMatch(/--manual-brown:\s*var\(--panne-espresso\)/);
    const action = entryCss.match(/\.entry-page \.manual-primary\s*\{[\s\S]*?\n\}/)?.[0] ?? "";
    expect(action).toMatch(/background:\s*var\(--panne-espresso\)/);
    expect(action).toMatch(/color:\s*var\(--panne-creme\)/);
    expect(action).toMatch(/border:\s*1px solid var\(--panne-espresso\)/);
    expect(entryCss).toMatch(/\.entry-page \.manual-primary:hover:not\(:disabled\)/);
    expect(entryCss).toMatch(/\.entry-page \.manual-primary:focus-visible/);
    expect(entryCss).toMatch(/\.entry-page \.manual-primary:disabled/);

    await user.type(screen.getByLabelText("Fornecedor"), "Moinho Real");
    await user.type(screen.getByLabelText("Número da nota"), "50661");
    await user.type(screen.getByLabelText("Descrição"), "Farinha tipo 1");
    await user.type(screen.getByLabelText("Quantidade"), "25");
    await user.click(screen.getByRole("button", { name: "Revisar e gravar" }));
    expect(await screen.findByRole("button", { name: "Gravar nota" })).toHaveClass("primary", "manual-primary");
    expect(screen.queryByRole("button", { name: "Revisar e gravar" })).not.toBeInTheDocument();
  });

  it("oferece consulta pública no portal após a chave, sem validar nem preencher a nota", async () => {
    const user = userEvent.setup();
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/gestao/compras/entradas/nova");
    expect(await screen.findByRole("heading", { name: "Registrar entrada" })).toBeInTheDocument();

    await user.type(
      screen.getByLabelText("Chave de acesso"),
      "35260812345678000190550010005066121034567890",
    );
    const portal = screen.getByRole("link", { name: "Consultar esta chave no portal da Fazenda" });
    expect(portal).toHaveAttribute(
      "href",
      "https://www.nfe.fazenda.gov.br/portal/consultaRecaptcha.aspx?tipoConsulta=completa&tipoConteudo=XbSeqxE8pl8=",
    );
    expect(portal).toHaveAttribute("target", "_blank");
    expect(screen.getByText(/Abrir o portal não valida a nota na Panne/)).toBeInTheDocument();
    expect(screen.queryByText(/validada pela Panne/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Fornecedor")).toHaveValue("");
    expect(screen.getByLabelText("Número da nota")).toHaveValue("");
    expect(screen.queryByDisplayValue(/FORNECEDOR DEMONSTRACAO/)).not.toBeInTheDocument();
  });

  it("mostra erros no campo, revisão antes de gravar e confirma na mesma página sem estoque", async () => {
    const user = userEvent.setup();
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/gestao/compras/entradas/nova");
    expect(await screen.findByRole("heading", { name: "Registrar entrada" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Revisar e gravar" }));
    expect(await screen.findByText("Informe o fornecedor.")).toBeInTheDocument();
    expect(screen.getByText("Informe o número da nota.")).toBeInTheDocument();
    expect(screen.getByText("Informe ao menos um item com descrição e quantidade.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Revisão" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Fornecedor")).toHaveValue("");

    await user.click(screen.getByLabelText("Quero guardar o arquivo com esta nota"));
    const file = new File(["foto-ilegivel"], "nota-ilegivel.jpeg", { type: "image/jpeg" });
    await user.upload(screen.getByLabelText("Arquivo de referência"), file);
    expect(screen.getByText(/Anexo escolhido: nota-ilegivel.jpeg/)).toBeInTheDocument();
    expect(screen.getByLabelText("Fornecedor")).toHaveValue("");
    expect(screen.getByLabelText("Número da nota")).toHaveValue("");
    expect(screen.getByLabelText("Chave de acesso")).toHaveValue("");
    expect(screen.queryByDisplayValue(/FORNECEDOR DEMONSTRACAO/)).not.toBeInTheDocument();

    await user.type(screen.getByLabelText("Fornecedor"), "Moinho Real");
    await user.type(screen.getByLabelText("Número da nota"), "50661");
    await user.type(screen.getByLabelText("Descrição"), "Farinha tipo 1");
    await user.type(screen.getByLabelText("Quantidade"), "25");
    await user.click(screen.getByRole("button", { name: "Revisar e gravar" }));

    expect(await screen.findByRole("heading", { name: "Revisão" })).toBeInTheDocument();
    expect(screen.getByText("Fornecedor: Moinho Real")).toBeInTheDocument();
    expect(screen.getByText(/Nota 50661/)).toBeInTheDocument();
    expect(screen.getByText(/Gravar a nota não lança estoque/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirmar entrada no estoque" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Gravar nota" }));
    expect(await screen.findByText(/Nota gravada · estoque pendente/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Revisar e confirmar entrada no estoque" })).toBeInTheDocument();
    expect(screen.queryByText(/estoque atualizado/i)).not.toBeInTheDocument();
  });

  it("grava nota sem chave e só anexa depois, sem criar outra nota", async () => {
    const user = userEvent.setup();
    const calls: string[] = [];
    async function readBody(request: Request) {
      try {
        const text = await request.clone().text();
        return text ? JSON.parse(text) : {};
      } catch {
        return {};
      }
    }
    installApiMock({
      "/fiscal/documents/scan": async (_url, request) => {
        calls.push("POST /scan");
        const body = await readBody(request);
        expect(body.document_id).toBe(FISCAL_DOCUMENT_ID);
        expect(body.ocr).toBeUndefined();
        return json({ data: fiscalDocumentFixture, row_version: 1 });
      },
    });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/gestao/compras/entradas/nova");
    expect(await screen.findByRole("heading", { name: "Registrar entrada" })).toBeInTheDocument();

    await user.type(screen.getByLabelText("Fornecedor"), "Moinho Real do Ensaio");
    await user.type(screen.getByLabelText("Número da nota"), "4108");
    await user.type(screen.getByLabelText("Descrição"), "Farinha tipo 1");
    await user.type(screen.getByLabelText("Quantidade"), "25");
    await user.click(screen.getByRole("button", { name: "Revisar e gravar" }));
    await user.click(await screen.findByRole("button", { name: "Gravar nota" }));

    expect(await screen.findByText(/Nota gravada · estoque pendente/)).toBeInTheDocument();
    expect(screen.queryByText(/estoque atualizado/i)).not.toBeInTheDocument();
    expect(calls.filter((item) => item.includes("/scan"))).toHaveLength(0);

    const file = new File(["ref"], "danfe-ensaio.jpeg", { type: "image/jpeg" });
    await user.upload(screen.getByLabelText("Arquivo de referência"), file);
    await user.click(screen.getByRole("button", { name: "Guardar referência" }));
    expect(await screen.findByText(/Referência guardada: danfe-ensaio.jpeg/)).toBeInTheDocument();
    expect(calls.filter((item) => item.includes("/scan"))).toHaveLength(1);
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
          match: {
            status: "matched",
            target_kind: "ingredient",
            target_id: "ing-pao",
            target_label: "Pao frances 250g",
            suggestion_reason: null,
          },
          stock_unit_code: "UN",
          review: {
            suggested_ingredient_name: "Pao frances 250g",
            suggested_ingredient_id: "ing-pao",
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
