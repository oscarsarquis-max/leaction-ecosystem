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
    const err = new Error((data && data.error) || 'Falha na requisição')
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}

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
  listAgendaEventos: (mes, planoSession) => {
    const q = new URLSearchParams()
    if (mes) q.set('mes', mes)
    if (planoSession) q.set('plano_session', planoSession)
    const qs = q.toString()
    return request(`/api/agenda-eventos${qs ? `?${qs}` : ''}`)
  },
  grafoAgenda: () => request('/api/agenda-eventos/grafo'),
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
  concluirAula: (id, payload) =>
    request(`/api/agenda-eventos/${id}/concluir-aula`, {
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
}
