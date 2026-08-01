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

/** Modo Aula — move 4 cards → Fazendo e persiste status em_execucao + data_inicio */
export function iniciarAula(id) {
  return request(`/api/daily/${encodeURIComponent(id)}/iniciar`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

/** Modo Aula — move 4 cards → Pronto, data_conclusao e status realizado */
export function encerrarAula(id) {
  return request(`/api/daily/${encodeURIComponent(id)}/encerrar`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

/** Retroalimentação pós-aula (ClassFeedbackModal) */
export function enviarFeedbackAula(id, payload) {
  return request(`/api/daily/${encodeURIComponent(id)}/feedback`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function sugerirDinamicas(termo = '', contexto = {}) {
  const q = new URLSearchParams()
  if (termo) q.set('q', termo)
  if (contexto?.tema) q.set('tema', contexto.tema)
  if (contexto?.objetivo) q.set('objetivo', contexto.objetivo)
  if (contexto?.conteudo) q.set('conteudo', contexto.conteudo)
  if (contexto?.limit) q.set('limit', String(contexto.limit))
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
