/**
 * Sensor CRM → POST /api/tracking/enviar (proxy Action-Sponge).
 * session_id UUID em localStorage (TTL 30 dias).
 */

const STORAGE_KEY = 'inove4us_crm_session'
const TTL_MS = 30 * 24 * 60 * 60 * 1000
const ENDPOINT = '/api/tracking/enviar'

function uuidv4() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

function readStore() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed?.id || !parsed?.expiresAt) return null
    if (Date.now() > Number(parsed.expiresAt)) {
      localStorage.removeItem(STORAGE_KEY)
      return null
    }
    return parsed
  } catch {
    return null
  }
}

function writeStore(id) {
  const payload = { id, expiresAt: Date.now() + TTL_MS }
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  } catch {
    /* private mode */
  }
  return payload
}

export function getTrackingSessionId() {
  const existing = readStore()
  if (existing) {
    writeStore(existing.id)
    return existing.id
  }
  return writeStore(uuidv4()).id
}

/**
 * @param {string} tipoEvento
 * @param {{ url?: string, idUsuario?: number|null, tempoGastoSegundos?: number, useBeacon?: boolean }} [options]
 */
export function trackEvent(tipoEvento, options = {}) {
  const body = {
    id_sessao: getTrackingSessionId(),
    tipo_evento: String(tipoEvento || 'pageview'),
    url_pagina:
      options.url ||
      (typeof window !== 'undefined'
        ? `${window.location.pathname}${window.location.search}`
        : '/'),
    id_usuario: options.idUsuario != null ? options.idUsuario : null,
    tempo_gasto_segundos: options.tempoGastoSegundos || 0,
  }

  try {
    if (
      options.useBeacon &&
      typeof navigator !== 'undefined' &&
      typeof navigator.sendBeacon === 'function'
    ) {
      const blob = new Blob([JSON.stringify(body)], { type: 'application/json' })
      navigator.sendBeacon(ENDPOINT, blob)
      return Promise.resolve({ ok: true, beacon: true })
    }
    return fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      keepalive: true,
      credentials: 'same-origin',
    })
      .then((res) => res.json().catch(() => ({ ok: true })))
      .catch(() => ({ ok: false }))
  } catch {
    return Promise.resolve({ ok: false })
  }
}

export function trackPageview(url, idUsuario = null) {
  return trackEvent('pageview', { url, idUsuario })
}

/** Eventos de funcionalidade inove4us (Action-Sponge). */
export const CrmEvents = {
  DESAFIO_ESTRUTURAR: 'desafio_estruturar',
  DESAFIO_ESTRUTURAR_ERRO: 'desafio_estruturar_erro',
  DESAFIO_ESTRUTURAR_FALLBACK: 'desafio_estruturar_fallback',
  PLANO_GERAR: 'plano_gerar',
  CAMINHO_SELECIONAR: 'caminho_selecionar',
  /** Abriu upgrade / foi para vitrine de planos (assinatura ou pacote). */
  CHECKOUT_INICIAR: 'checkout_iniciar',
  /** Retorno Mercado Pago — pagamento aprovado (créditos/assinatura). */
  PAGAMENTO_APROVADO: 'pagamento_aprovado',
  PAGAMENTO_PENDENTE: 'pagamento_pendente',
  PAGAMENTO_ERRO: 'pagamento_erro',
}
