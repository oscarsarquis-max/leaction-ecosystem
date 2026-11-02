/**
 * CURSOR-033: ajustes do Inventário inicial antes do lançamento real.
 * Parecidos, custo pela unidade, valor total, pendências na hora, menu "⋯", lista compacta e litro/ml.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ORG_A } from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

const css = readFileSync(path.resolve(path.dirname(fileURLToPath(import.meta.url)), "styles/app.css"), "utf8");
const stripped = css.replace(/\/\*[\s\S]*?\*\//g, "");
const URL_PAGE = "/componentes/estoque/inventario";
type User = ReturnType<typeof userEvent.setup>;

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

function rowElements(): HTMLElement[] {
  return Array.from(document.querySelectorAll<HTMLElement>("li[data-row-id]"));
}

function ingredientInput(row: HTMLElement): HTMLElement {
  return within(row).getByLabelText(/^Ingrediente/);
}

async function open(overrides: Parameters<typeof installApiMock>[1] = {}) {
  installApiMock(overrides);
  await renderApp(URL_PAGE);
  expect(await screen.findByRole("heading", { name: "Inventário inicial" })).toBeInTheDocument();
  await screen.findByLabelText("Local do estoque");
  await waitFor(() => expect((screen.getByLabelText("Local do estoque") as HTMLSelectElement).value).not.toBe(""));
}

async function paste(user: User, text: string) {
  await user.click(screen.getByRole("textbox", { name: "Colar da planilha" }));
  await user.paste(text);
  await user.click(screen.getByRole("button", { name: "Preencher a tabela" }));
  await waitFor(() => expect(rowElements().length).toBeGreaterThanOrEqual(2));
}

const saveButton = () => screen.getByRole("button", { name: "Gravar inventário" });

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

describe("Parecidos: evitar ingrediente duplicado", () => {
  it("colado: mostra 'Parecido com', deixa a linha a decidir e bloqueia a gravação", async () => {
    const user = userEvent.setup();
    await open();
    await paste(user, "Açucar cristalino\t10\tkg");
    const row = rowElements()[0];
    const panel = within(row).getByRole("group", { name: /Ingrediente parecido na linha 1/ });
    expect(panel).toHaveTextContent("Parecido com: Açúcar cristal");
    expect(within(panel).getByRole("button", { name: /^Usar este/ })).toBeInTheDocument();
    expect(within(panel).getByRole("button", { name: /^Criar novo/ })).toBeInTheDocument();
    expect(within(row).getByText("a decidir")).toBeInTheDocument();
    expect(screen.getByTestId("resumo-inventario")).toHaveTextContent("1 a decidir");
    expect(screen.getByTestId("resumo-inventario")).toHaveTextContent("0 ingredientes novos");
    expect(saveButton()).toBeDisabled();
    expect(screen.getByTestId("motivo-bloqueio")).toHaveTextContent(/1 a decidir/);
  });

  it("'Usar este' troca pelo ingrediente do cadastro e libera a gravação", async () => {
    const user = userEvent.setup();
    await open();
    await paste(user, "Açucar cristalino\t10\tkg");
    await user.click(within(rowElements()[0]).getByRole("button", { name: /^Usar este/ }));
    expect(ingredientInput(rowElements()[0])).toHaveValue("Açúcar cristal");
    expect(within(rowElements()[0]).queryByText(/Parecido com/)).toBeNull();
    expect(screen.queryByTestId("motivo-bloqueio")).toBeNull();
    expect(saveButton()).toBeEnabled();
  });

  it("'Criar novo' mantém o nome digitado como ingrediente novo e libera a gravação", async () => {
    const user = userEvent.setup();
    await open();
    await paste(user, "Açucar cristalino\t10\tkg");
    await user.click(within(rowElements()[0]).getByRole("button", { name: /^Criar novo/ }));
    expect(ingredientInput(rowElements()[0])).toHaveValue("Açucar cristalino");
    expect(within(rowElements()[0]).getByText("novo")).toBeInTheDocument();
    expect(within(rowElements()[0]).queryByText(/Parecido com/)).toBeNull();
    expect(screen.getByTestId("resumo-inventario")).toHaveTextContent("1 ingrediente novo");
    expect(saveButton()).toBeEnabled();
  });

  it("digitado: o parecido aparece quando a pessoa sai do campo", async () => {
    const user = userEvent.setup();
    await open();
    await user.type(ingredientInput(rowElements()[0]), "Acucar cristalino");
    expect(within(rowElements()[0]).queryByText(/Parecido com/)).toBeNull();
    await user.tab();
    expect(await within(rowElements()[0]).findByText(/Parecido com/)).toBeInTheDocument();
    expect(saveButton()).toBeDisabled();
  });

  it("nome sem parecido nenhum fica como novo, sem pedir decisão", async () => {
    const user = userEvent.setup();
    await open();
    await paste(user, "Granola da casa\t3\tkg");
    expect(within(rowElements()[0]).queryByText(/Parecido com/)).toBeNull();
    expect(within(rowElements()[0]).getByText("novo")).toBeInTheDocument();
    expect(saveButton()).toBeEnabled();
  });

  it("a recusa da API para nome igual aparece na linha, sem perder o que foi digitado", async () => {
    const user = userEvent.setup();
    await open({
      "/inventory/openings/batch": () =>
        json(
          {
            code: "inventario_com_erros",
            message: "Nada foi gravado. Corrija as linhas marcadas e grave de novo.",
            errors: [
              {
                index: 0,
                field: "ingredient",
                code: "ingrediente_ja_existe",
                message: 'Já existe "Granola da casa" no cadastro. Escolha esse ingrediente na lista.',
              },
            ],
          },
          422,
        ),
    });
    await paste(user, "Granola da casa\t3\tkg");
    await user.click(saveButton());
    expect(await within(rowElements()[0]).findByText(/Já existe "Granola da casa"/)).toBeInTheDocument();
    expect(ingredientInput(rowElements()[0])).toHaveValue("Granola da casa");
  });
});

describe("Custo pela unidade e valor total", () => {
  it("o rótulo do custo segue a unidade da linha", async () => {
    const user = userEvent.setup();
    await open();
    await paste(user, "Granola da casa\t3\tkg");
    const row = rowElements()[0];
    expect(within(row).getByLabelText(/^R\$ por kg/)).toBeInTheDocument();
    fireEvent.change(within(row).getByLabelText(/^Unidade da linha/), { target: { value: "un" } });
    expect(within(row).getByLabelText(/^R\$ por unidade/)).toBeInTheDocument();
    fireEvent.change(within(row).getByLabelText(/^Unidade da linha/), { target: { value: "emb" } });
    expect(within(row).getByLabelText(/^R\$ por embalagem/)).toBeInTheDocument();
    expect(within(row).queryByLabelText(/^R\$ por kg/)).toBeNull();
  });

  it("a revisão mostra o valor total e avisa que item sem custo não soma", async () => {
    const user = userEvent.setup();
    await open();
    await paste(user, ["Farinha de trigo tipo 1\t25\tkg\t\t4,80", "Açúcar cristal\t10\tkg\t\t3,5", "Granola da casa\t3\tkg"].join("\n"));
    const total = screen.getByTestId("valor-total");
    expect(total.textContent?.replace(/\s/g, " ")).toContain("R$ 155,00");
    expect(total).toHaveTextContent("Itens sem custo não somam.");
    expect(screen.getByTestId("resumo-inventario")).toHaveTextContent("1 sem custo");
  });

  it("sem nenhum custo informado o total é R$ 0,00", async () => {
    const user = userEvent.setup();
    await open();
    await paste(user, "Granola da casa\t3\tkg");
    expect(screen.getByTestId("valor-total").textContent?.replace(/\s/g, " ")).toContain("R$ 0,00");
  });
});

describe("Pendências na hora", () => {
  it("embalagem sem conteúdo é marcada na linha ao escolher a unidade, e Gravar mostra o motivo", async () => {
    const user = userEvent.setup();
    await open();
    await paste(user, "Granola da casa\t3\tkg");
    const row = rowElements()[0];
    expect(saveButton()).toBeEnabled();
    fireEvent.change(within(row).getByLabelText(/^Unidade da linha/), { target: { value: "emb" } });
    expect(within(row).getByText("Informe quanto vem em cada embalagem.")).toBeInTheDocument();
    expect(within(row).getByLabelText(/^Conteúdo de cada embalagem/)).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByTestId("resumo-inventario")).toHaveTextContent("1 linha incompleta");
    expect(saveButton()).toBeDisabled();
    expect(screen.getByTestId("motivo-bloqueio")).toHaveTextContent(/1 linha incompleta/);
    expect(saveButton()).toHaveAccessibleDescription(/1 linha incompleta/);

    await user.type(within(row).getByLabelText(/^Conteúdo de cada embalagem/), "500");
    expect(within(row).queryByText("Informe quanto vem em cada embalagem.")).toBeNull();
    expect(screen.getByTestId("resumo-inventario")).not.toHaveTextContent("incompleta");
    expect(saveButton()).toBeEnabled();
  });

  it("conta linhas incompletas e a decidir juntas, e 'Mostrar o que falta' revela o campo", async () => {
    const user = userEvent.setup();
    await open();
    await user.type(ingredientInput(rowElements()[0]), "Granola da casa");
    await user.click(await screen.findByRole("option", { name: /Criar "Granola da casa"/ }));
    await waitFor(() => expect(within(rowElements()[0]).getByLabelText(/^Quantidade/)).toHaveFocus());
    expect(screen.getByTestId("resumo-inventario")).toHaveTextContent("1 linha incompleta");
    expect(saveButton()).toBeDisabled();
    expect(within(rowElements()[0]).queryByText(/Informe a quantidade/)).toBeNull();
    await user.click(screen.getByRole("button", { name: "Mostrar o que falta" }));
    expect(within(rowElements()[0]).getByText(/Informe a quantidade/)).toBeInTheDocument();

    await paste(user, "Açucar cristalino\t10\tkg");
    expect(screen.getByTestId("resumo-inventario")).toHaveTextContent("1 linha incompleta · 1 a decidir");
  });
});

describe("Menu ⋯ por linha", () => {
  it("troca 'Duplicar' e 'Remover' soltos por um menu, que fecha com Esc e ao clicar fora", async () => {
    const user = userEvent.setup();
    await open();
    await paste(user, "Granola da casa\t3\tkg");
    expect(screen.queryByRole("button", { name: /^Duplicar/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Remover/ })).toBeNull();
    const trigger = screen.getByRole("button", { name: "Mais ações da linha 1" });
    expect(trigger).toHaveAttribute("aria-haspopup", "menu");
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    await user.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    const menu = screen.getByRole("menu", { name: "Ações da linha 1" });
    expect(within(menu).getAllByRole("menuitem").map((item) => item.textContent)).toEqual(["Duplicar linha 1", "Remover linha 1"]);
    expect(within(menu).getByRole("menuitem", { name: "Duplicar linha 1" })).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).toBeNull();
    expect(trigger).toHaveFocus();

    await user.click(trigger);
    expect(screen.getByRole("menu")).toBeInTheDocument();
    await user.click(screen.getByRole("textbox", { name: "Colar da planilha" }));
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("Duplicar e Remover pelo menu continuam funcionando", async () => {
    const user = userEvent.setup();
    await open();
    await paste(user, "Granola da casa\t3\tkg");
    await user.click(screen.getByRole("button", { name: "Mais ações da linha 1" }));
    await user.click(screen.getByRole("menuitem", { name: "Duplicar linha 1" }));
    await waitFor(() => expect(screen.getByTestId("resumo-inventario")).toHaveTextContent(/^2 itens/));
    await user.click(screen.getByRole("button", { name: "Mais ações da linha 2" }));
    await user.click(screen.getByRole("menuitem", { name: "Remover linha 2" }));
    await waitFor(() => expect(screen.getByTestId("resumo-inventario")).toHaveTextContent(/^1 item/));
  });
});

describe("Litro e ml", () => {
  it("oferece lançar como embalagem de 1 l e converte a linha", async () => {
    const user = userEvent.setup();
    await open();
    await paste(user, "Leite longa vida\t4\tl");
    const row = rowElements()[0];
    const offer = within(row).getByRole("group", { name: /Litro e ml na linha 1/ });
    expect(offer).toHaveTextContent("Lançar como embalagem de");
    expect(within(offer).getByLabelText(/^Lançar como embalagem de/)).toHaveValue("1");
    expect((within(row).getByLabelText(/^Unidade da linha/) as HTMLSelectElement).value).toBe("l");
    expect(saveButton()).toBeDisabled();

    await user.click(within(offer).getByRole("button", { name: /^Lançar como embalagem/ }));
    expect((within(row).getByLabelText(/^Unidade da linha/) as HTMLSelectElement).value).toBe("emb");
    expect(within(row).getByLabelText(/^Conteúdo de cada embalagem/)).toHaveValue("1");
    expect((within(row).getByLabelText(/^Unidade do conteúdo/) as HTMLSelectElement).value).toBe("l");
    expect(within(row).getByLabelText(/^Quantidade/)).toHaveValue("4");
    expect(within(row).queryByRole("group", { name: /Litro e ml/ })).toBeNull();
    expect(saveButton()).toBeEnabled();
  });

  it("em ml, usa o conteúdo informado na oferta", async () => {
    const user = userEvent.setup();
    await open();
    await paste(user, "Essência de baunilha\t3\tml");
    const row = rowElements()[0];
    const offer = within(row).getByRole("group", { name: /Litro e ml na linha 1/ });
    const content = within(offer).getByLabelText(/^Lançar como embalagem de/);
    await user.clear(content);
    await user.type(content, "500");
    await user.click(within(offer).getByRole("button", { name: /^Lançar como embalagem/ }));
    expect((within(row).getByLabelText(/^Unidade da linha/) as HTMLSelectElement).value).toBe("emb");
    expect(within(row).getByLabelText(/^Conteúdo de cada embalagem/)).toHaveValue("500");
    expect((within(row).getByLabelText(/^Unidade do conteúdo/) as HTMLSelectElement).value).toBe("ml");
  });

  it("escolher l ou ml na lista de unidades também mostra a oferta", async () => {
    const user = userEvent.setup();
    await open();
    await paste(user, "Granola da casa\t3\tkg");
    const row = rowElements()[0];
    fireEvent.change(within(row).getByLabelText(/^Unidade da linha/), { target: { value: "ml" } });
    expect(within(row).getByRole("group", { name: /Litro e ml na linha 1/ })).toBeInTheDocument();
  });
});

describe("Colunas do desktop", () => {
  it("o título usa a mesma grade e a mesma caixa da linha, em 1440 px", () => {
    const section = stripped.slice(stripped.indexOf(".inv-row__toggle {"));
    expect(section).toMatch(/\.inv-grid__head,\s*\.inv-row\s*\{\s*grid-template-columns:\s*2rem minmax\(12rem, 1fr\)/);
    expect(section).toMatch(/\.inv-grid__head\s*\{[^}]*border-left:\s*4px solid transparent/);
    expect(section).toMatch(/\.inv-grid__head\s*\{[^}]*border:\s*1px solid transparent/);
    expect(section).toMatch(/\.inv-grid__head\s*\{[^}]*padding:\s*0 0\.75rem/);
  });
});

describe("Celular (390 px)", () => {
  beforeEach(() => stubViewport(390));

  it("cada item tem um botão de detalhes, que avisa a pendência e abre ao tocar", async () => {
    const user = userEvent.setup();
    await open();
    await paste(user, "Granola da casa\t3\tkg");
    const row = rowElements()[0];
    const toggle = within(row).getByRole("button", { name: "Detalhes da linha 1" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(row).toHaveAttribute("data-open", "false");
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(row).toHaveAttribute("data-open", "true");
    await user.click(toggle);
    expect(row).toHaveAttribute("data-open", "false");

    fireEvent.change(within(row).getByLabelText(/^Unidade da linha/), { target: { value: "emb" } });
    expect(within(row).getByRole("button", { name: "Detalhes da linha 1 (com pendência)" })).toHaveTextContent("!");
    expect(row).toHaveAttribute("data-open", "true");
  });

  it("a lista fica numa linha por item e o resumo com o botão ficam fixos no rodapé", () => {
    const block = stripped.slice(stripped.lastIndexOf("@media (max-width: 720px)"));
    expect(block).toMatch(/\.inv-row\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)\s+3\.6rem\s+5\.9rem\s+2\.75rem/);
    expect(block).toMatch(/\.inv-row__details\s*\{[^}]*display:\s*none/);
    expect(block).toMatch(/\.inv-row\[data-open="true"\]\s*\.inv-row__details\s*\{[^}]*display:\s*grid/);
    expect(block).toMatch(/\.inv-batch__review\s*\{[^}]*position:\s*sticky[^}]*bottom:\s*0/);
    expect(block).toMatch(/\.inv-row__toggle\s*\{[^}]*min-height:\s*2\.75rem/);
    expect(block).toMatch(/\.inv-row__toggle\s*\{[^}]*min-width:\s*2\.75rem/);
    expect(block).not.toMatch(/transform\s*:\s*scale\s*\(/);
  });

  it("o resumo, o total e o botão Gravar continuam na tela, e os detalhes seguem acessíveis", async () => {
    const user = userEvent.setup();
    await open();
    await paste(user, "Farinha de trigo tipo 1\t25\tkg\t\t4,80");
    const row = rowElements()[0];
    for (const label of [/^Ingrediente/, /^Quantidade/, /^Unidade da linha/, /^Validade/, /^Lote/, /^R\$ por kg/]) {
      expect(within(row).getByLabelText(label)).toBeInTheDocument();
    }
    expect(screen.getByTestId("valor-total").textContent?.replace(/\s/g, " ")).toContain("R$ 120,00");
    expect(saveButton()).toBeEnabled();
  });
});
