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

/** Valor persistido do <option> BNCC (bate com rotulo_seletor da API). */
export function bnccOptionValue(item) {
  const rotulo = String(item?.rotulo_seletor || '').trim()
  if (rotulo) return rotulo
  const tema = String(item?.tema || '').trim()
  const codigo = String(item?.habilidade_codigo || '').trim()
  if (tema && codigo) return `${tema} — ${codigo}`
  return tema || codigo
}

/**
 * Quando vários itens compartilham o mesmo `tema` (unidade temática / objeto)
 * e o código muda, o enunciado oficial (`texto` / texto_oficial) é o campo
 * que diferencia de verdade — não um rótulo genérico.
 */
export function qualificadorBncc(item, lista = []) {
  const tema = String(item?.tema || '').trim().toLowerCase()
  if (!tema) return ''
  const dups = (lista || []).filter(
    (x) => String(x?.tema || '').trim().toLowerCase() === tema,
  )
  if (dups.length < 2) return ''
  const texto = String(item?.texto_oficial || '').trim()
  const textos = new Set(
    dups.map((x) => String(x?.texto_oficial || '').trim()).filter(Boolean),
  )
  if (texto && textos.size > 1) return texto
  return String(item?.habilidade_codigo || '').trim()
}

export function filtraBnccPorBusca(lista, busca) {
  const q = String(busca || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
  if (!q) return lista || []
  const fold = (s) =>
    String(s || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
  return (lista || []).filter((b) => {
    const blob = [
      b?.tema,
      b?.habilidade_codigo,
      b?.texto_oficial,
      b?.rotulo_seletor,
      bnccOptionValue(b),
    ]
      .map(fold)
      .join(' ')
    return blob.includes(q)
  })
}

export function rotuloBnccOption(item, { max = 160, lista = [] } = {}) {
  const codigo = String(item?.habilidade_codigo || '').trim()
  const tema = String(item?.tema || '').trim()
  const qual = qualificadorBncc(item, lista)
  const qualShort =
    qual && qual.length > 72 ? `${qual.slice(0, 71)}…` : qual
  const suffix = qualShort ? ` (${qualShort})` : ''
  const fallback = `${bnccOptionValue(item)}${suffix}`
  if (!codigo) {
    if (fallback.length <= max) return fallback
    return `${fallback.slice(0, Math.max(1, max - 1))}…`
  }
  const prefix = `${codigo} — `
  const body = `${tema || ''}${suffix}`
  if (!body.trim()) return codigo
  if (prefix.length + body.length <= max) return `${prefix}${body}`
  const room = max - prefix.length - 1
  if (room < 1) return codigo
  return `${prefix}${body.slice(0, room)}…`
}
