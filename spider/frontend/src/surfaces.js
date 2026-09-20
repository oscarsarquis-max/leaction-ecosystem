/** Superfícies: Monitor (frontend da Spider), satélite e Experience. */

export function normalizePath(pathname = "/") {
  if (!pathname || pathname === "/") return "/";
  return pathname.replace(/\/+$/, "") || "/";
}

export function resolveSurface(pathname = "/") {
  const path = normalizePath(pathname);
  if (path === "/" || path === "/console" || path.startsWith("/console/")) return "console";
  if (path === "/demo/contextual-link") return "hub";
  if (path === "/spiderbank" || path.startsWith("/spiderbank/")) return "spiderbank";
  return "console";
}

export function isSpiderBankPath(pathname = "/") {
  return resolveSurface(pathname) === "spiderbank";
}
