import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import BrandLogo from '../components/BrandLogo'
import ImportacaoPasso1Guia from '../components/ImportacaoPasso1Guia'
import {
  mensagemDeErroApi,
  mensagemImportacao,
  MSG,
} from '../lib/importacoesMensagens'
import {
  confirmarImportacao,
  detalheImportacao,
  listarImportacoes,
  preVisualizarArquivo,
} from '../services/importacoesService'

const COLUNAS_PADRAO = [
  { key: 'titulo', label: 'Título da aula ou evento' },
  { key: 'data', label: 'Data' },
  { key: 'hora_inicio', label: 'Horário de início' },
  { key: 'hora_fim', label: 'Horário de término' },
  { key: 'tipo', label: 'É aula ou é evento?' },
  { key: 'instituicao', label: 'Instituição' },
  { key: 'curso', label: 'Curso' },
  { key: 'disciplina', label: 'Disciplina' },
  { key: 'assunto', label: 'Assunto' },
  { key: 'observacoes', label: 'Observações' },
]

function formatWhen(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR')
  } catch {
    return iso
  }
}

function linhaTemProblema(linha) {
  return linha?.status === 'pendente' || !linha?.titulo || !linha?.data
}

function revalidarLinha(linha) {
  const mensagens = []
  let status = 'ok'
  if (!(linha.titulo || '').trim()) {
    mensagens.push(MSG.titulo_ausente)
    status = 'pendente'
  }
  if (!(linha.data || '').trim() && !(linha.data_iso || '').trim()) {
    mensagens.push(MSG.data_ausente)
    status = 'pendente'
  }
  const avisos = (linha.mensagens || []).filter(
    (m) =>
      m &&
      !m.includes('Faltou') &&
      !m.includes('não foi reconhecida') &&
      status !== 'pendente',
  )
  if (status !== 'pendente' && (linha.status === 'aviso' || avisos.length)) {
    status = 'aviso'
    if (avisos.length) mensagens.push(...avisos)
    else if (linha.mensagens?.length) mensagens.push(...linha.mensagens)
  }
  return {
    ...linha,
    tipo: linha.tipo === 'evento' ? 'evento' : 'aula',
    tipo_label: linha.tipo === 'evento' ? 'Evento' : 'Aula',
    status,
    mensagens,
  }
}

