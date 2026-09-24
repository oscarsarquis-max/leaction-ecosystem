/** Rotas de formulário do caminho manual: orientação começa recolhida e não sobrepõe campos. */
export function isManualFormRoute(pathname: string): boolean {
  if (pathname === "/componentes/ingredientes/consolidar") return true;
  if (pathname === "/componentes/estoque/abertura") return true;
  if (pathname === "/gestao/compras/entradas/nova") return true;
  return /^\/gestao\/compras\/entradas\/[^/]+$/.test(pathname);
}

/** Visão geral do Estoque: mesma recolha da orientação, sem virar formulário. */
export function isInventoryOverviewRoute(pathname: string): boolean {
  return pathname === "/componentes/estoque";
}

export function shouldStartCoachCollapsed(pathname: string): boolean {
  if (isManualFormRoute(pathname) || isInventoryOverviewRoute(pathname)) return true;
  if (typeof window !== "undefined" && typeof window.matchMedia === "function") {
    return window.matchMedia("(max-width: 720px)").matches;
  }
  return false;
}

/** Aberto, o painel ocupa o fluxo em vez de grudar por cima do conteúdo. */
export function coachOccupiesFlow(pathname: string): boolean {
  return isManualFormRoute(pathname) || isInventoryOverviewRoute(pathname);
}
