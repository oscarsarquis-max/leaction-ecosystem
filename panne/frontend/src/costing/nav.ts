/** Navegação canônica da área econômica — CURSOR-028 organic. */
export type EconomicNavId =
  | "visao"
  | "formacao"
  | "variacao"
  | "precos"
  | "politicas"
  | "calculadora";

export type EconomicNavItem = {
  id: EconomicNavId;
  to: string;
  label: string;
  end?: boolean;
  permission?: string;
  /** Query opcional ao abrir (ex.: calculadora aberta). */
  search?: string;
};

export const ECONOMIC_NAV: EconomicNavItem[] = [
  { id: "visao", to: "/gestao/custos", label: "Visão geral", end: true },
  { id: "formacao", to: "/gestao/custos/formacao", label: "Formação do custo" },
  { id: "variacao", to: "/gestao/custos/variacao", label: "Previsto vs realizado" },
  { id: "precos", to: "/gestao/custos/precos", label: "Preços e histórico", permission: "costing.read" },
  { id: "politicas", to: "/gestao/custos/politicas", label: "Políticas e premissas" },
  {
    id: "calculadora",
    to: "/gestao/custos/calculadora",
    label: "Calculadora",
    permission: "costing.read",
  },
];

export function matchEconomicNav(pathname: string): EconomicNavId | null {
  if (!pathname.startsWith("/gestao/custos")) return null;
  if (pathname === "/gestao/custos" || pathname === "/gestao/custos/") return "visao";
  if (pathname.startsWith("/gestao/custos/formacao") || pathname.startsWith("/gestao/custos/decisao") || pathname.startsWith("/gestao/custos/calculos"))
    return "formacao";
  if (pathname.startsWith("/gestao/custos/variacao") || pathname.startsWith("/gestao/custos/previstos") || pathname.startsWith("/gestao/custos/realizados"))
    return "variacao";
  if (pathname.startsWith("/gestao/custos/precos")) return "precos";
  if (pathname.startsWith("/gestao/custos/politicas")) return "politicas";
  if (pathname.startsWith("/gestao/custos/calculadora") || pathname.startsWith("/gestao/custos/simulacoes"))
    return "calculadora";
  return "visao";
}

export function economicCrumbLabel(id: EconomicNavId | null): string {
  const item = ECONOMIC_NAV.find((row) => row.id === id);
  return item?.label ?? "Custos, preços e margem";
}
