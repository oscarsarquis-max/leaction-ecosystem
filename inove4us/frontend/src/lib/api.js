async function request(path, options = {}) {
  const res = await fetch(path, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })

  let data = null
  try {
    data = await res.json()
  } catch {
    data = null
  }

  if (!res.ok) {
    const fromBody = data && (data.error || data.erro)
    const message =
      fromBody ||
      (res.status === 504
        ? 'A análise demorou mais que o esperado. Tente de novo em instantes.'
        : res.status === 502 || res.status === 503
          ? 'Serviço temporariamente indisponível. Tente de novo em instantes.'
          : 'Falha na requisição')
    const err = new Error(message)
    err.status = res.status
    err.data = data
    err.code = data?.code || (res.status === 504 ? 'GATEWAY_TIMEOUT' : null)
    throw err
  }
  return data
}

/** Cliente HTTP compartilhado (fetch + cookies de sessão). */
export { request }

export const api = {
  me: () => request('/api/auth/me'),
  checkEmail: (email) =>
    request('/api/auth/check-email', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),
  registerLead: (payload) =>
    request('/api/auth/register-lead', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  verifyCode: (email, code) =>
    request('/api/auth/verify-code', {
      method: 'POST',
      body: JSON.stringify({ email, code }),
    }),
  logout: () => request('/api/auth/logout', { method: 'POST', body: '{}' }),
  completeNinaOnboarding: () =>
    request('/api/auth/nina-onboarding', {
      method: 'POST',
      body: JSON.stringify({ done: true }),
    }),
  resetNinaOnboarding: () =>
    request('/api/auth/nina-onboarding', {
      method: 'POST',
      body: JSON.stringify({ reset: true }),
    }),
  dismissNotice: (id) =>
    request(`/api/notices/${id}/dismiss`, {
      method: 'POST',
      body: '{}',
    }),
  getMural: (includeLidos = false) => {
    const q = includeLidos ? '?include_lidos=1' : ''
    return request(`/api/mural${q}`)
  },
  getAvisosMesa: () => request('/api/avisos-mesa'),
  marcarCienciaMural: (id) =>
    request(`/api/mural/${id}/ciencia`, { method: 'POST' }),
  estruturarWizard: (payload) =>
    request('/api/wizard/estruturar', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  catalogoMetodologiasWizard: () => request('/api/wizard/catalogo-metodologias'),
  selecionarCaminho: (caminho) =>
    request('/api/wizard/selecionar-caminho', {
      method: 'POST',
      body: JSON.stringify({ caminho }),
    }),
  listAgendaEventos: (mes, planoSession, extra = {}) => {
    const q = new URLSearchParams()
    if (mes) q.set('mes', mes)
    if (planoSession) q.set('plano_session', planoSession)
    if (extra.origem) q.set('origem', extra.origem)
    const qs = q.toString()
    return request(`/api/agenda-eventos${qs ? `?${qs}` : ''}`)
  },

  grafoAgenda: (periodoLetivoId) => {
    const q = new URLSearchParams()
    if (periodoLetivoId != null && periodoLetivoId !== '') {
      q.set('periodo_letivo_id', String(periodoLetivoId))
    }
    const qs = q.toString()
    return request(`/api/agenda-eventos/grafo${qs ? `?${qs}` : ''}`)
  },
  createAgendaEvento: (payload) =>
    request('/api/agenda-eventos', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  registrarAulas: (payload) =>
    request('/api/agenda-eventos/registrar-aulas', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getAgendaEvento: (id) => request(`/api/agenda-eventos/${id}`),
  /** mesa do desafio (cadeia + plano_session), opcionalmente filtrado por aula_id. */
  getAgendaKanban: (id, aulaId = null) => {
    const q = new URLSearchParams()
    if (aulaId != null && aulaId !== '') q.set('aula_id', String(aulaId))
    const qs = q.toString()
    return request(`/api/agenda-eventos/${id}/kanban${qs ? `?${qs}` : ''}`)
  },
  getDesafioDoEvento: (idEvento) => request(`/api/agenda-eventos/${idEvento}/desafio`),
  getDesafio: (desafioId) => request(`/api/desafios/${desafioId}`),
  /** Persiste desafio com plano/cards (sem aulas) — retomada sem nova IA. */
  criarDesafio: (payload) =>
    request('/api/desafios', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listDesafios: ({ q, limit } = {}) => {
    const params = new URLSearchParams()
    if (q) params.set('q', q)
    if (limit != null) params.set('limit', String(limit))
    const qs = params.toString()
    return request(`/api/desafios${qs ? `?${qs}` : ''}`)
  },
  getDesafioMesa: (desafioId) => request(`/api/desafios/${desafioId}/mesa`),
  listDesafioExecucoes: (desafioId) => request(`/api/desafios/${desafioId}/execucoes`),
  replicarDesafio: (desafioId, payload) =>
    request(`/api/desafios/${desafioId}/replicar`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  convidarColaborador: (desafioId, payload) =>
    request(`/api/desafios/${desafioId}/convidar`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listDesafioColaboradores: (desafioId) =>
    request(`/api/desafios/${desafioId}/colaboradores`),
  getConvite: (token) => request(`/api/convites/${encodeURIComponent(token)}`),
  aceitarConvite: (token) =>
    request(`/api/convites/${encodeURIComponent(token)}/aceitar`, {
      method: 'POST',
      body: '{}',
    }),
  recusarConvite: (token) =>
    request(`/api/convites/${encodeURIComponent(token)}/recusar`, {
      method: 'POST',
      body: '{}',
    }),
  concluirAula: (id, payload) =>
    request(`/api/agenda-eventos/${id}/concluir-aula`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  enviarFeedbackAula: (id, payload) =>
    request(`/api/agenda-eventos/${id}/feedback`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateAgendaEstado: (id, payload) =>
    request(`/api/agenda-eventos/${id}/estado`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  /** Adaptação Inclusiva (PEI) — gera subcard via IA. */
  adaptarPei: (payload) =>
    request('/api/kanban/adaptar-pei', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateAgendaEvento: (id, payload) =>
    request(`/api/agenda-eventos/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteAgendaEvento: (id) =>
    request(`/api/agenda-eventos/${id}`, { method: 'DELETE' }),
  enviarFeedback: ({ tipo, mensagem }) =>
    request('/api/feedbacks', {
      method: 'POST',
      body: JSON.stringify({ tipo, mensagem }),
    }),
  /** Árvore do assistente (Hub CMS + fallback local). */
  getAssistenteChat: () => request('/api/assistente-chat'),
  /** Micro-CMS Hub — colunas /acesso (config_key=inove4us). */
  getCmsSite: (configKey = 'inove4us') =>
    request(`/api/cms/site?config_key=${encodeURIComponent(configKey)}`),
  createBillingCheckout: (sku = 'golive-50') =>
    request('/api/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ sku }),
    }),
  /** Vitrine de planos no Action Hub (escolha antes do pagamento). */
  getBillingPlansUrl: () => request('/api/billing/plans-url'),
}
