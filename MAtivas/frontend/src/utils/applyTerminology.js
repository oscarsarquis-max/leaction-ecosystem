/**
 * Aplica substituições de vocabulário (regras admin) em qualquer texto da UI.
 * Substitui apenas palavras/frases inteiras — nunca trechos dentro de outras palavras
 * (ex.: "dor" não altera "Problematizadora").
 */

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function patternForKeyword(keyword, ignoreCase) {
  const escaped = escapeRegex(keyword.trim())
  const flags = `${ignoreCase === false ? 'g' : 'gi'}u`
  // Limites unicode: não substituir se houver letra/número imediatamente antes ou depois.
  return new RegExp(`(?<![\\p{L}\\p{N}])${escaped}(?![\\p{L}\\p{N}])`, flags)
}

export function applyTerminology(text, substituicoes = []) {
  if (!text || !substituicoes?.length) return text ?? ''

  let resultado = String(text)

  const ordenadas = [...substituicoes].sort(
    (a, b) => (b.de || b.keyword || '').length - (a.de || a.keyword || '').length,
  )

  for (const regra of ordenadas) {
    const de = (regra.de || regra.keyword || '').trim()
    const para = regra.para ?? regra.replacement ?? ''
    if (!de || !para) continue

    resultado = resultado.replace(
      patternForKeyword(de, regra.ignore_case !== false),
      para,
    )
  }

  return resultado
}
