import api from './api.js'
import { encerrarSessaoAdmin, obterAdminToken } from './adminAuth.js'

function authHeaders() {
  return { Authorization: `Bearer ${obterAdminToken()}` }
}

function handleAuthError(error) {
  if (error?.response?.status === 401) {
    encerrarSessaoAdmin()
  }
  throw error
}

export const RULE_TYPE_TO_API = {
  proibir: 'bloqueada',
  substituir: 'substituir',
  forcar: 'obrigatoria',
}

export const RULE_TYPE_LABELS = {
  bloqueada: 'Proibir',
  substituir: 'Substituir',
  obrigatoria: 'Forçar',
}

export async function listarRegras() {
  try {
    const { data } = await api.get('/api/admin/rules', { headers: authHeaders() })
    return data
  } catch (error) {
    handleAuthError(error)
  }
}

export async function criarRegra({ keyword, rule_type, replacement }) {
  try {
    const { data } = await api.post(
      '/api/admin/rules',
      { keyword, rule_type, replacement: replacement || null },
      { headers: authHeaders() },
    )
    return data
  } catch (error) {
    handleAuthError(error)
  }
}

export async function desativarRegra(id) {
  try {
    const { data } = await api.delete(`/api/admin/rules/${id}`, { headers: authHeaders() })
    return data
  } catch (error) {
    handleAuthError(error)
  }
}

export async function listarAuditoria(limit = 50) {
  try {
    const { data } = await api.get('/api/admin/auditoria', {
      params: { limit },
      headers: authHeaders(),
    })
    return data
  } catch (error) {
    handleAuthError(error)
  }
}

export async function listarConteudoUi() {
  try {
    const { data } = await api.get('/api/admin/ui-content', { headers: authHeaders() })
    return data
  } catch (error) {
    handleAuthError(error)
  }
}

export async function salvarConteudoUi(item) {
  try {
    const { data } = await api.put('/api/admin/ui-content', item, { headers: authHeaders() })
    return data
  } catch (error) {
    handleAuthError(error)
  }
}
