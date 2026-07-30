/**
 * Helpers compartilhados da fase task_breakdown (board + export Linear).
 */

export function unwrapArtifact(raw) {
  if (!raw || typeof raw !== 'object') return raw
  if (
    raw.artifact_data !== undefined &&
    (raw.status || raw.phase || raw.capability || raw.meta || raw.quality_score != null)
  ) {
    return raw.artifact_data
  }
  return raw
}

/** Extrai array de epics do artefato (envelope ou nested). */
export function extractTaskBreakdownEpics(artifactData) {
  if (!artifactData || typeof artifactData !== 'object') return null
  const inner = unwrapArtifact(artifactData)
  const candidates = [inner, artifactData]
  if (inner && typeof inner === 'object' && inner.artifact_data) {
    candidates.push(inner.artifact_data)
  }
  for (const cand of candidates) {
    if (!cand || typeof cand !== 'object') continue
    const epics = cand.epics
    if (Array.isArray(epics) && epics.length) {
      return epics.filter((e) => e && typeof e === 'object')
    }
  }
  return null
}

export function isTaskBreakdownPhase(phase) {
  if (!phase || typeof phase !== 'object') return false
  const id = String(phase.phase_id || phase.id || '')
    .trim()
    .toLowerCase()
  const name = String(phase.name || '')
    .trim()
    .toLowerCase()
  const capability = String(phase.capability || phase.type || '')
    .trim()
    .toLowerCase()
  if (
    capability === 'task_breakdown' ||
    capability === 'tasks_breakdown' ||
    capability === 'linear_export' ||
    capability === 'jira_export'
  ) {
    return true
  }
  if (
    id === 'task_breakdown' ||
    id.includes('task_breakdown') ||
    id.includes('tasks_breakdown')
  ) {
    return true
  }
  return /task\s*breakdown|épicos|epics|linear|jira/.test(name)
}

export function isPhaseExportReady(status) {
  const s = String(status || '').toUpperCase()
  return s === 'APPROVED' || s === 'SUCCESS' || s === 'COMPLETED'
}

/**
 * Retorna a fase task_breakdown pronta para export Linear, ou null.
 */
export function findLinearExportCandidate(phases) {
  if (!Array.isArray(phases)) return null
  for (const phase of phases) {
    if (!isTaskBreakdownPhase(phase)) continue
    if (!isPhaseExportReady(phase.status)) continue
    const epics = extractTaskBreakdownEpics(phase.artifact_data)
    if (!epics?.length) continue
    return { phase, epics }
  }
  return null
}
