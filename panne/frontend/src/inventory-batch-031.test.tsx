/**
 * CURSOR-031: tela de inventário inicial em lote.
 * Só o que é da tela: colar, teclado, rascunho, erro por linha, resumo, gravação e 390 px.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ORG_A } from "./api/fixtures";
import { draftKey } from "./pages/inventoryBatch";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

const css = readFileSync(path.resolve(path.dirname(fileURLToPath(import.meta.url)), "styles/app.css"), "utf8");
const URL_PAGE = "/componentes/estoque/inventario";

const PASTED = [
  "Farinha de trigo tipo 1\t25\tkg\t15/03/2027\t4,80",
  "Açúcar cristal\t10\tkg",
  "Fermento biológico\t3\tpacote\t01/12/2026",
  "Sal marinho\t5\tkg",
  "Manteiga\t2\tun\t\t32,5",
].join("\n");

function stubViewport(width: number) {
  Object.defineProperty(window, "innerWidth", { configurable: true, value: width });
  window.matchMedia = ((query: string) => {
    const max = /max-width:\s*(\d+)px/.exec(query);
    const min = /min-width:\s*(\d+)px/.exec(query);
    let matches = true;
    if (max) matches = matches && width <= Number(max[1]);
    if (min) matches = matches && width >= Number(min[1]);
    return {
      matches,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    } as MediaQueryList;
  }) as typeof window.matchMedia;
}

function ingredientInput(row: HTMLElement): HTMLElement {
  return within(row).getByLabelText(/^Ingrediente/);
}

function rowElements(): HTMLElement[] {
  return Array.from(document.querySelectorAll<HTMLElement>("li[data-row-id]"));
}

async function open(overrides: Parameters<typeof installApiMock>[1] = {}) {
  installApiMock(overrides);
  const rendered = await renderApp(URL_PAGE);
  expect(await screen.findByRole("heading", { name: "Inventário inicial" })).toBeInTheDocument();
  await screen.findByLabelText("Local do estoque");
  await waitFor(() => expect((screen.getByLabelText("Local do estoque") as HTMLSelectElement).value).not.toBe(""));
  return rendered;
}

async function pasteFive(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("textbox", { name: "Colar da planilha" }));
  await user.paste(PASTED);
  await user.click(screen.getByRole("button", { name: "Preencher a tabela" }));
}

async function fillPack(user: ReturnType<typeof userEvent.setup>) {
  await user.type(within(rowElements()[2]).getByLabelText(/^Conteúdo de cada embalagem/), "500");
}

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("panne.activeOrganization", ORG_A);
  stubViewport(1440);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

describe("Inventário inicial em lote", () => {
  it("abre vazia, com local, data e motivo uma vez só e uma linha pronta", async () => {
    await open();
    expect(screen.getAllByLabelText("Local do estoque")).toHaveLength(1);
    expect(screen.getAllByLabelText("Data da contagem")).toHaveLength(1);
    expect(screen.getAllByLabelText("Motivo")).toHaveLength(1);
    expect((screen.getByLabelText("Motivo") as HTMLInputElement).value).toBe("Inventário inicial");
    expect((screen.getByLabelText("Data da contagem") as HTMLInputElement).value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(rowElements()).toHaveLength(1);
    expect(screen.getByTestId("resumo-inventario")).toHaveTextContent("0 itens · 0 ingredientes novos · 0 sem custo · 0 sem validade");
    expect(screen.getByRole("button", { name: "Gravar inventário" })).toBeDisabled();
  });

  it("aparece no menu de Estoque no lugar de 'Abrir saldo sem nota', e a tela antiga segue na URL", async () => {
    await open();
    const submenu = screen.getByRole("navigation", { name: "Submenu" });
    expect(within(submenu).getByRole("link", { name: "Inventário inicial" })).toHaveAttribute(
      "href",
      "/componentes/estoque/inventario",
    );
    expect(within(submenu).queryByText("Abrir saldo sem nota")).toBeNull();
    cleanup();
    installApiMock();
    await renderApp("/componentes/estoque/abertura");
    expect(await screen.findByRole("heading", { name: "Abrir saldo sem nota" })).toBeInTheDocument();
  });

  it("cola 5 linhas da planilha, marca o que é novo e mostra o resumo", async () => {
    const user = userEvent.setup();
    await open();
    await pasteFive(user);

    await waitFor(() => expect(rowElements().length).toBeGreaterThanOrEqual(6));
    const filled = rowElements().slice(0, 5);
    expect(within(filled[0]).queryByText("novo")).toBeNull();
    expect(within(filled[2]).getByText("novo")).toBeInTheDocument();
    expect(within(filled[3]).getByText("novo")).toBeInTheDocument();
    expect(within(filled[4]).getByText("novo")).toBeInTheDocument();
    expect((within(filled[2]).getByLabelText(/^Unidade da linha/) as HTMLSelectElement).value).toBe("emb");
    expect(within(filled[2]).getByLabelText(/^Conteúdo de cada embalagem/)).toBeInTheDocument();
    expect(within(filled[0]).queryByLabelText(/^Conteúdo de cada embalagem/)).toBeNull();
    expect(screen.getByTestId("resumo-inventario")).toHaveTextContent(
      "5 itens · 3 ingredientes novos · 3 sem custo · 3 sem validade",
    );
    expect(screen.getByText(/5 linhas preenchidas, 3 nomes novos marcados/)).toBeInTheDocument();
  });

  it("aceita colar direto na tabela", async () => {
    const user = userEvent.setup();
    await open();
    const first = rowElements()[0];
    await user.click(ingredientInput(first));
    await user.paste("Sal marinho\t5\tkg\n Manteiga\t2\tun");
    await waitFor(() => expect(screen.getByTestId("resumo-inventario")).toHaveTextContent(/^2 itens/));
  });

  it("Enter vai para a próxima linha e a linha do fim nasce sozinha", async () => {
    const user = userEvent.setup();
    await open();
    expect(rowElements()).toHaveLength(1);
    const quantity = within(rowElements()[0]).getByLabelText(/^Quantidade/);
    await user.type(quantity, "5");
    await waitFor(() => expect(rowElements()).toHaveLength(2));
    await user.keyboard("{Enter}");
    const second = rowElements()[1];
    await waitFor(() => expect(second.contains(document.activeElement)).toBe(true));
    await user.keyboard("{Enter}");
    await waitFor(() => expect(rowElements()).toHaveLength(3));
    expect(rowElements()[2].contains(document.activeElement)).toBe(true);
  });

  it("escolhe ingrediente da lista, oferece criar um novo e vai para a quantidade", async () => {
    const user = userEvent.setup();
    await open();
    const combo = ingredientInput(rowElements()[0]);
    await user.type(combo, "Farinha");
    await user.click(await screen.findByRole("option", { name: /Farinha de trigo tipo 1/ }));
    await waitFor(() => expect(within(rowElements()[0]).getByLabelText(/^Quantidade/)).toHaveFocus());
    expect(within(rowElements()[0]).getByText(/Estoque em kg/)).toBeInTheDocument();

    const second = ingredientInput(rowElements()[1]);
    await user.type(second, "Granola da casa");
    await user.click(await screen.findByRole("option", { name: /Criar "Granola da casa"/ }));
    expect(within(rowElements()[1]).getByText("novo")).toBeInTheDocument();
  });

  it("duplica e remove linhas", async () => {
    const user = userEvent.setup();
    await open();
    await pasteFive(user);
    await waitFor(() => expect(rowElements().length).toBeGreaterThanOrEqual(6));
    const before = rowElements().length;
    await user.click(screen.getByRole("button", { name: "Duplicar linha 4" }));
    await waitFor(() => expect(rowElements()).toHaveLength(before + 1));
    expect(screen.getByTestId("resumo-inventario")).toHaveTextContent(/^6 itens/);
    await user.click(screen.getByRole("button", { name: "Remover linha 5" }));
    await waitFor(() => expect(rowElements()).toHaveLength(before));
    expect(screen.getByTestId("resumo-inventario")).toHaveTextContent(/^5 itens/);
  });

  it("guarda o rascunho no navegador e ele volta depois de recarregar", async () => {
    const user = userEvent.setup();
    const first = await open();
    await pasteFive(user);
    await waitFor(() => expect(localStorage.getItem(draftKey(ORG_A))).not.toBeNull());
    first.view.unmount();
    cleanup();

    await open();
    expect(await screen.findByText(/Recuperamos o rascunho/)).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByTestId("resumo-inventario")).toHaveTextContent(
        "5 itens · 3 ingredientes novos · 3 sem custo · 3 sem validade",
      ),
    );
    await user.click(screen.getByRole("button", { name: "Descartar rascunho" }));
    expect(localStorage.getItem(draftKey(ORG_A))).toBeNull();
    expect(screen.getByTestId("resumo-inventario")).toHaveTextContent(/^0 itens/);
  });

  it("aponta a linha com problema antes de enviar, sem perder o que foi digitado", async () => {
    const user = userEvent.setup();
    let sent = 0;
    await open({
      "/inventory/openings/batch": () => {
        sent += 1;
        return json({ data: {} });
      },
    });
    await user.type(ingredientInput(rowElements()[0]), "Sal marinho");
    await user.click(await screen.findByRole("option", { name: /Criar "Sal marinho"/ }));
    await user.click(screen.getByRole("button", { name: "Gravar inventário" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Corrija 1 linha marcada/);
    expect(within(rowElements()[0]).getByText(/Informe a quantidade/)).toBeInTheDocument();
    expect(ingredientInput(rowElements()[0])).toHaveValue("Sal marinho");
    expect(sent).toBe(0);
  });

  it("mostra o erro devolvido pelo servidor na linha certa e mantém tudo", async () => {
    const user = userEvent.setup();
    await open({
      "/inventory/openings/batch": () =>
        json(
          {
            code: "inventario_com_erros",
            message: "Nada foi gravado. Corrija as linhas marcadas e grave de novo.",
            errors: [
              {
                index: 1,
                field: "unit_code",
                code: "unidade_incompativel",
                message: "Este ingrediente é controlado em quilos. Use essa unidade.",
              },
            ],
          },
          422,
        ),
    });
    await pasteFive(user);
    await waitFor(() => expect(rowElements().length).toBeGreaterThanOrEqual(6));
    await fillPack(user);
    await user.click(screen.getByRole("button", { name: "Gravar inventário" }));

    const second = rowElements()[1];
    expect(await within(second).findByText(/controlado em quilos/)).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/Nada foi gravado/);
    expect(ingredientInput(rowElements()[0])).toHaveValue("Farinha de trigo tipo 1");
    expect(within(second).getByLabelText(/^Quantidade/)).toHaveValue("10");
    expect(screen.getByTestId("resumo-inventario")).toHaveTextContent(/^5 itens/);
    await waitFor(() => expect(localStorage.getItem(draftKey(ORG_A))).not.toBeNull());
  });

  it("grava, limpa o rascunho e leva para a Visão geral do estoque", async () => {
    const user = userEvent.setup();
    let body: Record<string, unknown> | null = null;
    await open({
      "/inventory/openings/batch": (_url, request) => {
        void request
          .clone()
          .json()
          .then((value) => {
            body = value as Record<string, unknown>;
          });
        return json({
          data: { batch_id: "b-1", line_count: 5, created_ingredients: 3, replayed: false, lines: [] },
        });
      },
    });
    await pasteFive(user);
    await waitFor(() => expect(rowElements().length).toBeGreaterThanOrEqual(6));
    await fillPack(user);
    await user.click(screen.getByRole("button", { name: "Gravar inventário" }));

    const done = await screen.findByTestId("inventario-gravado");
    expect(done).toHaveTextContent(/5 itens lançados em Almoxarifado Central/);
    expect(done).toHaveTextContent(/3 ingredientes novos foram cadastrados/);
    expect(screen.getByRole("link", { name: "Abrir a Visão geral do estoque" })).toHaveAttribute(
      "href",
      "/componentes/estoque",
    );
    expect(localStorage.getItem(draftKey(ORG_A))).toBeNull();
    await waitFor(() => expect(body).not.toBeNull());
    const sentBody = body as unknown as { lines: unknown[]; reason: string };
    expect(sentBody.lines).toHaveLength(5);
    expect(sentBody.reason).toBe("Inventário inicial");
  });

  it("não usa termos técnicos na tela", async () => {
    const user = userEvent.setup();
    await open();
    await pasteFive(user);
    const text = document.body.textContent ?? "";
    for (const term of [/append-only/i, /can[ôo]nic/i, /payload/i, /idempot/i, /ledger/i, /\bUUID\b/i]) {
      expect(text).not.toMatch(term);
    }
  });
});

describe("Inventário inicial em 390 CSS px", () => {
  beforeEach(() => stubViewport(390));

  it("mantém todos os campos acessíveis em cada linha e só pede conteúdo para embalagem", async () => {
    const user = userEvent.setup();
    await open();
    await pasteFive(user);
    await waitFor(() => expect(rowElements().length).toBeGreaterThanOrEqual(6));
    const pack = rowElements()[2];
    for (const label of [/^Ingrediente/, /^Quantidade/, /^Unidade da linha/, /^Conteúdo de cada embalagem/, /^Validade/, /^Lote/, /^Custo unitário/]) {
      expect(within(pack).getByLabelText(label)).toBeInTheDocument();
    }
    const kilo = rowElements()[0];
    expect(within(kilo).queryByLabelText(/^Conteúdo de cada embalagem/)).toBeNull();
    fireEvent.change(within(kilo).getByLabelText(/^Unidade da linha/), { target: { value: "emb" } });
    expect(within(kilo).getByLabelText(/^Conteúdo de cada embalagem/)).toBeInTheDocument();
  });

  it("vira cartão abaixo de 1101 px, com alvos de toque de 44 px", () => {
    const stripped = css.replace(/\/\*[\s\S]*?\*\//g, "");
    expect(stripped).toMatch(/\.inv-row\s*\{[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/);
    expect(stripped).toMatch(/@media \(min-width: 1101px\)\s*\{[\s\S]*?\.inv-row\s*\{[^}]*grid-template-columns:\s*2rem/);
    expect(stripped).toMatch(/\.inv-icon\s*\{[^}]*min-height:\s*2\.75rem[^}]*\}/);
    expect(stripped).toMatch(/\.inv-icon\s*\{[^}]*min-width:\s*2\.75rem/);
    expect(stripped).toMatch(/\.manual-path input:not\(\[type="checkbox"\]\):not\(\[type="radio"\]\)\s*\{[^}]*min-height:\s*2\.75rem/);
    expect(stripped).not.toMatch(/transform\s*:\s*scale\s*\(/);
  });
});
