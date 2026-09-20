const FALLBACK = "/admin/produtos";

export function safeAdminNext(raw: string | null | undefined): string {
  if (!raw) {
    return FALLBACK;
  }
  let value = raw.trim();
  try {
    value = decodeURIComponent(value);
  } catch {
    return FALLBACK;
  }
  if (
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.includes("://") ||
    value.includes("\\") ||
    value.includes("..")
  ) {
    return FALLBACK;
  }
  const path = value.split("?")[0].split("#")[0];
  if (path === "/admin" || path === "/admin/login") {
    return FALLBACK;
  }
  if (path === "/admin/produtos" || path.startsWith("/admin/produtos/")) {
    return path;
  }
  if (path === "/admin/pedidos" || path.startsWith("/admin/pedidos/")) {
    return path;
  }
  return FALLBACK;
}

export function storefrontAccessUrl(nextPath: string): string {
  return `/?next=${encodeURIComponent(safeAdminNext(nextPath))}#acesso`;
}

export function goToPath(path: string): void {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function replaceWithPath(path: string): void {
  window.history.replaceState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function nextFromLocation(search = window.location.search): string {
  return safeAdminNext(new URLSearchParams(search).get("next"));
}
