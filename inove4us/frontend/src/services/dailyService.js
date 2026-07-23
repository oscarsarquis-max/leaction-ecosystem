/**
 * Vetor Dia a Dia — cliente da API /api/daily/*
 * Usa o mesmo `request` de lib/api.js (fetch + credentials).
 */
import { request } from '../lib/api'

export function planejarAula(dados) {
  return request('/api/daily/planejar', {
    method: 'POST',
    body: JSON.stringify(dados),
  })
}

export function listarAulas({ page = 1, pageSize = 20 } = {}) {
  const q = new URLSearchParams()
  q.set('page', String(page))
  q.set('page_size', String(pageSize))
  return request(`/api/daily/?${q.toString()}`)
}

export function buscarAula(id) {
  return request(`/api/daily/${encodeURIComponent(id)}`)
}

export function atualizarAula(id, dados) {
  return request(`/api/daily/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(dados),
  })
}

export function excluirAula(id) {
  return request(`/api/daily/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })
}

export function sugerirDinamicas(termo = '') {
  const q = new URLSearchParams()
  if (termo) q.set('q', termo)
  const qs = q.toString()
  return request(`/api/daily/sugerir-dinamicas${qs ? `?${qs}` : ''}`)
}

export function isSchemaPendingError(err) {
  return (
    err?.status === 503 ||
    err?.code === 'schema_pending' ||
    err?.data?.code === 'schema_pending'
  )
}