export default function ImportacoesPage() {
  const navigate = useNavigate()

  const [passo, setPasso] = useState(1)
  const [file, setFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const [nomeArquivo, setNomeArquivo] = useState('')
  const [colunasArquivo, setColunasArquivo] = useState([])
  const [mapeamento, setMapeamento] = useState({})
  const [camposDestino, setCamposDestino] = useState(COLUNAS_PADRAO)
  const [linhas, setLinhas] = useState([])
  const [colOrder, setColOrder] = useState(COLUNAS_PADRAO.map((c) => c.key))
  const [dragCol, setDragCol] = useState(null)
  const [filtroPendentes, setFiltroPendentes] = useState(false)
  const [resultado, setResultado] = useState(null)

  const [lotes, setLotes] = useState([])
  const [loadingList, setLoadingList] = useState(true)

  const loadLotes = useCallback(async () => {
    setLoadingList(true)
    try {
      const data = await listarImportacoes()
      setLotes(Array.isArray(data?.importacoes) ? data.importacoes : [])
    } catch (err) {
      setError(mensagemDeErroApi(err))
    } finally {
      setLoadingList(false)
    }
  }, [])

  useEffect(() => {
    void loadLotes()
  }, [loadLotes])

  const resumo = useMemo(() => {
    const base = linhas.map(revalidarLinha)
    const prontas = base.filter((l) => l.status !== 'pendente')
    const pendentes = base.filter((l) => l.status === 'pendente')
    return {
      prontas: prontas.length,
      pendentes: pendentes.length,
      aulas: prontas.filter((l) => l.tipo === 'aula').length,
      eventos: prontas.filter((l) => l.tipo === 'evento').length,
      total: base.length,
    }
  }, [linhas])

  const linhasVisiveis = useMemo(() => {
    const base = linhas.map(revalidarLinha)
    if (!filtroPendentes) return base
    return base.filter((l) => l.status === 'pendente')
  }, [linhas, filtroPendentes])

  async function interpretarArquivo(arquivo, mapOverride = null) {
    setBusy(true)
    setError('')
    try {
      const data = await preVisualizarArquivo(arquivo, mapOverride)
      setNomeArquivo(data.nome_arquivo || arquivo.name)
      setColunasArquivo(data.colunas_arquivo || [])
      setMapeamento(data.mapeamento || {})
      if (Array.isArray(data.campos_destino) && data.campos_destino.length) {
        setCamposDestino(data.campos_destino)
      }
      setLinhas(Array.isArray(data.linhas) ? data.linhas.map(revalidarLinha) : [])
      setResultado(null)
      setFiltroPendentes(false)
      setPasso(2)
    } catch (err) {
      setError(mensagemDeErroApi(err))
    } finally {
      setBusy(false)
    }
  }

  function onPickFile(arquivo) {
    if (!arquivo) return
    setFile(arquivo)
    void interpretarArquivo(arquivo)
  }

  async function aplicarMapeamento() {
    if (!file) {
      setError(MSG.selecione_arquivo)
      return
    }
    await interpretarArquivo(file, mapeamento)
  }

  function updateCelula(linhaNum, campo, valor) {
    setLinhas((prev) =>
      prev.map((l) => {
        if (l.linha !== linhaNum) return l
        const next = { ...l, [campo]: valor }
        if (campo === 'tipo') {
          next.tipo = valor === 'evento' ? 'evento' : 'aula'
          next.tipo_label = next.tipo === 'evento' ? 'Evento' : 'Aula'
        }
        if (campo === 'data') {
          // Mantém data_iso se o usuário digitar dd/mm/aaaa
          const m = String(valor || '').match(/^(\d{2})\/(\d{2})\/(\d{4})$/)
          next.data_iso = m ? `${m[3]}-${m[2]}-${m[1]}` : l.data_iso || ''
        }
        return revalidarLinha(next)
      }),
    )
  }

  function onDragStartCol(key) {
    setDragCol(key)
  }

  function onDropCol(targetKey) {
    if (!dragCol || dragCol === targetKey) {
      setDragCol(null)
      return
    }
    setColOrder((prev) => {
      const next = prev.filter((k) => k !== dragCol)
      const idx = next.indexOf(targetKey)
      if (idx < 0) return prev
      next.splice(idx, 0, dragCol)
      return next
    })
    setDragCol(null)
  }

  async function handleConfirmar() {
    setBusy(true)
    setError('')
    try {
      const payload = linhas.map(revalidarLinha)
      const data = await confirmarImportacao({
        nome_arquivo: nomeArquivo || 'planilha de planejamento',
        linhas: payload,
      })
      setResultado(data)
      setPasso(3)
      await loadLotes()
    } catch (err) {
      setError(mensagemDeErroApi(err))
    } finally {
      setBusy(false)
    }
  }

  async function corrigirPendencias(loteId) {
    setBusy(true)
    setError('')
    try {
      const data = await detalheImportacao(loteId)
      const imp = data?.importacao
      const pend = Array.isArray(imp?.linhas_pendentes) ? imp.linhas_pendentes : []
      if (!pend.length) {
        setError('Não há pendências para corrigir neste envio.')
        setBusy(false)
        return
      }
      setNomeArquivo(imp?.nome_arquivo || `Envio ${loteId}`)
      setFile(null)
      setColunasArquivo([])
      setMapeamento({})
      setLinhas(pend.map(revalidarLinha))
      setFiltroPendentes(true)
      setResultado(null)
      setPasso(2)
      navigate('/importacoes', { replace: true })
    } catch (err) {
      setError(mensagemDeErroApi(err))
    } finally {
      setBusy(false)
    }
  }

  function reiniciar() {
    setPasso(1)
    setFile(null)
    setLinhas([])
    setResultado(null)
    setError('')
    setFiltroPendentes(false)
    setNomeArquivo('')
  }

  const labelCol = (key) =>
    COLUNAS_PADRAO.find((c) => c.key === key)?.label ||
    camposDestino.find((c) => c.key === key)?.label ||
    key

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-brand-200/80 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Link to="/mesa-do-inovador" aria-label="Voltar à Mesa">
            <BrandLogo
              variant="internal"
              className="h-16 w-auto max-w-[200px] object-contain"
            />
          </Link>
          <Link
            to="/mesa-do-inovador"
            className="btn-ghost min-h-11 !px-4 !py-2.5 text-sm"
          >
            ← Mesa
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pb-20 pt-6 sm:px-6">
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-brand-600">
          Planejamento · importação
        </p>
        <h1 className="font-display text-3xl font-bold text-bordo-deep">
          Importar aulas e eventos
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-bordo-soft">
          Traga sua planilha de planejamento, confira as linhas e confirme. Nada é gravado
          até você confirmar.
        </p>

        <ol className="mt-6 flex flex-wrap gap-2 text-xs font-semibold">
          {[
            { n: 1, t: 'Enviar arquivo' },
            { n: 2, t: 'Conferir e ajustar' },
            { n: 3, t: 'Confirmar' },
          ].map((s) => (
            <li
              key={s.n}
              className={`rounded-full px-3 py-1.5 ${
                passo === s.n
                  ? 'bg-bordo text-white'
                  : passo > s.n
                    ? 'bg-emerald-100 text-emerald-900'
                    : 'bg-brand-50 text-bordo-soft'
              }`}
            >
              {s.n}. {s.t}
            </li>
          ))}
        </ol>

        {error ? (
          <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
            {error}
          </p>
        ) : null}

        {passo === 1 ? (
          <section className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:items-start">
            <div
              className={`rounded-2xl border-2 border-dashed px-6 py-14 text-center transition ${
                dragOver
                  ? 'border-bordo bg-brand-50'
                  : 'border-brand-200 bg-brand-50/30'
              }`}
              onDragOver={(e) => {
                e.preventDefault()
                setDragOver(true)
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault()
                setDragOver(false)
                const f = e.dataTransfer.files?.[0]
                if (f) onPickFile(f)
              }}
            >
              <p className="font-display text-xl font-bold text-bordo-deep">
                Envie sua planilha de planejamento
              </p>
              <p className="mt-2 text-sm text-bordo-soft">
                Arraste o arquivo para cá ou selecione no computador. Aceita arquivos de
                planilha (Excel ou similar).
              </p>
              {file ? (
                <p className="mt-3 text-sm font-medium text-bordo">
                  Arquivo selecionado: {file.name}
                  {busy ? ' · lendo…' : ''}
                </p>
              ) : null}
              <label className="mt-6 inline-flex cursor-pointer">
                <span className="btn-primary min-h-11 !px-5 !py-3 text-sm">
                  {busy ? 'Lendo arquivo…' : file ? 'Trocar arquivo' : 'Escolher arquivo'}
                </span>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  className="sr-only"
                  disabled={busy}
                  onChange={(e) => onPickFile(e.target.files?.[0] || null)}
                />
              </label>
            </div>

            <ImportacaoPasso1Guia />
          </section>
        ) : null}

        {passo === 2 ? (
          <section className="mt-8 space-y-6">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="font-display text-xl font-bold text-bordo-deep">
                  Conferir e ajustar
                </h2>
                <p className="mt-1 text-sm text-bordo-soft">
                  {nomeArquivo ? `Arquivo: ${nomeArquivo}` : 'Linhas para revisão'}
                  {filtroPendentes ? ' · mostrando só pendências' : ''}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-ghost !px-3 !py-2 text-sm"
                  onClick={reiniciar}
                >
                  Enviar outro arquivo
                </button>
                {resumo.pendentes > 0 ? (
                  <button
                    type="button"
                    className="btn-ghost !px-3 !py-2 text-sm"
                    onClick={() => setFiltroPendentes((v) => !v)}
                  >
                    {filtroPendentes ? 'Ver todas as linhas' : 'Ver pendências'}
                  </button>
                ) : null}
              </div>
            </div>

            {colunasArquivo.length > 0 && file ? (
              <div className="rounded-2xl border border-brand-100 bg-white p-4">
                <h3 className="text-sm font-bold text-bordo-deep">
                  Associação de colunas
                </h3>
                <p className="mt-1 text-xs text-bordo-soft">
                  Se o nome da coluna no seu arquivo for diferente, diga o que cada uma
                  significa.
                </p>
                <ul className="mt-3 grid gap-2 sm:grid-cols-2">
                  {colunasArquivo.map((col) => (
                    <li key={col} className="flex flex-col gap-1 text-sm">
                      <span className="text-xs font-semibold text-bordo-soft">
                        Essa coluna do seu arquivo é:
                      </span>
                      <span className="truncate font-medium text-bordo">{col}</span>
                      <select
                        className="field-input min-h-10 py-1.5 text-sm"
                        value={mapeamento[col] ?? ''}
                        onChange={(e) =>
                          setMapeamento((prev) => ({ ...prev, [col]: e.target.value }))
                        }
                      >
                        {(camposDestino.length ? camposDestino : [
                          ...COLUNAS_PADRAO,
                          { key: '', label: '(não usar esta coluna)' },
                        ]).map((opt) => (
                          <option key={`${col}-${opt.key || 'none'}`} value={opt.key}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </li>
                  ))}
                </ul>
                <button
                  type="button"
                  className="btn-ghost mt-3 !px-4 !py-2 text-sm"
                  disabled={busy}
                  onClick={() => void aplicarMapeamento()}
                >
                  Aplicar associação
                </button>
              </div>
            ) : null}

            <p className="text-sm text-bordo">
              Serão criadas {resumo.aulas} aula{resumo.aulas === 1 ? '' : 's'} e{' '}
              {resumo.eventos} evento{resumo.eventos === 1 ? '' : 's'}.
              {resumo.pendentes > 0
                ? ` ${resumo.pendentes} linha${resumo.pendentes === 1 ? '' : 's'} está pendente até ser corrigida.`
                : ' Todas as linhas estão prontas.'}
            </p>

            <div className="overflow-x-auto rounded-xl border border-brand-100 bg-white">
              <table className="min-w-full text-left text-xs">
                <thead className="bg-brand-50 text-[11px] font-bold text-bordo-deep">
                  <tr>
                    <th className="px-2 py-2">#</th>
                    {colOrder.map((key) => (
                      <th
                        key={key}
                        draggable
                        onDragStart={() => onDragStartCol(key)}
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={() => onDropCol(key)}
                        className="cursor-grab px-2 py-2 select-none active:cursor-grabbing"
                        title="Arraste para reordenar"
                      >
                        {labelCol(key)}
                      </th>
                    ))}
                    <th className="px-2 py-2">Situação</th>
                  </tr>
                </thead>
                <tbody>
                  {linhasVisiveis.map((l) => {
                    const bad = linhaTemProblema(l)
                    return (
                      <tr
                        key={l.linha}
                        className={`border-t border-brand-50 ${
                          bad ? 'bg-amber-50/70' : ''
                        }`}
                      >
                        <td className="px-2 py-1.5 tabular-nums text-bordo-soft">
                          {l.linha}
                        </td>
                        {colOrder.map((key) => (
                          <td key={key} className="px-1 py-1">
                            {key === 'tipo' ? (
                              <select
                                className={`field-input min-h-9 py-1 text-xs ${
                                  bad && !l.titulo ? 'ring-1 ring-amber-400' : ''
                                }`}
                                value={l.tipo || 'aula'}
                                onChange={(e) =>
                                  updateCelula(l.linha, 'tipo', e.target.value)
                                }
                              >
                                <option value="aula">Aula</option>
                                <option value="evento">Evento</option>
                              </select>
                            ) : (
                              <input
                                className={`field-input min-h-9 min-w-[7rem] py-1 text-xs ${
                                  (key === 'titulo' && !l.titulo) ||
                                  (key === 'data' && !l.data)
                                    ? 'ring-1 ring-amber-400'
                                    : ''
                                }`}
                                value={
                                  key === 'data'
                                    ? l.data || ''
                                    : l[key] || ''
                                }
                                placeholder={
                                  key === 'data' ? 'dd/mm/aaaa' : undefined
                                }
                                onChange={(e) =>
                                  updateCelula(l.linha, key, e.target.value)
                                }
                              />
                            )}
                          </td>
                        ))}
                        <td className="max-w-[14rem] px-2 py-1.5 text-[11px] text-bordo-soft">
                          {l.status === 'pendente'
                            ? (l.mensagens || []).join(' ') || mensagemImportacao('pendente')
                            : l.status === 'aviso'
                              ? (l.mensagens || []).join(' ')
                              : 'Pronta'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-primary min-h-11 !px-5 !py-3 text-sm disabled:opacity-60"
                disabled={resumo.prontas === 0}
                onClick={() => {
                  setError('')
                  setResultado(null)
                  setPasso(3)
                }}
              >
                Ir para confirmação
              </button>
            </div>
          </section>
        ) : null}

        {passo === 3 && !resultado ? (
          <section className="mt-8 space-y-4">
            <h2 className="font-display text-xl font-bold text-bordo-deep">
              Confirmar importação
            </h2>
            <p className="text-sm text-bordo">
              Serão criadas {resumo.aulas} aula{resumo.aulas === 1 ? '' : 's'} e{' '}
              {resumo.eventos} evento{resumo.eventos === 1 ? '' : 's'}.
              {resumo.pendentes > 0
                ? ` ${resumo.pendentes} linha${resumo.pendentes === 1 ? '' : 's'} está pendente até ser corrigida.`
                : ''}
            </p>
            <p className="text-xs text-bordo-soft">
              Nada foi gravado ainda. Ao confirmar, as linhas prontas entram na sua agenda.
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-ghost !px-4 !py-2 text-sm"
                onClick={() => setPasso(2)}
              >
                Voltar e ajustar
              </button>
              <button
                type="button"
                className="btn-primary min-h-11 !px-5 !py-3 text-sm disabled:opacity-60"
                disabled={busy || resumo.prontas === 0}
                onClick={() => void handleConfirmar()}
              >
                {busy ? 'Confirmando…' : 'Confirmar importação'}
              </button>
            </div>
          </section>
        ) : null}

        {passo === 3 && resultado ? (
          <section className="mt-8 space-y-4">
            <h2 className="font-display text-xl font-bold text-bordo-deep">
              Importação concluída
            </h2>
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50/70 px-4 py-4">
              <p className="text-sm font-medium text-emerald-950">
                {resultado.mensagem || 'Importação concluída.'}
              </p>
              {(resultado.total_erro || 0) > 0 ? (
                <button
                  type="button"
                  className="btn-ghost mt-3 !px-3 !py-2 text-sm"
                  onClick={() => void corrigirPendencias(resultado.lote_id)}
                >
                  Corrigir pendências
                </button>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-2">
              <Link to="/mesa-do-inovador" className="btn-primary !px-4 !py-2 text-sm">
                Ver na agenda
              </Link>
              <button
                type="button"
                className="btn-ghost !px-4 !py-2 text-sm"
                onClick={reiniciar}
              >
                Importar outro arquivo
              </button>
            </div>
          </section>
        ) : null}

        <section className="mt-12">
          <h2 className="font-display text-lg font-bold text-bordo-deep">
            Envios anteriores
          </h2>
          {loadingList ? (
            <p className="mt-2 text-sm text-bordo-soft">Carregando…</p>
          ) : lotes.length === 0 ? (
            <p className="mt-2 text-sm text-bordo-soft">
              Você ainda não enviou nenhuma planilha.
            </p>
          ) : (
            <ul className="mt-4 grid gap-3 sm:grid-cols-2">
              {lotes.map((l) => {
                const pend = l.total_erro || 0
                const ok = l.total_sucesso || 0
                return (
                  <li
                    key={l.id}
                    className="rounded-2xl border border-brand-100 bg-white px-4 py-4 shadow-sm"
                  >
                    <p className="font-semibold text-bordo-deep">
                      {l.nome_arquivo || `Envio ${l.id}`}
                    </p>
                    <p className="mt-1 text-xs text-bordo-soft">
                      {formatWhen(l.created_at)}
                    </p>
                    <p className="mt-3 text-sm text-bordo">
                      {ok} aula{ok === 1 ? '' : 's'} ou evento{ok === 1 ? '' : 's'}{' '}
                      registrado{ok === 1 ? '' : 's'}
                      {pend > 0
                        ? ` · ${pend} pendência${pend === 1 ? '' : 's'}`
                        : ''}
                      {(l.total_aviso || 0) > 0
                        ? ` · ${l.total_aviso} aviso${l.total_aviso === 1 ? '' : 's'}`
                        : ''}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {pend > 0 ? (
                        <button
                          type="button"
                          className="btn-primary !px-3 !py-2 text-xs"
                          disabled={busy}
                          onClick={() => void corrigirPendencias(l.id)}
                        >
                          Corrigir pendências
                        </button>
                      ) : (
                        <span className="text-xs font-medium text-emerald-800">
                          Concluído
                        </span>
                      )}
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      </main>
    </div>
  )
}
