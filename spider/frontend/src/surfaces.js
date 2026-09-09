/** Superfícies: Hub comercial, SpiderBank (satélite) e Console (técnica). */

export function normalizePath(pathname = "/") {
  if (!pathname || pathname === "/") return "/";
  return pathname.replace(/\/+$/, "") || "/";
}

export function resolveSurface(pathname = "/") {
  const path = normalizePath(pathname);
  if (path === "/" || path === "/demo/contextual-link") return "hub";
  if (path === "/console" || path.startsWith("/console/")) return "console";
  if (path === "/spiderbank" || path.startsWith("/spiderbank/")) return "spiderbank";
  return "hub";
}

export function isSpiderBankPath(pathname = "/") {
  return resolveSurface(pathname) === "spiderbank";
}
