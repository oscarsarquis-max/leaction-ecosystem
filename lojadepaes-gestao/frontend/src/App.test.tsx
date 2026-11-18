import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import type { Fluxo, Organizacao, SessaoInfo } from "./lib/api";

const ORG: Organizacao = {
  id: "org-1",
  nome: "Loja de Pães – Boulangerie",
  nome_curto: "boulangerie",
  cnpj: "11222333000181",
  cnpj_formatado: "11.222.333/0001-81",
  fonte_loja: true,
  papel: "dono",
};

function sessao(sobre: Partial<SessaoInfo> = {}): SessaoInfo {
  return {
    usuario: "admin@lojadepaes.com.br",
    nome: "Loja de Pães",
    admin_plataforma: false,
    papel: "dono",
    permissoes: ["ver_hoje", "ver_estoque", "lancar", "ajustar", "juntar", "gerenciar_usuarios"],
    csrf: "c",
    fuso: "America/Sao_Paulo",
    organizacao: ORG,
    organizacoes: [ORG],
    precisa_escolher_organizacao: false,
    ...sobre,
  };
}

const FLUXO: Fluxo = {
  entradas_total: 2,
  entradas_pendentes: 1,
  proximo_passo: null,
  etapas: [
    { id: "entradas", nome: "Entradas", pergunta: "O que chegou?", estado: "atencao", frase: "1 pendente", href: "/entradas" },
    { id: "ingredientes", nome: "Ingredientes", pergunta: "O que eu tenho?", estado: "atencao", frase: "2 vencem em 7 dias", href: "/ingredientes" },
    { id: "produtos", nome: "Produtos", pergunta: "O que eu vendo?", estado: null, frase: "em breve", href: null },
    { id: "receitas", nome: "Receitas", pergunta: "Como eu faço?", estado: null, frase: "em breve", href: null },
    { id: "producao", nome: "Produção", pergunta: "O que faço hoje?", estado: null, frase: "em breve", href: null },
  ],
};

const HOJE = {
  hoje: "2026-11-02",
  ate: "2026-11-15",
  dias: 14,
  fonte_loja: true,
  compatibilidade: { ok: true, versao_loja: null, versao_conhecida: null, mensagem: null },
  fornadas: [],
  total_paes_fisicos: 0,
  fluxo: FLUXO,
  vence_em_7_dias: [],
  sem_saldo: [],
};

