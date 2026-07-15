import api from './api.js'

/**
 * Autentica na área administrativa.
 * @param {string} password
 * @returns {Promise<object>} { sucesso, token, username }
 */
export async function loginAdmin(password) {
  const { data } = await api.post('/api/admin/login', { password })
  return data
}

/**
 * Persiste sessão admin no localStorage.
 * @param {string} token
 * @param {string} [username]
 */
export function salvarSessaoAdmin(token, username = 'admin') {
  localStorage.setItem('isAdmin', 'true')
  if (token) {
    localStorage.setItem('adminToken', token)
  }
  if (username) {
    localStorage.setItem('adminUsername', username)
  }
}

export function isAdminLogado() {
  return localStorage.getItem('isAdmin') === 'true'
}

export function obterAdminToken() {
  return localStorage.getItem('adminToken')
}

export function obterAdminUsername() {
  return localStorage.getItem('adminUsername') || 'admin'
}

export function encerrarSessaoAdmin() {
  localStorage.removeItem('isAdmin')
  localStorage.removeItem('adminToken')
  localStorage.removeItem('adminUsername')
}
