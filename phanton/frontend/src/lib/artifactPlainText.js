/** Texto legível a partir do envelope de artefato (Crystal Ball / fases). */

function unwrap(raw) {
  if (!raw || typeof raw !== 'object') return raw
  if (
    raw.artifact_data !== undefined &&
    (raw.status || raw.phase || raw.capability || raw.meta)
  ) {
    return raw.artifact_data
  }
  return raw
}

function asList(value) {
  if (Array.isArray(value)) return value
  if (value == null) return []
  return [value]
}

function formatPassos(passos) {
  return asList(passos)
    .map((p, i) => {
      if (typeof p === 'string') return `${i + 1}. ${p}`
      if (!p || typeof p !== 'object') return `${i + 1}. ${String(p)}`
      const titulo =
        p.titulo || p.titulo_do_card || p.title || p.imperativo || `Passo ${i + 1}`
      const desc =
        p.descricao ||
        p.como_executar_detalhado ||
        p.description ||
        p.descricao_base ||
        ''
      const tempo = p.tempo != null && p.tempo !== '' ? `\nTempo: ${p.tempo}` : ''
      return `${i + 1}. ${titulo}\n${desc}${tempo}`.trim()
    })
    .join('\n\n')
}

/**
 * Converte artefato (envelope ou inner) em texto normal para leitura/cópia.
 */
export function formatArtifactPlainText(artifact) {
  if (artifact == null) return ''
  if (typeof artifact === 'string') return artifact

  const inner = unwrap(artifact)
  if (inner == null) return ''
  if (typeof inner === 'string') return inner
  if (typeof inner !== 'object') return String(inner)

  if (inner.erro || inner.error) {
    return String(inner.erro || inner.error)
  }

  // Entrega / markdown
  for (const key of [
    'delivery',
    'entrega',
    'prd_markdown',
    'sdd_markdown',
    'cursor_prompt',
    'markdown',
    'documento',
  ]) {
    if (typeof inner[key] === 'string' && inner[key].trim()) {
      return inner[key].trim()
    }
  }

  // Biblioteca de passos / síntese
  const passos = inner.passos || inner.dinamica_passo_a_passo || inner.cards
  if (Array.isArray(passos) && passos.length) {
    const parts = []
    if (inner.metodologia_encontrada || inner.metodologia) {
      parts.push(`Metodologia: ${inner.metodologia_encontrada || inner.metodologia}`)
    }
    if (inner.resumo_sintese || inner.resumo || inner.summary) {
      parts.push(
        `Resumo:\n${inner.resumo_sintese || inner.resumo || inner.summary}`,
      )
    }
    parts.push(`Passos:\n\n${formatPassos(passos)}`)
    const pontos = asList(inner.pontos_chave || inner.key_points)
    if (pontos.length) {
      parts.push(
        `Pontos-chave:\n${pontos.map((p) => `- ${typeof p === 'string' ? p : JSON.stringify(p)}`).join('\n')}`,
      )
    }
    return parts.join('\n\n')
  }

  // Methodology
  if (inner.metodologia || inner.objetivo || inner.principios || inner.notas) {
    const lines = []
    if (inner.metodologia || inner.methodology) {
      lines.push(`Metodologia: ${inner.metodologia || inner.methodology}`)
    }
    if (inner.objetivo || inner.objective || inner.objetivo_geral) {
      lines.push(
        `Objetivo:\n${inner.objetivo || inner.objective || inner.objetivo_geral}`,
      )
    }
    const principios = asList(inner.principios || inner.principles)
    if (principios.length) {
      lines.push(
        `Princípios:\n${principios.map((p) => `- ${typeof p === 'string' ? p : JSON.stringify(p)}`).join('\n')}`,
      )
    }
    const notas = inner.notas || inner.notes || ''
    if (notas) {
      lines.push(
        `Notas:\n${Array.isArray(notas) ? notas.join('\n') : String(notas)}`,
      )
    }
    return lines.join('\n\n')
  }

  // Research / achados
  const achados = asList(inner.achados || inner.findings)
  if (achados.length) {
    return achados
      .map((a, i) => {
        if (typeof a === 'string') return `${i + 1}. ${a}`
        const t = a?.titulo || a?.title || `Achado ${i + 1}`
        const r = a?.resumo || a?.summary || ''
        return `${i + 1}. ${t}\n${r}`.trim()
      })
      .join('\n\n')
  }

  // Context7 hits
  if (Array.isArray(inner.context7_hits) && inner.context7_hits.length) {
    return inner.context7_hits
      .map((h, i) => {
        const t = h?.titulo || `Doc ${i + 1}`
        const r = h?.resumo || ''
        return `${i + 1}. ${t}\n${r}`.trim()
      })
      .join('\n\n')
  }

  // Fallback: campos escalares legíveis
  const scalars = Object.entries(inner).filter(
    ([, v]) => v != null && v !== '' && typeof v !== 'object',
  )
  if (scalars.length) {
    return scalars
      .map(([k, v]) => `${String(k).replaceAll('_', ' ')}: ${v}`)
      .join('\n')
  }

  try {
    return JSON.stringify(inner, null, 2)
  } catch {
    return String(inner)
  }
}
