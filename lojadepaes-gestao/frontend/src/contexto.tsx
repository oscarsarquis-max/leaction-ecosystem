import { createContext, useContext } from "react";
import type { SessaoInfo } from "./lib/api";

export type GestaoCtx = {
  sessao: SessaoInfo;
  /** Endereço atual, com a query (ex.: `?filtro=pendentes`). */
  search: string;
  navegar: (para: string, substituir?: boolean) => void;
  /** Depois de gravar algo, as bolinhas do menu precisam ser recalculadas. */
  atualizarFluxo: () => void;
  pode: (acao: string) => boolean;
  /** Nome da tela de segundo nível, quando ele não está no endereço (Receitas / Bolo). */
  definirTitulo?: (titulo: string | null) => void;
  tituloPagina?: string | null;
};

export const GestaoContext = createContext<GestaoCtx | null>(null);

export function useGestao(): GestaoCtx {
  const ctx = useContext(GestaoContext);
  if (!ctx) throw new Error("useGestao fora do GestaoContext");
  return ctx;
}
