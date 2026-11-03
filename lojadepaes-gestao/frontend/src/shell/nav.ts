import type { Etapa } from "../lib/api";

// O fluxo da padaria: 5 etapas, cada uma responde uma pergunta. As etapas 3 a 5 ainda não existem.
// O estado (ponto e frase) vem do servidor (GET /fluxo); isto é só o que vale antes dele chegar.
export const ETAPAS_BASE: Etapa[] = [
  { id: "entradas", nome: "Entradas", pergunta: "O que chegou?", estado: null, frase: "", href: "/entradas" },
  { id: "ingredientes", nome: "Ingredientes", pergunta: "O que eu tenho?", estado: null, frase: "", href: "/ingredientes" },
  { id: "produtos", nome: "Produtos", pergunta: "O que eu vendo?", estado: null, frase: "em breve", href: null },
  { id: "receitas", nome: "Receitas", pergunta: "Como eu faço?", estado: null, frase: "em breve", href: null },
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
  if (path.startsWith("/gestao/locais")) return "locais";
  if (path.startsWith("/gestao/usuarios")) return "usuarios";
  return "hoje";
}

export function trailFor(path: string): { group: string; page: string } {
  const id = activeNavId(path);
  const etapa = ETAPAS_BASE.find((e) => e.id === id);
  if (etapa) return { group: "Fluxo da padaria", page: etapa.nome };
  const gestao = GESTAO_ITENS.find((g) => g.id === id);
  if (gestao) return { group: "Gestão", page: gestao.label };
  return { group: "Hoje", page: "Hoje" };
}

export const PERGUNTAS: Record<string, string> = Object.fromEntries(ETAPAS_BASE.map((e) => [e.id, e.pergunta]));
