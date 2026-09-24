/** Rotas de formulário do caminho manual: orientação começa recolhida e não sobrepõe campos. */
export function isManualFormRoute(pathname: string): boolean {
  if (pathname === "/componentes/ingredientes/consolidar") return true;
  if (pathname === "/componentes/estoque/abertura") return true;
  if (pathname === "/gestao/compras/entradas/nova") return false;
  return /^\/gestao\/compras\/entradas\/[^/]+$/.test(pathname);
}

export function shouldStartCoachCollapsed(pathname: string): boolean {
  if (isManualFormRoute(pathname)) return true;
  if (typeof window !== "undefined" && typeof window.matchMedia === "function") {
    return window.matchMedia("(max-width: 720px)").matches;
  }
  return false;
}
