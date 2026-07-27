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
    const message =
      (data && (data.error || data.erro)) || 'Falha na requisição'
    const err = new Error(message)
    err.status = res.status
    err.data = data
    err.code = data?.code || null
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
  dismissNotice: (id) =>
    request(`/api/notices/${id}/dismiss`, {
      method: 'POST',
      body: '{}',
    }),
  estruturarWizard: (payload) =>
    request('/api/wizard/estruturar', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
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
  concluirAula: (id, payload) =>
    request(`/api/agenda-eventos/${id}/concluir-aula`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateAgendaEstado: (id, payload) =>
    request(`/api/agenda-eventos/${id}/estado`, {
      method: 'PUT',
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
  createBillingCheckout: (sku = 'golive-50') =>
    request('/api/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ sku }),
    }),
  /** Vitrine de planos no Action Hub (escolha antes do pagamento). */
  getBillingPlansUrl: () => request('/api/billing/plans-url'),
}
