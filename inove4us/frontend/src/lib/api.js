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
}
