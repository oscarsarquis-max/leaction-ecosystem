import type { Etapa } from "../lib/api";

// O fluxo da padaria: 5 etapas, cada uma responde uma pergunta. A etapa 5 ainda não existe.
// O estado (ponto e frase) vem do servidor (GET /fluxo); isto é só o que vale antes dele chegar.
export const ETAPAS_BASE: Etapa[] = [
  { id: "entradas", nome: "Entradas", pergunta: "O que chegou?", estado: null, frase: "", href: "/entradas" },
  { id: "ingredientes", nome: "Ingredientes", pergunta: "O que eu tenho?", estado: null, frase: "", href: "/ingredientes" },
  { id: "produtos", nome: "Produtos", pergunta: "O que eu vendo?", estado: null, frase: "", href: "/produtos" },
  { id: "receitas", nome: "Receitas", pergunta: "Como eu faço?", estado: null, frase: "", href: "/receitas" },
  { id: "producao", nome: "Produção", pergunta: "O que faço hoje?", estado: null, frase: "em breve", href: null },
];

export type GestaoItem = { id: string; label: string; href?: string; permissao?: string };

export const GESTAO_ITENS: GestaoItem[] = [
  { id: "custos", label: "Custos" },
  { id: "locais", label: "Locais", href: "/gestao/locais" },
  { id: "usuarios", label: "Usuários", href: "/gestao/usuarios", permissao: "gerenciar_usuarios" },
];

export function activeNavId(path: string): string {
  if (path.startsWith("/entradas")) return "entradas";
  if (path.startsWith("/ingredientes")) return "ingredientes";
  if (path.startsWith("/produtos")) return "produtos";
  if (path.startsWith("/receitas")) return "receitas";
  if (path.startsWith("/gestao/locais")) return "locais";
  if (path.startsWith("/gestao/usuarios")) return "usuarios";
  return "hoje";
}

/**
 * O que a barra de cima mostra.
 * - `secao`: o item do menu em que a pessoa está (o celular mostra este nome).
 * - `page`: o título da tela.
 * - `group`: só existe em telas de segundo nível (ex.: "Entradas / Entrada sem nota").
 *   Tela de primeiro nível mostra só o título, sem trilha.
 */
export function trailFor(path: string): { group: string | null; page: string; secao: string } {
  const id = activeNavId(path);
  const etapa = ETAPAS_BASE.find((e) => e.id === id);
  const gestao = GESTAO_ITENS.find((g) => g.id === id);
  const secao = etapa ? etapa.nome : gestao ? gestao.label : "Hoje";
  if (path.startsWith("/entradas/sem-nota")) return { group: "Entradas", page: "Entrada sem nota", secao };
  if (path.startsWith("/receitas/")) return { group: "Receitas", page: "Receita", secao: "Receitas" };
  return { group: null, page: secao, secao };
}

export const PERGUNTAS: Record<string, string> = Object.fromEntries(ETAPAS_BASE.map((e) => [e.id, e.pergunta]));
