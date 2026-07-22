import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BookOpen,
  ClipboardList,
  Download,
  FileDown,
  Layout,
  LogOut,
  MessageSquare,
  Search,
  Trash2,
  X,
} from 'lucide-react'
import Brand from '../components/Brand.jsx'
import AdminUiContent from '../components/AdminUiContent.jsx'
import { encerrarSessaoAdmin, obterAdminUsername } from '../services/adminAuth.js'
import {
  RULE_TYPE_LABELS,
  RULE_TYPE_TO_API,
  baixarPlanilhaAuditoria,
  criarRegra,
  desativarRegra,
  listarAuditoria,
  listarRegras,
  obterAdminMe,
} from '../services/adminApi.js'
import {
  baixarPdfHistoricoCompleto,
  baixarPdfHistoricoInteracao,
} from '../utils/exportHistoricoPdf.js'

const TABS = {
  DICTIONARY: 'dictionary',
  CONTENT: 'content',
  AUDIT: 'audit',
}

function parseInteractionHistory(item) {
  let history = item?.interaction_history
  if (!history) return []
  if (typeof history === 'string') {
    try {
      history = JSON.parse(history)
    } catch {
      return []
    }
  }
  return Array.isArray(history) ? history : []
}

function formatDiagnostico(item) {
  const partes = [item.conteudo_desafio, item.sintese, item.opcoes_selecionadas].filter(Boolean)
  return partes.join(' · ') || '—'
}

