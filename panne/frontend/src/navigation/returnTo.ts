/** Destino de retorno contextual. Nunca /inicio. Nunca URL absoluta. */

export function safeReturnTo(raw: string | null | undefined, fallback: string): string {
  if (!raw) return fallback;
  const value = raw.trim();
  if (!value.startsWith("/")) return fallback;
  if (value.startsWith("//") || value.includes("://")) return fallback;
  if (value === "/inicio" || value.startsWith("/inicio/") || value.startsWith("/inicio?")) {
    return fallback;
  }
  return value;
}

export function listReturnParam(search: string): string {
  const qs = search.startsWith("?") ? search.slice(1) : search;
  const path = qs ? `/produtos?${qs}` : "/produtos";
  return encodeURIComponent(path);
}

export function productHref(productId: string, listSearch = ""): string {
  const encoded = listReturnParam(listSearch);
  return encoded === encodeURIComponent("/produtos")
    ? `/produtos/${productId}`
    : `/produtos/${productId}?from=${encoded}`;
}
