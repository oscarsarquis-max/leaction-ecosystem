/**
 * Converte ementa (texto livre) em tópicos selecionáveis.
 * Convenção: uma linha = um item (aceita bullets e numeração).
 */
export function parseEmentaTopicos(ementa) {
  const raw = String(ementa || '')
  if (!raw.trim()) return []
  const seen = new Set()
  const out = []
  for (const line of raw.split(/\r?\n/)) {
    let t = line.trim()
    if (!t) continue
    t = t
      .replace(/^[-*•–—]+\s*/, '')
      .replace(/^\d+[.)]\s*/, '')
      .replace(/^[a-zA-Z][.)]\s*/, '')
      .trim()
    if (t.length < 2) continue
    const key = t.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    out.push(t)
  }
  return out
}
