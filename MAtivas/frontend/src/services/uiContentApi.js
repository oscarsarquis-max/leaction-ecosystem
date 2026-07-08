import api from './api.js'

export async function buscarConteudoUi() {
  const { data } = await api.get('/api/ui/conteudo')
  return data
}