function servir(s: SessaoInfo | null, extra: Record<string, unknown> = {}) {
  const rotas: Record<string, unknown> = {
    "/api/v1/auth/sessao": s,
    "/api/v1/fluxo": FLUXO,
    "/api/v1/hoje": HOJE,
    ...extra,
  };
  const fetchMock = vi.fn(async (url: string, _init?: { body?: string }) => {
    const caminho = url.split("?")[0];
    if (caminho === "/api/v1/auth/sessao" && s === null) return { ok: false, status: 401, json: async () => ({ detail: "sem sessão" }) };
    if (!(caminho in rotas)) return { ok: false, status: 404, json: async () => ({ detail: "não achei" }) };
    return { ok: true, status: 200, json: async () => rotas[caminho] };
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function mediaQuery(estreito: boolean) {
  vi.stubGlobal(
    "matchMedia",
    (consulta: string) => ({
      matches: estreito && consulta.includes("max-width: 959px"),
      media: consulta,
      addEventListener: () => {},
      removeEventListener: () => {},
    }),
  );
}

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  mediaQuery(false);
});
afterEach(() => vi.unstubAllGlobals());

describe("o que cada pessoa vê ao entrar", () => {
  it("o membro da organização vê nome e CNPJ na barra e o fluxo da padaria no menu", async () => {
    servir(sessao());
    render(<App />);
    const organizacao = await screen.findByLabelText("Organização atual");
    expect(organizacao).toHaveTextContent("Loja de Pães – Boulangerie");
    expect(organizacao).toHaveTextContent("CNPJ 11.222.333/0001-81");

    const menu = screen.getByRole("navigation", { name: "Menu da Gestão" });
    expect(within(menu).getByText("Fluxo da padaria")).toBeInTheDocument();
    const entradas = within(menu).getByRole("link", { name: /Entradas/ });
    await waitFor(() => expect(entradas).toHaveTextContent("1 pendente"));
    expect(entradas).toHaveTextContent("atenção");
    expect(within(menu).getByRole("link", { name: /Ingredientes/ })).toHaveTextContent("2 vencem em 7 dias");
    // as etapas futuras aparecem, mas não são links
    expect(within(menu).queryByRole("link", { name: /Produtos/ })).not.toBeInTheDocument();
    expect(within(menu).getByText("O que eu vendo?")).toBeInTheDocument();
    expect(within(menu).getAllByText("em breve").length).toBeGreaterThanOrEqual(4);
    expect(within(menu).getByRole("link", { name: "Locais" })).toBeInTheDocument();
    expect(within(menu).getByRole("link", { name: "Usuários" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Loja de Pães" })).toBeInTheDocument();
  });

  it("só o dono vê Usuários no menu", async () => {
    servir(sessao({ papel: "operador", permissoes: ["ver_hoje", "ver_estoque", "lancar"] }));
    render(<App />);
    const menu = await screen.findByRole("navigation", { name: "Menu da Gestão" });
    expect(within(menu).queryByRole("link", { name: "Usuários" })).not.toBeInTheDocument();
  });

  it("o admin da plataforma, sem organização, só vê que a conta não opera nenhuma", async () => {
    servir(sessao({ usuario: "oscar", nome: "Oscar", admin_plataforma: true, papel: null, permissoes: [], organizacao: null, organizacoes: [] }));
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Sua conta não opera nenhuma organização" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Menu da Gestão" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Organização atual")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sair" })).toBeInTheDocument();
  });

  it("quem tem duas organizações escolhe uma antes de ver qualquer dado", async () => {
    const outra: Organizacao = { ...ORG, id: "org-2", nome: "Padaria do Bairro", cnpj_formatado: "12.ABC.345/01DE-35", fonte_loja: false };
    const fetchMock = servir(
      sessao({ organizacao: null, organizacoes: [ORG, outra], precisa_escolher_organizacao: true, papel: null, permissoes: [] }),
      { "/api/v1/auth/organizacao": sessao({ organizacao: outra, organizacoes: [ORG, outra] }) },
    );
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Em qual organização você vai trabalhar?" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Menu da Gestão" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Padaria do Bairro/ }));
    expect(await screen.findByLabelText("Organização atual")).toHaveTextContent("Padaria do Bairro");
    const chamada = fetchMock.mock.calls.find(([url]) => String(url).endsWith("/auth/organizacao"));
    expect(chamada).toBeTruthy();
    expect(JSON.parse(chamada![1]!.body!)).toEqual({ organizacao_id: "org-2" });
  });

  it("no celular a barra mostra a etapa atual com o ponto, e o CNPJ vai para a segunda linha", async () => {
    mediaQuery(true);
    window.history.replaceState(null, "", "/ingredientes");
    servir(sessao(), { "/api/v1/ingredientes": { ingredientes: [], pares_parecidos: [] } });
    render(<App />);
    const botao = await screen.findByRole("button", { name: /Ingredientes/ });
    expect(botao).toHaveAttribute("aria-expanded", "false");
    expect(within(botao).getByText("atenção")).toBeInTheDocument();
    const org = screen.getByLabelText("Organização atual");
    expect(org).toHaveTextContent("CNPJ 11.222.333/0001-81");
    await userEvent.click(botao);
    expect(botao).toHaveAttribute("aria-expanded", "true");
    expect(within(screen.getByRole("navigation", { name: "Menu da Gestão" })).getByRole("link", { name: /Entradas/ })).toBeInTheDocument();
  });

  it("no computador a barra de cima mostra só o título em Hoje, sem “Hoje / Hoje”", async () => {
    servir(sessao());
    render(<App />);
    await screen.findByLabelText("Organização atual");
    const trilha = document.querySelector(".gestao-trail")!;
    expect(trilha.textContent?.trim()).toBe("Hoje");
    expect(trilha.querySelector("span")).toBeNull();
  });

  it("endereço desconhecido volta para Hoje", async () => {
    window.history.replaceState(null, "", "/nao-existe");
    servir(sessao());
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Hoje", level: 1 })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/");
  });
});