function csvEscape(value) {
  const raw = value == null ? '' : String(value)
  const normalized = raw.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  if (/[;"\n]/.test(normalized)) {
    return `"${normalized.replace(/"/g, '""')}"`
  }
  return normalized
}

function jsonParaCelula(valor) {
  if (valor == null || valor === '') return ''
  if (typeof valor === 'string') {
    try {
      const parsed = JSON.parse(valor)
      return JSON.stringify(parsed)
    } catch {
      return valor
    }
  }
  try {
    return JSON.stringify(valor)
  } catch {
    return String(valor)
  }
}

/** Exporta o estado atual da tabela de auditoria como mativas_auditoria.csv */
function exportarAuditoriaCsvLocal(itens) {
  const header = [
    'ID do Projeto',
    'Status',
    'Metodologia',
    'Justificativa',
    'Feedback da autora',
    'Curtido',
    'Data da curtida',
    'Data geracao do roteiro',
    'Passos (JSON)',
    'Professor ID',
    'Professor nome',
    'Professor email',
    'Professor estado',
    'Desafio ID',
    'Desafio / contexto',
    'Opcoes selecionadas',
    'Nivel de ensino',
    'Formato da aula',
    'Sintese',
    'Diagnostico (resumo)',
    'Dialogo IA (JSON)',
  ]
  const linhas = [header.join(';')]
  for (const item of itens || []) {
    const dialogo = parseInteractionHistory(item).map((h) => ({
      id: h.id ?? null,
      tipo_acao: h.tipo_acao ?? null,
      data_registro: h.data_registro ?? null,
      modelo_ia: h.modelo_ia ?? null,
      prompt_usuario: h.prompt_usuario ?? null,
      resposta_ia: h.resposta_ia ?? null,
      prompt_sistema: h.prompt_sistema ?? null,
      tokens_prompt: h.tokens_prompt ?? null,
      tokens_resposta: h.tokens_resposta ?? null,
    }))
    const curtido = Boolean(item.curtido || item.curtido_em)
    linhas.push(
      [
        item.roteiro_id ?? '',
        item.status ?? '',
        item.metodologia_recomendada ?? '',
        item.justificativa ?? '',
        item.feedback_autora ?? '',
        curtido ? 'Sim' : 'Nao',
        item.curtido_em ?? '',
        item.data_geracao ?? '',
        jsonParaCelula(item.passos_json),
        item.professor_id ?? '',
        item.professor_nome ?? '',
        item.professor_email ?? '',
        item.professor_estado ?? '',
        item.desafio_id ?? '',
        item.conteudo_desafio ?? '',
        item.opcoes_selecionadas ?? '',
        item.nivel_ensino ?? '',
        item.formato_aula ?? '',
        item.sintese ?? '',
        formatDiagnostico(item),
        jsonParaCelula(dialogo),
      ]
        .map(csvEscape)
        .join(';'),
    )
  }
  const blob = new Blob(['\ufeff' + linhas.join('\n')], {
    type: 'text/csv;charset=utf-8;',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'mativas_auditoria.csv'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function statusBadgeClass(status) {
  switch (status) {
    case 'Concluido':
      return 'bg-emerald-100 text-emerald-800'
    case 'Pendente':
      return 'bg-amber-100 text-amber-800'
    case 'Erro':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-700'
  }
}

function HistoricoModal({ item, onClose }) {
  const interacoes = parseInteractionHistory(item)

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-historico-titulo"
    >
      <div className="flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <h3 id="modal-historico-titulo" className="text-base font-semibold text-slate-900">
              Histórico de interações — Projeto #{item.roteiro_id}
            </h3>
            <p className="text-xs text-slate-500">
              {item.professor_nome} · {item.metodologia_recomendada || 'Sem metodologia'}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-500 transition hover:bg-slate-100"
            aria-label="Fechar"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto px-5 py-4">
          <div className="rounded-lg bg-slate-50 p-4 text-sm">
            <p className="mb-1 font-semibold text-slate-700">Diagnóstico do projeto</p>
            <p className="text-slate-600">{formatDiagnostico(item)}</p>
            <p className="mt-3 text-slate-700">
              <span className="font-semibold">Curtida:</span>{' '}
              {item.curtido || item.curtido_em ? (
                <span className="font-semibold text-rose-600">
                  Sim
                  {item.curtido_em
                    ? ` · ${new Date(item.curtido_em).toLocaleString('pt-BR')}`
                    : ''}
                </span>
              ) : (
                <span className="text-slate-500">Não</span>
              )}
            </p>
          </div>

          {interacoes.length === 0 ? (
            <div className="space-y-4 text-sm text-slate-600">
              <p className="rounded-lg border border-dashed border-slate-200 px-4 py-6 text-center">
                Nenhum registro em <code className="text-xs">interaction_history</code> para este
                projeto.
              </p>
              {item.justificativa && (
                <div className="rounded-lg bg-indigo-50 p-4">
                  <p className="mb-1 font-semibold text-indigo-900">Justificativa gerada</p>
                  <p className="whitespace-pre-wrap">{item.justificativa}</p>
                </div>
              )}
              {item.passos_json && (
                <div className="rounded-lg bg-slate-50 p-4">
                  <p className="mb-2 font-semibold text-slate-800">Passos do roteiro</p>
                  <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-xs">
                    {JSON.stringify(
                      typeof item.passos_json === 'string'
                        ? JSON.parse(item.passos_json)
                        : item.passos_json,
                      null,
                      2,
                    )}
                  </pre>
                </div>
              )}
              <div className="flex justify-end border-t border-slate-100 pt-4">
                <button
                  type="button"
                  onClick={() => baixarPdfHistoricoCompleto(item, [])}
                  className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-brand-primary transition hover:bg-indigo-50"
                >
                  <FileDown size={14} />
                  Formatar relatório em PDF
                </button>
              </div>
            </div>
          ) : (
            <>
              {interacoes.map((interacao, index) => (
                <div
                  key={interacao.id || index}
                  className="space-y-3 rounded-xl border border-slate-100 p-1"
                >
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span className="font-semibold uppercase tracking-wide">
                      Interação {index + 1}
                      {interacao.tipo_acao ? ` · ${interacao.tipo_acao}` : ''}
                    </span>
                    <span>
                      {interacao.modelo_ia || 'modelo não informado'}
                      {interacao.data_registro
                        ? ` · ${new Date(interacao.data_registro).toLocaleString('pt-BR')}`
                        : ''}
                    </span>
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <p className="mb-2 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-slate-500">
                      <MessageSquare size={14} />
                      Pergunta do usuário / professor
                    </p>
                    <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
                      {interacao.prompt_usuario || '—'}
                    </p>
                  </div>

                  <div className="rounded-xl border border-indigo-100 bg-indigo-50 p-4">
                    <p className="mb-2 text-xs font-bold uppercase tracking-wide text-indigo-700">
                      Resposta do agente (IA)
                    </p>
                    <pre className="max-h-80 overflow-y-auto whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-indigo-950">
                      {interacao.resposta_ia || '—'}
                    </pre>
                  </div>

                  {interacao.prompt_sistema && (
                    <details className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm">
                      <summary className="cursor-pointer font-medium text-slate-600">
                        Ver prompt de sistema (contexto interno)
                      </summary>
                      <pre className="mt-3 max-h-48 overflow-y-auto whitespace-pre-wrap font-mono text-xs text-slate-600">
                        {interacao.prompt_sistema}
                      </pre>
                    </details>
                  )}

                  {(interacao.tokens_prompt > 0 || interacao.tokens_resposta > 0) && (
                    <p className="text-xs text-slate-400">
                      Tokens: {interacao.tokens_prompt ?? 0} entrada ·{' '}
                      {interacao.tokens_resposta ?? 0} saída
                    </p>
                  )}

                  <div className="flex justify-end border-t border-slate-100 pt-3">
                    <button
                      type="button"
                      onClick={() => baixarPdfHistoricoInteracao(item, interacao, index)}
                      className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-brand-primary transition hover:bg-indigo-50"
                    >
                      <FileDown size={14} />
                      Formatar relatório em PDF
                    </button>
                  </div>
                </div>
              ))}

              <div className="flex justify-end border-t border-slate-200 pt-4">
                <button
                  type="button"
                  onClick={() => baixarPdfHistoricoCompleto(item, interacoes)}
                  className="inline-flex items-center gap-2 rounded-lg bg-brand-primary px-3 py-2 text-xs font-semibold text-white shadow-sm transition hover:opacity-90"
                >
                  <FileDown size={14} />
                  PDF do histórico completo
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function Admin() {
  const navigate = useNavigate()
  const [abaAtiva, setAbaAtiva] = useState(TABS.DICTIONARY)

  const [regras, setRegras] = useState([])
  const [carregandoRegras, setCarregandoRegras] = useState(true)
  const [erroRegras, setErroRegras] = useState('')
  const [salvandoRegra, setSalvandoRegra] = useState(false)

  const [palavraChave, setPalavraChave] = useState('')
  const [tipoAcao, setTipoAcao] = useState('substituir')
  const [palavraSubstituta, setPalavraSubstituta] = useState('')

  const [auditoria, setAuditoria] = useState([])
  const [carregandoAuditoria, setCarregandoAuditoria] = useState(false)
  const [erroAuditoria, setErroAuditoria] = useState('')
  const [modalItem, setModalItem] = useState(null)
  const [adminUsername, setAdminUsername] = useState(() => obterAdminUsername())
  const [baixandoPlanilha, setBaixandoPlanilha] = useState(false)
  const [erroPlanilha, setErroPlanilha] = useState('')
  const [buscaAuditoria, setBuscaAuditoria] = useState('')
  const [buscaAplicada, setBuscaAplicada] = useState('')

  const carregarRegras = useCallback(async () => {
    setCarregandoRegras(true)
    setErroRegras('')
    try {
      const dados = await listarRegras()
      setRegras(dados)
    } catch {
      setErroRegras('Não foi possível carregar as regras.')
      encerrarSessaoAdmin()
      navigate('/', { replace: true })
    } finally {
      setCarregandoRegras(false)
    }
  }, [navigate])

  const carregarAuditoria = useCallback(
    async (termo = '') => {
      setCarregandoAuditoria(true)
      setErroAuditoria('')
      try {
        const dados = await listarAuditoria(50, termo)
        setAuditoria(Array.isArray(dados) ? dados : [])
        setBuscaAplicada((termo || '').trim())
      } catch {
        setErroAuditoria('Não foi possível carregar a auditoria.')
        encerrarSessaoAdmin()
        navigate('/', { replace: true })
      } finally {
        setCarregandoAuditoria(false)
      }
    },
    [navigate],
  )

  useEffect(() => {
    carregarRegras()
  }, [carregarRegras])

  useEffect(() => {
    let ativo = true
    obterAdminMe()
      .then((me) => {
        if (ativo && me?.username) {
          setAdminUsername(me.username)
          localStorage.setItem('adminUsername', me.username)
        }
      })
      .catch(() => {})
    return () => {
      ativo = false
    }
  }, [])

  useEffect(() => {
    if (abaAtiva === TABS.AUDIT) {
      carregarAuditoria(buscaAplicada)
    }
    // Carrega ao abrir a aba; buscas manuais chamam carregarAuditoria diretamente.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abaAtiva])

  const handleBuscarAuditoria = (event) => {
    event?.preventDefault?.()
    carregarAuditoria(buscaAuditoria)
  }

  const handleExportarCsvTabela = () => {
    exportarAuditoriaCsvLocal(auditoria)
  }

  const handleBaixarPlanilha = async () => {
    setBaixandoPlanilha(true)
    setErroPlanilha('')
    try {
      await baixarPlanilhaAuditoria(500)
    } catch {
      setErroPlanilha('Não foi possível gerar a planilha. Tente novamente.')
    } finally {
      setBaixandoPlanilha(false)
    }
  }

  const handleLogout = () => {
    encerrarSessaoAdmin()
    navigate('/', { replace: true })
  }

  const handleAdicionarRegra = async (event) => {
    event.preventDefault()
    if (!palavraChave.trim()) return
    if (tipoAcao === 'substituir' && !palavraSubstituta.trim()) {
      setErroRegras('Informe a palavra substituta.')
      return
    }

    setSalvandoRegra(true)
    setErroRegras('')
    try {
      await criarRegra({
        keyword: palavraChave.trim(),
        rule_type: RULE_TYPE_TO_API[tipoAcao],
        replacement: tipoAcao === 'substituir' ? palavraSubstituta.trim() : null,
      })
      setPalavraChave('')
      setPalavraSubstituta('')
      setTipoAcao('substituir')
      await carregarRegras()
    } catch {
      setErroRegras('Falha ao adicionar a regra.')
    } finally {
      setSalvandoRegra(false)
    }
  }

  const handleInativarRegra = async (id) => {
    if (!window.confirm('Excluir/inativar esta regra?')) return
    setErroRegras('')
    try {
      await desativarRegra(id)
      await carregarRegras()
    } catch {
      setErroRegras('Falha ao inativar a regra.')
    }
  }

  return (
    <div className="admin-panel min-h-screen bg-slate-50 text-slate-800">
      <header className="border-b border-slate-200 bg-white">
        <div className="admin-inner mx-auto flex max-w-6xl items-start justify-between gap-4 px-4 py-5 sm:px-6">
          <div className="admin-header-brand">
            <Brand />
            <h1 className="admin-header-title">Painel Administrativo</h1>
            <p className="admin-header-subtitle">
              Gestão de vocabulário, conteúdo da interface e auditoria de projetos
            </p>
            <p className="mt-2 text-xs text-slate-500">
              Credencial associada:{' '}
              <span className="font-semibold text-slate-700">{adminUsername}</span>
              <span className="text-slate-400"> · autenticação por senha administrativa</span>
            </p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="mt-1 inline-flex shrink-0 items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
          >
            <LogOut size={16} />
            Sair
          </button>
        </div>
      </header>

      <main className="admin-inner mx-auto max-w-6xl px-4 py-6 sm:px-6">
        <div className="admin-tabs mb-6 flex gap-2 rounded-xl bg-white p-1 shadow-sm ring-1 ring-slate-200">
          <button
            type="button"
            onClick={() => setAbaAtiva(TABS.DICTIONARY)}
            className={`admin-tab flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition ${
              abaAtiva === TABS.DICTIONARY
                ? 'active bg-brand-primary text-white shadow'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <BookOpen size={16} />
            Dicionário da IA
          </button>
          <button
            type="button"
            onClick={() => setAbaAtiva(TABS.CONTENT)}
            className={`admin-tab flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition ${
              abaAtiva === TABS.CONTENT
                ? 'active bg-brand-primary text-white shadow'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <Layout size={16} />
            Conteúdo da Interface
          </button>
          <button
            type="button"
            onClick={() => setAbaAtiva(TABS.AUDIT)}
            className={`admin-tab flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition ${
              abaAtiva === TABS.AUDIT
                ? 'active bg-brand-primary text-white shadow'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <ClipboardList size={16} />
            Auditoria de Projetos
          </button>
        </div>

        {abaAtiva === TABS.DICTIONARY && (
          <section className="space-y-6">
            <div className="admin-card rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <h2 className="mb-4 text-base font-semibold text-slate-900">Adicionar nova regra</h2>
              <form
                onSubmit={handleAdicionarRegra}
                className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5 lg:items-end"
              >
                <label className="block text-sm">
                  <span className="mb-1 block font-medium text-slate-700">Palavra-chave</span>
                  <input
                    type="text"
                    value={palavraChave}
                    onChange={(e) => setPalavraChave(e.target.value)}
                    placeholder="ex.: metodologias ativas"
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/30"
                    required
                  />
                </label>
                <label className="block text-sm">
                  <span className="mb-1 block font-medium text-slate-700">Tipo de ação</span>
                  <select
                    value={tipoAcao}
                    onChange={(e) => setTipoAcao(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/30"
                  >
                    <option value="proibir">Proibir</option>
                    <option value="substituir">Substituir</option>
                  </select>
                </label>
                <label className="block text-sm sm:col-span-2">
                  <span className="mb-1 block font-medium text-slate-700">Palavra substituta</span>
                  <input
                    type="text"
                    value={palavraSubstituta}
                    onChange={(e) => setPalavraSubstituta(e.target.value)}
                    placeholder="Preencha quando a ação for Substituir"
                    disabled={tipoAcao !== 'substituir'}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/30 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                  />
                </label>
                <button
                  type="submit"
                  disabled={salvandoRegra}
                  className="rounded-lg bg-brand-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-600 disabled:opacity-60"
                >
                  {salvandoRegra ? 'Adicionando…' : 'Adicionar Regra'}
                </button>
              </form>
              <p className="mt-3 text-xs text-slate-500">
                Substituições afetam a interface inteira e só trocam palavras inteiras — por
                exemplo, &quot;dor&quot; não altera nomes como &quot;Problematizadora&quot;.
              </p>
              {erroRegras && <p className="mt-3 text-sm text-red-600">{erroRegras}</p>}
            </div>

            <div className="admin-card overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-slate-200">
              <div className="border-b border-slate-200 px-5 py-4">
                <h2 className="text-base font-semibold text-slate-900">Regras atuais</h2>
              </div>
              {carregandoRegras ? (
                <p className="px-5 py-8 text-sm text-slate-500">Carregando regras…</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                      <tr>
                        <th className="px-5 py-3 font-semibold">Palavra-chave</th>
                        <th className="px-5 py-3 font-semibold">Tipo</th>
                        <th className="px-5 py-3 font-semibold">Substituição</th>
                        <th className="px-5 py-3 font-semibold">Status</th>
                        <th className="px-5 py-3 font-semibold">Ação</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {regras.map((regra) => (
                        <tr key={regra.id} className="hover:bg-slate-50/80">
                          <td className="px-5 py-3 font-medium text-slate-900">{regra.keyword}</td>
                          <td className="px-5 py-3">
                            {RULE_TYPE_LABELS[regra.rule_type] || regra.rule_type}
                          </td>
                          <td className="px-5 py-3 text-slate-600">{regra.replacement || '—'}</td>
                          <td className="px-5 py-3">
                            <span
                              className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                                regra.is_active
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : 'bg-slate-100 text-slate-500'
                              }`}
                            >
                              {regra.is_active ? 'Ativa' : 'Inativa'}
                            </span>
                          </td>
                          <td className="px-5 py-3">
                            {regra.is_active && (
                              <button
                                type="button"
                                onClick={() => handleInativarRegra(regra.id)}
                                className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-red-600 transition hover:bg-red-50"
                              >
                                <Trash2 size={14} />
                                Excluir/Inativar
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                      {regras.length === 0 && (
                        <tr>
                          <td colSpan={5} className="px-5 py-8 text-center text-slate-500">
                            Nenhuma regra cadastrada.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>
        )}

        {abaAtiva === TABS.CONTENT && <AdminUiContent />}

        {abaAtiva === TABS.AUDIT && (
          <section className="space-y-4">
            {erroAuditoria && (
              <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{erroAuditoria}</p>
            )}
            {erroPlanilha && (
              <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{erroPlanilha}</p>
            )}

            <form
              onSubmit={handleBuscarAuditoria}
              className="flex flex-col gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200 sm:flex-row sm:items-center"
            >
              <div className="min-w-0 flex-1">
                <input
                  type="text"
                  value={buscaAuditoria}
                  onChange={(e) => {
                    const limpo = e.target.value.replace(/[\u200B-\u200D\uFEFF]/g, '')
                    setBuscaAuditoria(limpo)
                  }}
                  placeholder="Buscar metodologia, contexto, professor..."
                  autoComplete="off"
                  spellCheck={false}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm text-slate-800 outline-none ring-brand-primary/30 transition focus:border-brand-primary focus:ring-2"
                  aria-label="Busca global na auditoria"
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="submit"
                  disabled={carregandoAuditoria}
                  className="inline-flex items-center gap-2 rounded-lg bg-brand-primary px-4 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Search size={14} />
                  Buscar
                </button>
                <button
                  type="button"
                  onClick={handleExportarCsvTabela}
                  disabled={carregandoAuditoria || auditoria.length === 0}
                  className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Download size={14} />
                  Exportar CSV
                </button>
                {buscaAplicada && (
                  <button
                    type="button"
                    onClick={() => {
                      setBuscaAuditoria('')
                      carregarAuditoria('')
                    }}
                    className="inline-flex items-center gap-1 rounded-lg px-3 py-2.5 text-xs font-medium text-slate-500 transition hover:bg-slate-100"
                  >
                    <X size={14} />
                    Limpar
                  </button>
                )}
              </div>
            </form>
            {buscaAplicada && (
              <p className="text-xs text-slate-500">
                Resultados para <span className="font-semibold text-slate-700">&quot;{buscaAplicada}&quot;</span>
                {' · '}
                {auditoria.length} projeto(s)
              </p>
            )}

            <div className="admin-card overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-slate-200">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-4">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">Projetos dos clientes</h2>
                  <p className="mt-0.5 text-xs text-slate-500">
                    Planilha completa: dados do professor, contexto do desafio, roteiro e diálogo
                    IA↔professor (coluna JSON).
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleBaixarPlanilha}
                  disabled={baixandoPlanilha || carregandoAuditoria}
                  className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-brand-primary transition hover:bg-indigo-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Download size={14} />
                  {baixandoPlanilha ? 'Gerando planilha…' : 'Criar planilha (CSV)'}
                </button>
              </div>
              {carregandoAuditoria ? (
                <p className="px-5 py-8 text-sm text-slate-500">Carregando projetos…</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                      <tr>
                        <th className="px-5 py-3 font-semibold">Projeto</th>
                        <th className="px-5 py-3 font-semibold">Cliente</th>
                        <th className="px-5 py-3 font-semibold">Metodologia</th>
                        <th className="px-5 py-3 font-semibold">Status</th>
                        <th className="px-5 py-3 font-semibold">Curtida</th>
                        <th className="px-5 py-3 font-semibold">Ação</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {auditoria.map((item) => (
                        <tr key={item.roteiro_id} className="hover:bg-slate-50/80">
                          <td className="px-5 py-3">
                            <p className="font-medium text-slate-900">#{item.roteiro_id}</p>
                            <p className="mt-0.5 max-w-xs truncate text-xs text-slate-500">
                              {formatDiagnostico(item)}
                            </p>
                          </td>
                          <td className="px-5 py-3">
                            <p className="font-medium text-slate-800">{item.professor_nome}</p>
                            <p className="text-xs text-slate-500">{item.professor_email}</p>
                          </td>
                          <td className="px-5 py-3 text-slate-700">
                            {item.metodologia_recomendada || '—'}
                          </td>
                          <td className="px-5 py-3">
                            <span
                              className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusBadgeClass(item.status)}`}
                            >
                              {item.status}
                            </span>
                          </td>
                          <td className="px-5 py-3">
                            {item.curtido || item.curtido_em ? (
                              <span className="inline-flex rounded-full bg-rose-100 px-2.5 py-0.5 text-xs font-semibold text-rose-700">
                                Sim
                              </span>
                            ) : (
                              <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-500">
                                Não
                              </span>
                            )}
                          </td>
                          <td className="px-5 py-3">
                            <button
                              type="button"
                              onClick={() => setModalItem(item)}
                              className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-brand-primary transition hover:bg-indigo-50"
                            >
                              Ver Histórico
                            </button>
                          </td>
                        </tr>
                      ))}
                      {auditoria.length === 0 && (
                        <tr>
                          <td colSpan={6} className="px-5 py-8 text-center text-slate-500">
                            {buscaAplicada
                              ? 'Nenhum projeto encontrado para esta busca.'
                              : 'Nenhum projeto encontrado.'}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>
        )}
      </main>

      {modalItem && <HistoricoModal item={modalItem} onClose={() => setModalItem(null)} />}
    </div>
  )
}

export default Admin
