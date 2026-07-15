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

export async function listarAuditoria(limit = 50, q = '') {
  try {
    const params = { limit }
    const termo = (q || '').replace(/[\u200B-\u200D\uFEFF]/g, '').trim()
    if (termo) params.q = termo
    const { data } = await api.get('/api/admin/auditoria', {
      params,
      headers: authHeaders(),
    })
    return data
  } catch (error) {
    handleAuthError(error)
  }
}

/**
 * Baixa a planilha CSV completa de auditoria (usuário, relatório e diálogo IA em JSON).
 * @param {number} [limit=500]
 */
export async function baixarPlanilhaAuditoria(limit = 500) {
  try {
    const { data } = await api.get('/api/admin/auditoria/planilha', {
      params: { limit },
      headers: authHeaders(),
      responseType: 'blob',
    })
    const blob = data instanceof Blob ? data : new Blob([data], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
    a.href = url
    a.download = `mativas-auditoria-acessos-${stamp}.csv`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    handleAuthError(error)
  }
}

export async function obterAdminMe() {
  try {
    const { data } = await api.get('/api/admin/me', { headers: authHeaders() })
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
