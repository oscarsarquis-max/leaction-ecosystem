import { request } from '../lib/api'

export function listarInstituicoes(params = {}) {
  const q = new URLSearchParams()
  if (params.includeInactive) q.set('include_inactive', '1')
  const qs = q.toString()
  return request(`/api/instituicoes${qs ? `?${qs}` : ''}`)
}

export function criarInstituicao(payload) {
  return request('/api/instituicoes', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function atualizarInstituicao(id, payload) {
  return request(`/api/instituicoes/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function desativarInstituicao(id) {
  return request(`/api/instituicoes/${id}`, { method: 'DELETE' })
}

export function listarPeriodos(instituicaoId) {
  return request(`/api/instituicoes/${instituicaoId}/periodos-letivos`)
}

export function criarPeriodo(instituicaoId, payload) {
  return request(`/api/instituicoes/${instituicaoId}/periodos-letivos`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function atualizarPeriodo(periodoId, payload) {
  return request(`/api/periodos-letivos/${periodoId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function desativarPeriodo(periodoId) {
  return request(`/api/periodos-letivos/${periodoId}`, { method: 'DELETE' })
}

export function marcarPeriodoEmCurso(periodoId) {
  return request(`/api/periodos-letivos/${periodoId}/marcar-em-curso`, {
    method: 'POST',
    body: '{}',
  })
}

export function isSchemaPendingError(err) {
  return err?.status === 503 || err?.code === 'schema_pending' || err?.data?.code === 'schema_pending'
}

// --- Etapa 2: Cursos / Disciplinas ---

export function listarCursos(periodoId) {
  return request(`/api/periodos-letivos/${periodoId}/cursos`)
}

export function criarCurso(periodoId, payload) {
  return request(`/api/periodos-letivos/${periodoId}/cursos`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function atualizarCurso(cursoId, payload) {
  return request(`/api/cursos/${cursoId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function desativarCurso(cursoId) {
  return request(`/api/cursos/${cursoId}`, { method: 'DELETE' })
}

export function listarDisciplinas(cursoId) {
  return request(`/api/cursos/${cursoId}/disciplinas`)
}

export function criarDisciplina(cursoId, payload) {
  return request(`/api/cursos/${cursoId}/disciplinas`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function atualizarDisciplina(disciplinaId, payload) {
  return request(`/api/disciplinas/${disciplinaId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function desativarDisciplina(disciplinaId) {
  return request(`/api/disciplinas/${disciplinaId}`, { method: 'DELETE' })
}

// --- Turmas (1 curso → N turmas) ---

export function listarTurmas(cursoId) {
  return request(`/api/cursos/${cursoId}/turmas`)
}

export function criarTurma(cursoId, payload) {
  return request(`/api/cursos/${cursoId}/turmas`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function atualizarTurma(turmaId, payload) {
  return request(`/api/turmas/${turmaId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function desativarTurma(turmaId) {
  return request(`/api/turmas/${turmaId}`, { method: 'DELETE' })
}

/** Turmas ativas do professor (selects ao registrar aula). */
export function listarMinhasTurmas() {
  return request('/api/me/turmas')
}

/** Alocações School espelhadas (disciplina + turma). */
export function listarAlocacoesEscola() {
  return request('/api/me/alocacoes-escola')
}
