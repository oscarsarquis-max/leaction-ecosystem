import { request } from '../lib/api'

export function listarImportacoes() {
  return request('/api/importacoes')
}

export function detalheImportacao(id) {
  return request(`/api/importacoes/${encodeURIComponent(id)}`)
}

/** Passo 1→2: interpreta a planilha sem gravar. */
export async function preVisualizarArquivo(file, mapeamento = null) {
  const body = new FormData()
  body.append('file', file)
  if (mapeamento && typeof mapeamento === 'object') {
    body.append('mapeamento', JSON.stringify(mapeamento))
  }
  const res = await fetch('/api/importacoes/pre-visualizar', {
    method: 'POST',
    credentials: 'include',
    body,
  })
  let data = null
  try {
    data = await res.json()
  } catch {
    data = null
  }
  if (!res.ok) {
    const err = new Error((data && (data.error || data.erro)) || 'arquivo_invalido')
    err.status = res.status
    err.data = data
    err.code = data?.code || null
    throw err
  }
  return data
}

/** Passo 3: confirma e grava as linhas ajustadas. */
export async function confirmarImportacao({ nome_arquivo, linhas }) {
  return request('/api/importacoes/confirmar', {
    method: 'POST',
    body: JSON.stringify({ nome_arquivo, linhas }),
  })
}
