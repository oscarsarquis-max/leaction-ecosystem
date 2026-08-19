/** Base da API: vazio = same-origin (prod Caddy). Dev default localhost:8010. */
export function resolveApiBase() {
  const raw = import.meta.env.VITE_API_BASE
  if (raw === undefined || raw === null || raw === '') {
    if (import.meta.env.PROD) return ''
    return 'http://localhost:8010'
  }
  return String(raw)
}
