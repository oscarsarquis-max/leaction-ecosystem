/**
 * Dicionário único de mensagens da importação (português pedagógico).
 * Reutilizado na tela de importação e no histórico.
 */
export const MSG = {
  data_ausente: 'Faltou a data desta aula. Corrija e tente novamente.',
  data_invalida: 'A data desta aula não foi reconhecida. Use o formato dia/mês/ano.',
  titulo_ausente: 'Faltou o título desta aula ou evento.',
  disciplina_nao_encontrada:
    "Não encontramos '{nome}' no seu cadastro. Esta aula será importada sem esse vínculo.",
  vinculo_parcial:
    'Instituição ou curso informados sem disciplina. Esta aula será importada sem vínculo.',
  atualizado: 'Esta aula já tinha sido importada antes; os dados foram atualizados.',
  criado: 'Aula ou evento criado com sucesso.',
  arquivo_vazio: 'Não encontramos nenhuma linha de aula ou evento neste arquivo.',
  arquivo_grande: 'Este arquivo tem muitas linhas. Divida em partes menores e tente novamente.',
  arquivo_invalido:
    'Não foi possível ler este arquivo. Envie uma planilha de planejamento e tente novamente.',
  sem_sessao: 'Sua sessão expirou. Entre novamente para continuar.',
  falha_gravar: 'Não foi possível salvar esta linha. Corrija os dados e tente novamente.',
  pendente: 'Esta linha precisa de correção antes de ser importada.',
  selecione_arquivo: 'Escolha sua planilha de planejamento para continuar.',
}

export function mensagemImportacao(codeOrText, vars = {}) {
  if (!codeOrText) return MSG.falha_gravar
  const key = String(codeOrText)
  const template = MSG[key]
  if (!template) return key
  return template.replace(/\{(\w+)\}/g, (_, name) =>
    vars[name] != null ? String(vars[name]) : `{${name}}`,
  )
}

export function mensagemDeErroApi(err) {
  if (!err) return MSG.falha_gravar
  if (err.code && MSG[err.code]) return mensagemImportacao(err.code)
  const raw = err.message || err.data?.error || err.data?.erro || ''
  if (MSG[raw]) return mensagemImportacao(raw)
  // Evita jargão técnico vindo do backend legado
  const lower = String(raw).toLowerCase()
  if (lower.includes('autentic') || lower.includes('sess')) return MSG.sem_sessao
  if (lower.includes('vazio') || lower.includes('sem registro')) return MSG.arquivo_vazio
  if (lower.includes('limite') || lower.includes('muitas')) return MSG.arquivo_grande
  if (lower.includes('ler') || lower.includes('arquivo') || lower.includes('formato')) {
    return MSG.arquivo_invalido
  }
  return raw || MSG.falha_gravar
}
