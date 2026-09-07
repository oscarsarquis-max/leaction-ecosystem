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

/** Recorte piloto Escola Teste: 6º ano (EF) ou 1ª série (EM). */
export function inferCursoAnoBncc(turmaNome, cursoNome) {
  const t = String(turmaNome || '').toLowerCase()
  const c = String(cursoNome || '').toLowerCase()
  if (
    t.includes('6º') ||
    t.includes('6°') ||
    t.includes('6o ano') ||
    t.includes('6º ano')
  ) {
    return '6º ano'
  }
  if (/\b6\b/.test(t) && t.includes('ano')) return '6º ano'
  if (
    t.includes('1ª') ||
    t.includes('1°') ||
    t.includes('1a série') ||
    t.includes('1ª série') ||
    t.includes('serie')
  ) {
    return '1ª série'
  }
  if (c.includes('fundamental')) return '6º ano'
  if (c.includes('médio') || c.includes('medio')) return '1ª série'
  return ''
}
