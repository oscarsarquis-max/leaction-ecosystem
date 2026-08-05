/** Gera traceparent W3C: 00-<trace-id 32 hex>-<parent-id 16 hex>-01 */
export function generateTraceparent() {
  const bytes = new Uint8Array(24);
  crypto.getRandomValues(bytes);
  const hex = [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
  const traceId = hex.slice(0, 32);
  const parentId = hex.slice(32, 48);
  return `00-${traceId}-${parentId}-01`;
}

export function extractTraceId(traceparent) {
  if (!traceparent) return null;
  const parts = String(traceparent).split("-");
  return parts.length >= 2 ? parts[1] : null;
}
