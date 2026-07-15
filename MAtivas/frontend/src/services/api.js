import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000',
  headers: { 'Content-Type': 'application/json' },
})

/**
 * Gera e persiste um roteiro a partir do payload acumulado da jornada.
 * @param {object} payload - { nome, email, estado, desafio, opcoes,
 *   nivel, formato, participantes, sintese }
 * @returns {Promise<object>} roteiro criado (id, passos, etc.)
 */
export async function criarRoteiro(payload) {
  const { data } = await api.post('/api/roteiro', payload)
  return data
}

/**
 * Diagnóstico por Árvore de Decisão (Claude/Bedrock):
 * match_perfeito + alternativas_mesmo_ramo + fusao_estrategica.
 * @param {object} payload - { desafio, opcoes, sintese, nivel, formato }
 * @returns {Promise<object>}
 */
export async function diagnosticarMetodologia(payload) {
  const { data } = await api.post('/api/diagnostico', payload)
  return data
}

/**
 * Diálogo de refinamento: feedback sobre a abordagem escolhida →
 * novas sugestões com justificativa.
 * @param {object} payload
 */
export async function refinarDiagnostico(payload) {
  const { data } = await api.post('/api/diagnostico/refinar', payload)
  return data
}

/**
 * Consulta o status de processamento assíncrono de um roteiro.
 * @param {number} id
 * @returns {Promise<object>} { roteiroId, status, metodologia_recomendada, passos }
 */
export async function verificarStatusRoteiro(id) {
  const { data } = await api.get(`/api/roteiro/${id}/status`)
  return data
}

/**
 * Envia o roteiro/plano de aula por e-mail (Amazon SES).
 * @param {string} email - destinatário
 * @param {number} projectId - id do roteiro (roteiros.id)
 */
export async function enviarRoteiroEmail(email, projectId) {
  const { data } = await api.post('/api/roteiro/enviar-email', {
    email,
    project_id: projectId,
  })
  return data
}

/**
 * @param {number} roteiroId
 * @param {string} feedbackAutora
 */
export async function enviarFeedback(roteiroId, feedbackAutora) {
  const { data } = await api.post(`/api/roteiro/${roteiroId}/feedback`, {
    feedback_autora: feedbackAutora,
  })
  return data
}

/**
 * Atualiza a relação do professor com o livro e o opt-in do ecossistema.
 * @param {object} payload - { email, status_livro, opt_in_ecossistema }
 */
export async function atualizarLivro(payload) {
  const { data } = await api.put('/api/professor/livro', payload)
  return data
}

export default api
