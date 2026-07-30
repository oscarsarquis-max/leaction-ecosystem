import { unwrapArtifact } from './taskBreakdown'

function safeNodeId(name, index) {
  const base = String(name || `mod-${index + 1}`).replace(/[^a-zA-Z0-9_]/g, '_')
  return base || `m${index + 1}`
}

/** Monta Mermaid a partir do build_order (fallback quando o LLM omite o diagrama). */
export function architectureFromBuildOrder(buildOrder) {
  if (!Array.isArray(buildOrder) || !buildOrder.length) {
    return [
      'flowchart TB',
      '  UI[Apresentação / UI]',
      '  APP[Aplicação / API]',
      '  DATA[(Dados)]',
      '  UI --> APP --> DATA',
    ].join('\n')
  }

  const lines = ['flowchart TB']
  const ids = {}
  buildOrder.forEach((item, i) => {
    if (!item || typeof item !== 'object') return
    const name = String(item.modulo || `mod-${i + 1}`).trim()
    const id = safeNodeId(name, i)
    ids[name] = id
    const camada = String(item.camada || '').trim()
    const label = camada ? `${name} (${camada})` : name
    lines.push(`  ${id}["${label.replace(/"/g, "'")}"]`)
  })
  buildOrder.forEach((item) => {
    if (!item || typeof item !== 'object') return
    const name = String(item.modulo || '').trim()
    const src = ids[name]
    if (!src) return
    const deps = Array.isArray(item.depende_de) ? item.depende_de : []
    deps.forEach((dep) => {
      const dst = ids[String(dep || '').trim()]
      if (dst) lines.push(`  ${dst} --> ${src}`)
    })
  })
  if (lines.length === 1) return architectureFromBuildOrder([])
  return lines.join('\n')
}

function pickBuildOrder(...candidates) {
  for (const cand of candidates) {
    if (!cand || typeof cand !== 'object') continue
    if (Array.isArray(cand.build_order) && cand.build_order.length) {
      return cand.build_order
    }
  }
  return null
}

/** Extrai mermaid de arquitetura do artefato SDD (campo ou fallback build_order). */
export function extractArchitectureMermaid(artifactData) {
  if (!artifactData || typeof artifactData !== 'object') return null
  const inner = unwrapArtifact(artifactData)
  const candidates = [inner, artifactData]
  if (inner && typeof inner === 'object' && inner.artifact_data) {
    candidates.push(inner.artifact_data)
  }
  for (const cand of candidates) {
    if (!cand || typeof cand !== 'object') continue
    const raw =
      cand.architecture_mermaid ||
      cand.architecture_diagram ||
      cand.diagrama_arquitetura
    if (typeof raw === 'string' && raw.trim()) return raw.trim()
  }

  // Runs antigos / LLM sem o campo: deriva do build_order
  const order = pickBuildOrder(...candidates)
  if (order || isSddArtifact(artifactData)) {
    return architectureFromBuildOrder(order)
  }
  return null
}

export function isSddArtifact(artifactData) {
  if (!artifactData || typeof artifactData !== 'object') return false
  const inner = unwrapArtifact(artifactData)
  return Boolean(
    (typeof inner?.sdd_markdown === 'string' && inner.sdd_markdown.trim()) ||
      (typeof artifactData.sdd_markdown === 'string' &&
        artifactData.sdd_markdown.trim()),
  )
}
