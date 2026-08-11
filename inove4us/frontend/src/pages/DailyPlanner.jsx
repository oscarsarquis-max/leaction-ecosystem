import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import BrandLogo from '../components/BrandLogo'
import ClassFeedbackModal from '../components/ClassFeedbackModal'
import DailyCycleKanban, {
  buildCycleTasks,
  cycleKanbanPayload,
} from '../components/DailyCycleKanban'
import FieldHelp from '../components/FieldHelp'
import UpgradeCreditsModal from '../components/UpgradeCreditsModal'
import VinculoPedagogicoSelector from '../components/VinculoPedagogicoSelector'
import { useAuth } from '../lib/auth'
import { canRegisterDailyAula } from '../lib/dailyAccess'
import { parseEmentaTopicos } from '../lib/ementaTopicos'
import {
  atualizarAula,
  buscarAula,
  encerrarAula,
  enviarFeedbackAula,
  iniciarAula,
  isSchemaPendingError,
  planejarAula,
  sugerirDinamicas,
} from '../services/dailyService'

/** Alinhado a daily_routes.py / migration 007 */
const LIMITS = {
  tema_aula: 255,
  turma_nome: 120,
  objetivo_aprendizagem: 20_000,
  acolhida: 20_000,
  conteudo_essencial: 20_000,
  dinamica_texto: 20_000,
  fechamento_checkout: 20_000,
}

const UNSAVED_MSG =
  'Você tem alterações não salvas neste planejamento. Deseja sair sem salvar?'

function hojeISO() {
  const d = new Date()
  const p = (n) => (n < 10 ? `0${n}` : String(n))
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function emptyForm() {
  return {
    tema_aula: '',
    data_planejada: hojeISO(),
    turma_nome: '',
    objetivo_aprendizagem: '',
    acolhida: '',
    conteudo_essencial: '',
    dinamica_ativa_id: '',
    dinamica_nome: '',
    dinamica_texto: '',
    dinamica_etiqueta: '',
    dinamica_contexto: '',
    dinamica_passos: [],
    escola_override_mensagem: '',
    escola_override_versao: null,
    fechamento_checkout: '',
    status: 'draft',
    disciplina_id: null,
    ementa_topico: '',
    ementa_texto: '',
  }
}

function snapshotForm(f) {
  return JSON.stringify({
    tema_aula: f.tema_aula || '',
    data_planejada: f.data_planejada || '',
    turma_nome: f.turma_nome || '',
    objetivo_aprendizagem: f.objetivo_aprendizagem || '',
    acolhida: f.acolhida || '',
    conteudo_essencial: f.conteudo_essencial || '',
    dinamica_ativa_id: f.dinamica_ativa_id || '',
    dinamica_nome: f.dinamica_nome || '',
    fechamento_checkout: f.fechamento_checkout || '',
    disciplina_id: f.disciplina_id ?? null,
    ementa_topico: f.ementa_topico || '',
  })
}

function snapshotBoard(tasks) {
  return JSON.stringify(
    (tasks || []).map((t) => ({
      id: t.id,
      coluna: t.coluna,
      ultima_observacao: t.ultima_observacao || '',
      historico: t.historico || [],
    })),
  )
}

function CharHint({ value, max }) {
  const len = String(value || '').length
  const near = len >= Math.floor(max * 0.9)
  const at = len >= max
  if (max >= 1000 && len < Math.floor(max * 0.8)) return null
  return (
    <span
      className={`mt-1 block text-right text-[11px] tabular-nums ${
        at ? 'font-semibold text-amber-800' : near ? 'text-amber-700' : 'text-bordo-soft'
      }`}
    >
      {len.toLocaleString('pt-BR')} / {max.toLocaleString('pt-BR')}
    </span>
  )
}

function normalizeBusca(texto) {
  return String(texto || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim()
}

function textoRoteiroDinamica(item) {
  if (!item || typeof item !== 'object') return ''
  const roteiro = String(item.roteiro_literal || '').trim()
  if (roteiro) return roteiro
  const passos = Array.isArray(item.passos) ? item.passos : []
  if (passos.length) {
    const linhas = [item.nome || 'Dinâmica', '', 'ROTEIRO DE EXECUÇÃO (siga na ordem)']
    passos.forEach((p, i) => {
      const n = p.ordem || i + 1
      const min = p.duracao_minutos ? ` (~${p.duracao_minutos} min)` : ''
      linhas.push('')
      linhas.push(`Passo ${n} · ${p.titulo || `Etapa ${n}`}${min}`)
      if (p.objetivo) linhas.push(`Objetivo: ${p.objetivo}`)
      if (p.como_executar) linhas.push(`Como executar: ${p.como_executar}`)
      if (p.dica_de_facilitacao) linhas.push(`Facilitação: ${p.dica_de_facilitacao}`)
    })
    return linhas.join('\n').trim()
  }
  const partes = [item.nome, item.motivo || '', item.descricao_curta || ''].filter(Boolean)
  return [...new Set(partes)].join('\n\n').trim()
}

function camposDinamicaDeItem(item) {
  if (!item) {
    return {
      dinamica_ativa_id: '',
      dinamica_nome: '',
      dinamica_texto: '',
      dinamica_etiqueta: '',
      dinamica_contexto: '',
      dinamica_passos: [],
      escola_override_mensagem: '',
      escola_override_versao: null,
    }
  }
  const ov = item.escola_override || null
  return {
    dinamica_ativa_id: item.id || '',
    dinamica_nome: item.nome || '',
    dinamica_texto: textoRoteiroDinamica(item).slice(0, LIMITS.dinamica_texto),
    dinamica_etiqueta: item.etiqueta || '',
    dinamica_contexto: item.contexto_execucao || 'sala',
    dinamica_passos: Array.isArray(item.passos) ? item.passos : [],
    escola_override_mensagem: ov?.mensagem || ov?.diretriz_customizada || '',
    escola_override_versao: ov?.versao ?? null,
  }
}

function DinamicaRoteiroPanel({
  nome,
  etiqueta,
  contexto,
  passos,
  onEscolher,
  onTrocar,
  onRemover,
}) {
  const temRoteiro = Boolean(nome) && Array.isArray(passos) && passos.length > 0
  const totalMin = (passos || []).reduce(
    (acc, p) => acc + (Number(p.duracao_minutos) || 0),
    0,
  )

  if (!nome) {
    return (
      <div className="mt-2 rounded-2xl border border-dashed border-brand-300 bg-gradient-to-br from-brand-50/80 to-white p-5">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
          Diretriz da dinâmica
        </p>
        <h3 className="mt-1 font-display text-lg font-bold text-bordo-deep">
          Nenhuma dinâmica selecionada
        </h3>
        <p className="mt-2 text-sm leading-relaxed text-bordo-soft">
          A execução vem do catálogo da escola — não é texto livre. Escolha uma dinâmica
          para ver o roteiro passo a passo.
        </p>
        <button
          type="button"
          onClick={onEscolher}
          className="btn-primary mt-4 min-h-11 !px-5 !py-2.5 text-sm font-bold"
        >
          Escolher dinâmica
        </button>
      </div>
    )
  }

  return (
    <div className="mt-2 overflow-hidden rounded-2xl border border-cyan-200/80 bg-gradient-to-b from-cyan-50/70 via-white to-brand-50/40 shadow-soft">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-cyan-100 bg-white/70 px-4 py-3 sm:px-5">
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-cyan-800">
            {etiqueta || 'Dinâmica'} · somente leitura
          </p>
          <h3 className="mt-0.5 font-display text-xl font-bold text-bordo-deep">{nome}</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {contexto ? (
              <span className="rounded-full bg-cyan-100 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-cyan-900">
                Contexto · {contexto}
              </span>
            ) : null}
            {temRoteiro ? (
              <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-900">
                {passos.length} passos
                {totalMin > 0 ? ` · ~${totalMin} min` : ''}
              </span>
            ) : null}
            <span className="rounded-full bg-amber-50 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-900">
              Diretriz protegida
            </span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onTrocar}
            className="btn-ghost min-h-10 !px-3 !py-2 text-xs font-semibold"
          >
            Trocar
          </button>
          <button
            type="button"
            onClick={onRemover}
            className="btn-ghost min-h-10 !px-3 !py-2 text-xs font-semibold text-rose-700"
          >
            Remover
          </button>
        </div>
      </div>

      {temRoteiro ? (
        <ol className="space-y-3 p-4 sm:p-5">
          {passos.map((p, i) => {
            const n = p.ordem || i + 1
            return (
              <li
                key={`${n}-${p.titulo || i}`}
                className="rounded-xl border border-white/80 bg-white/90 p-4 shadow-sm"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="font-display text-base font-bold text-bordo-deep">
                    <span className="mr-2 inline-flex h-7 w-7 items-center justify-center rounded-full bg-cyan-700 text-xs font-bold text-white">
                      {n}
                    </span>
                    {p.titulo || `Etapa ${n}`}
                  </p>
                  {p.duracao_minutos ? (
                    <span className="rounded-md bg-bordo-deep/5 px-2 py-0.5 text-[11px] font-bold tabular-nums text-bordo">
                      ~{p.duracao_minutos} min
                    </span>
                  ) : null}
                </div>
                {p.objetivo ? (
                  <p className="mt-2 text-sm leading-relaxed text-bordo">
                    <span className="font-bold text-bordo-deep">Objetivo. </span>
                    {p.objetivo}
                  </p>
                ) : null}
                {p.como_executar ? (
                  <p className="mt-2 text-sm leading-relaxed text-bordo-soft">
                    <span className="font-bold text-bordo-deep">Como executar. </span>
                    {p.como_executar}
                  </p>
                ) : null}
                {p.dica_de_facilitacao ? (
                  <p className="mt-3 rounded-lg border border-amber-100 bg-amber-50/80 px-3 py-2 text-[12px] leading-relaxed text-amber-950">
                    <span className="font-bold">Facilitação. </span>
                    {p.dica_de_facilitacao}
                  </p>
                ) : null}
              </li>
            )
          })}
        </ol>
      ) : (
        <p className="px-4 py-5 text-sm text-bordo-soft sm:px-5">
          Dinâmica selecionada, mas sem passos detalhados na base. Troque por outra do
          catálogo.
        </p>
      )}
    </div>
  )
}

/** Filtro local do catálogo — limpar o termo devolve a lista completa na hora. */
function filtrarDinamicas(items, termo) {
  const q = normalizeBusca(termo)
  if (!q) return items
  return items.filter((d) => {
    const blob = normalizeBusca(
      [d.id, d.nome, d.descricao_curta, d.etiqueta, d.roteiro_literal]
        .filter(Boolean)
        .join(' '),
    )
    return blob.includes(q)
  })
}

/**
 * Planejamento rápido de uma aula (~50 min) — criar ou editar.
 */
export default function DailyPlanner() {
  const { id } = useParams()
  const isNew = !id || id === 'nova'
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuth()
  const canRegister = canRegisterDailyAula(user)
  const [upgradeOpen, setUpgradeOpen] = useState(false)

  const [form, setForm] = useState(emptyForm)
  const [baseline, setBaseline] = useState(() => snapshotForm(emptyForm()))
  const [tasks, setTasks] = useState(() => buildCycleTasks(emptyForm(), null))
  const [boardBaseline, setBoardBaseline] = useState(() =>
    snapshotBoard(buildCycleTasks(emptyForm(), null)),
  )
  const [dirty, setDirty] = useState(false)
  const dirtyRef = useRef(false)
  const [loading, setLoading] = useState(!isNew)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [schemaPending, setSchemaPending] = useState(false)

  const [pickerOpen, setPickerOpen] = useState(false)
  const [pickerLoading, setPickerLoading] = useState(false)
  const [pickerTermo, setPickerTermo] = useState('')
  const [catalogoDinamicas, setCatalogoDinamicas] = useState([])
  const [pickerError, setPickerError] = useState('')
  const dinamicasVisiveis = filtrarDinamicas(catalogoDinamicas, pickerTermo)

  const [modoAulaBusy, setModoAulaBusy] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)
  const [feedbackBusy, setFeedbackBusy] = useState(false)
  const [feedbackAula, setFeedbackAula] = useState(null)

  const isInProgress = form.status === 'em_execucao' || form.status === 'in_progress'
  const isCompleted = form.status === 'realizado' || form.status === 'completed'
  const canStartAula = !isNew && !isInProgress && !isCompleted && Boolean(id)
  const ementaTopicos = useMemo(
    () => parseEmentaTopicos(form.ementa_texto),
    [form.ementa_texto],
  )

  const applyForm = useCallback((next, kanbanState = null) => {
    const nextTasks = buildCycleTasks(next, kanbanState)
    setForm(next)
    setTasks(nextTasks)
    setBaseline(snapshotForm(next))
    setBoardBaseline(snapshotBoard(nextTasks))
    dirtyRef.current = false
    setDirty(false)
  }, [])

  const setField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  // Mantém o resumo dos cards alinhado ao texto do formulário
  useEffect(() => {
    if (loading) return
    setTasks((prev) => buildCycleTasks(form, { tarefas: prev }))
  }, [
    form.acolhida,
    form.conteudo_essencial,
    form.dinamica_texto,
    form.dinamica_nome,
    form.dinamica_passos,
    form.fechamento_checkout,
    loading,
  ])

  useEffect(() => {
    if (loading) return
    const nextDirty =
      snapshotForm(form) !== baseline || snapshotBoard(tasks) !== boardBaseline
    dirtyRef.current = nextDirty
    setDirty(nextDirty)
  }, [form, baseline, tasks, boardBaseline, loading])

  useEffect(() => {
    const onBeforeUnload = (e) => {
      if (!dirtyRef.current) return
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [])

  useEffect(() => {
    if (loading) return
    if (location.hash !== '#kanban') return
    const t = window.setTimeout(() => {
      document.getElementById('ciclo-kanban')?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      })
    }, 120)
    return () => window.clearTimeout(t)
  }, [loading, location.hash, id])

  function confirmLeave() {
    if (!dirtyRef.current) return true
    return window.confirm(UNSAVED_MSG)
  }

  function handleLeaveClick(e) {
    if (!confirmLeave()) e.preventDefault()
  }

  function goTo(path) {
    if (!confirmLeave()) return
    dirtyRef.current = false
    setDirty(false)
    navigate(path)
  }

  const hydrateFromAula = useCallback(
    async (aula) => {
      let dinamicaCampos = camposDinamicaDeItem(null)
      const dinId = aula.dinamica_ativa_id || ''
      if (dinId) {
        try {
          const sug = await sugerirDinamicas('')
          const found = (sug?.dinamicas || []).find((d) => d.id === dinId)
          if (found) {
            dinamicaCampos = camposDinamicaDeItem(found)
          } else {
            dinamicaCampos = {
              ...camposDinamicaDeItem(null),
              dinamica_ativa_id: dinId,
              dinamica_nome: dinId,
              dinamica_texto: dinId,
            }
          }
        } catch {
          dinamicaCampos = {
            ...camposDinamicaDeItem(null),
            dinamica_ativa_id: dinId,
            dinamica_nome: dinId,
            dinamica_texto: dinId,
          }
        }
      }
      applyForm(
        {
          tema_aula: aula.tema_aula || '',
          data_planejada: String(aula.data_planejada || '').slice(0, 10) || hojeISO(),
          turma_nome: aula.turma_nome || '',
          objetivo_aprendizagem: aula.objetivo_aprendizagem || '',
          acolhida: aula.acolhida || '',
          conteudo_essencial: aula.conteudo_essencial || '',
          ...dinamicaCampos,
          fechamento_checkout: aula.fechamento_checkout || '',
          status: aula.status || 'draft',
          disciplina_id: aula.disciplina_id ?? null,
          ementa_topico: aula.ementa_topico || '',
          ementa_texto: '',
        },
        aula.kanban_state || null,
      )
    },
    [applyForm],
  )

  useEffect(() => {
    if (isNew) {
      applyForm(emptyForm())
      setLoading(false)
      return
    }
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError('')
      setSchemaPending(false)
      try {
        const data = await buscarAula(id)
        if (cancelled) return
        const aula = data?.aula || data
        await hydrateFromAula(aula)
      } catch (err) {
        if (cancelled) return
        if (isSchemaPendingError(err)) setSchemaPending(true)
        else setError(err?.message || 'Aula não encontrada.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id, isNew, hydrateFromAula, applyForm])

  async function openPicker() {
    setPickerOpen(true)
    setPickerTermo('')
    setPickerError('')
    setPickerLoading(true)
    try {
      const data = await sugerirDinamicas('', {
        tema: form.tema_aula.trim(),
        objetivo: form.objetivo_aprendizagem.trim(),
        conteudo: form.conteudo_essencial.trim(),
        limit: 12,
      })
      setCatalogoDinamicas(Array.isArray(data?.dinamicas) ? data.dinamicas : [])
    } catch (err) {
      if (isSchemaPendingError(err)) {
        setSchemaPending(true)
        setPickerOpen(false)
      } else {
        setPickerError(err?.message || 'Não foi possível carregar sugestões.')
        setCatalogoDinamicas([])
      }
    } finally {
      setPickerLoading(false)
    }
  }

  function closePicker() {
    setPickerOpen(false)
    setPickerTermo('')
  }

  function limparBuscaPicker() {
    setPickerTermo('')
  }

  function selectDinamica(item) {
    setForm((prev) => ({
      ...prev,
      ...camposDinamicaDeItem(item),
    }))
    closePicker()
  }

  function limparDinamica() {
    setForm((prev) => ({
      ...prev,
      ...camposDinamicaDeItem(null),
    }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (!form.tema_aula.trim()) {
      setError('Informe o tema da aula.')
      return
    }
    if (!form.data_planejada) {
      setError('Informe a data.')
      return
    }

    const payload = {
      tema_aula: form.tema_aula.trim().slice(0, LIMITS.tema_aula),
      data_planejada: form.data_planejada,
      turma_nome: form.turma_nome.trim().slice(0, LIMITS.turma_nome) || null,
      objetivo_aprendizagem: form.objetivo_aprendizagem.slice(0, LIMITS.objetivo_aprendizagem),
      acolhida: form.acolhida.slice(0, LIMITS.acolhida),
      conteudo_essencial: form.conteudo_essencial.slice(0, LIMITS.conteudo_essencial),
      dinamica_ativa_id: form.dinamica_ativa_id || null,
      fechamento_checkout: form.fechamento_checkout.slice(0, LIMITS.fechamento_checkout),
      kanban_state: cycleKanbanPayload(tasks),
      disciplina_id: form.disciplina_id ?? null,
      ementa_topico: form.ementa_topico.trim().slice(0, LIMITS.tema_aula) || null,
    }

    setSaving(true)
    try {
      if (isNew) {
        const created = await planejarAula(payload)
        const newId = created?.id || created?.aula?.id
        dirtyRef.current = false
        setDirty(false)
        if (newId) navigate(`/dia-a-dia/${newId}`, { replace: true })
        else navigate('/dia-a-dia')
      } else {
        await atualizarAula(id, {
          ...payload,
          status: form.status === 'draft' ? 'planejado' : form.status,
        })
        dirtyRef.current = false
        setDirty(false)
        navigate('/dia-a-dia')
      }
    } catch (err) {
      if (isSchemaPendingError(err)) setSchemaPending(true)
      else setError(err?.message || 'Não foi possível salvar.')
    } finally {
      setSaving(false)
    }
  }

  async function persistDraftIfNeeded() {
    if (isNew || !id) return
    if (!dirtyRef.current) return
    const payload = {
      tema_aula: form.tema_aula.trim().slice(0, LIMITS.tema_aula),
      data_planejada: form.data_planejada,
      turma_nome: form.turma_nome.trim().slice(0, LIMITS.turma_nome) || null,
      objetivo_aprendizagem: form.objetivo_aprendizagem.slice(0, LIMITS.objetivo_aprendizagem),
      acolhida: form.acolhida.slice(0, LIMITS.acolhida),
      conteudo_essencial: form.conteudo_essencial.slice(0, LIMITS.conteudo_essencial),
      dinamica_ativa_id: form.dinamica_ativa_id || null,
      fechamento_checkout: form.fechamento_checkout.slice(0, LIMITS.fechamento_checkout),
      kanban_state: cycleKanbanPayload(tasks),
      disciplina_id: form.disciplina_id ?? null,
      ementa_topico: form.ementa_topico.trim().slice(0, LIMITS.tema_aula) || null,
      status: form.status === 'draft' ? 'planejado' : form.status,
    }
    await atualizarAula(id, payload)
  }

  async function handleIniciarAula() {
    if (!canStartAula || modoAulaBusy) return
    setError('')
    setModoAulaBusy(true)
    try {
      await persistDraftIfNeeded()
      const data = await iniciarAula(id)
      const aula = data?.aula || data
      await hydrateFromAula(aula)
      dirtyRef.current = false
      setDirty(false)
    } catch (err) {
      if (isSchemaPendingError(err)) setSchemaPending(true)
      else setError(err?.message || 'Não foi possível iniciar a aula.')
    } finally {
      setModoAulaBusy(false)
    }
  }

  async function handleEncerrarAula() {
    if (!isInProgress || modoAulaBusy || !id) return
    setError('')
    setModoAulaBusy(true)
    try {
      const data = await encerrarAula(id)
      const aula = data?.aula || data
      await hydrateFromAula(aula)
      dirtyRef.current = false
      setDirty(false)
      setFeedbackAula({
        id: aula?.id || id,
        tema_aula: aula?.tema_aula || form.tema_aula,
        turma_nome: aula?.turma_nome || form.turma_nome,
        data_planejada: aula?.data_planejada || form.data_planejada,
      })
      setShowFeedback(true)
    } catch (err) {
      if (isSchemaPendingError(err)) setSchemaPending(true)
      else setError(err?.message || 'Não foi possível encerrar a aula.')
    } finally {
      setModoAulaBusy(false)
    }
  }

  async function handleSubmitFeedback(payload) {
    if (!feedbackAula?.id) return
    setFeedbackBusy(true)
    setError('')
    try {
      await enviarFeedbackAula(feedbackAula.id, payload)
      setShowFeedback(false)
      setFeedbackAula(null)
      navigate('/dia-a-dia')
    } catch (err) {
      setError(err?.message || 'Falha ao salvar o feedback da aula.')
    } finally {
      setFeedbackBusy(false)
    }
  }

  function closeFeedback() {
    if (feedbackBusy) return
    setShowFeedback(false)
    setFeedbackAula(null)
  }

  if (schemaPending) {
    return (
      <div className="min-h-screen">
        <header className="sticky top-0 z-40 border-b border-brand-200/80 bg-white/90 backdrop-blur-md">
          <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
            <Link to="/mesa-do-inovador" aria-label="Voltar">
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
        <main className="mx-auto max-w-3xl px-4 py-16 text-center sm:px-6">
          <h1 className="font-display text-2xl font-bold text-bordo-deep">Em breve</h1>
          <p className="mx-auto mt-3 max-w-lg text-sm leading-relaxed text-bordo-soft">
            O planejamento diário rápido estará disponível em breve! Estamos em fase final de
            atualização da plataforma.
          </p>
        </main>
      </div>
    )
  }

  if (isNew && !canRegister) {
    return (
      <div className="min-h-screen">
        <header className="sticky top-0 z-40 border-b border-brand-200/80 bg-white/90 backdrop-blur-md">
          <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
            <Link to="/mesa-do-inovador" aria-label="Voltar">
              <BrandLogo
                variant="internal"
                className="h-16 w-auto max-w-[200px] object-contain"
              />
            </Link>
            <Link to="/dia-a-dia" className="btn-ghost min-h-11 !px-4 !py-2.5 text-sm">
              ← Aulas
            </Link>
          </div>
        </header>
        <main className="mx-auto max-w-3xl px-4 py-16 text-center sm:px-6">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-brand-600">
            Dia a Dia
          </p>
          <h1 className="mt-2 font-display text-2xl font-bold text-bordo-deep">
            Registro disponível nos planos
          </h1>
          <p className="mx-auto mt-3 max-w-lg text-sm leading-relaxed text-bordo-soft">
            No gratuito você pode navegar pelo Dia a Dia. Para planejar e registrar aulas,
            escolha o Profissional, o Mentor ou um pacote avulso.
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
            <button
              type="button"
              onClick={() => setUpgradeOpen(true)}
              className="btn-primary min-h-11 !px-5 !py-3 text-sm"
            >
              Ver planos
            </button>
            <Link to="/dia-a-dia" className="btn-ghost min-h-11 !px-5 !py-3 text-sm">
              Voltar à listagem
            </Link>
          </div>
        </main>
        <UpgradeCreditsModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} />
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-brand-200/80 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Link
            to="/mesa-do-inovador"
            className="flex items-center gap-3"
            aria-label="Voltar à Mesa do Inovador"
            onClick={handleLeaveClick}
          >
            <BrandLogo
              variant="internal"
              className="h-16 w-auto max-w-[200px] object-contain sm:max-w-[240px]"
            />
          </Link>
          <div className="flex flex-wrap items-center gap-2">
            {dirty ? (
              <span className="hidden text-[11px] font-semibold text-amber-800 sm:inline">
                Não salvo
              </span>
            ) : null}
            <button
              type="button"
              onClick={() => goTo('/mesa-do-inovador')}
              className="btn-ghost min-h-11 !px-4 !py-2.5 text-sm font-semibold"
            >
              ← Mesa
            </button>
            <button
              type="button"
              onClick={() => goTo('/dia-a-dia')}
              className="btn-ghost min-h-11 !px-4 !py-2.5 text-sm"
            >
              ← Aulas
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pb-20 pt-6 sm:px-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-brand-600">
              Vetor Dia a Dia · atividade de uma aula
            </p>
            <h1 className="font-display text-3xl font-bold text-bordo-deep">
              {isInProgress
                ? 'Modo Aula'
                : isNew
                  ? 'Montar o ciclo do dia'
                  : 'Ajustar o ciclo do dia'}
            </h1>
            <p className="mt-2 max-w-3xl text-sm text-bordo-soft">
              {isInProgress
                ? 'Roteiro de voo dos 50 min. Pode fechar o notebook — a aula permanece em execução até você encerrar.'
                : 'Esquerda: planejar as 4 estações. Direita: mover na mesa (Para Fazer → Fazendo → Pronto). Cada migração exige observação — como no Desafio.'}
            </p>
            {form.tema_aula ? (
              <p className="mt-2 text-sm font-semibold text-bordo">
                {form.tema_aula}
                {form.turma_nome ? (
                  <span className="font-normal text-bordo-soft"> · {form.turma_nome}</span>
                ) : null}
              </p>
            ) : null}
          </div>

          {!isNew && !loading ? (
            <div className="flex flex-wrap items-center gap-2">
              {isInProgress ? (
                <button
                  type="button"
                  onClick={() => void handleEncerrarAula()}
                  disabled={modoAulaBusy}
                  className="btn-primary min-h-12 !bg-rose-700 !px-5 !py-3 text-sm font-bold shadow-soft hover:!bg-rose-800 disabled:opacity-60"
                >
                  {modoAulaBusy ? 'Encerrando…' : '⏹️ Encerrar Aula'}
                </button>
              ) : canStartAula ? (
                <button
                  type="button"
                  onClick={() => void handleIniciarAula()}
                  disabled={modoAulaBusy || !form.tema_aula.trim()}
                  className="btn-primary min-h-12 !px-5 !py-3 text-sm font-bold shadow-soft disabled:opacity-60"
                >
                  {modoAulaBusy ? 'Iniciando…' : '▶️ Iniciar Aula'}
                </button>
              ) : isCompleted ? (
                <span className="rounded-full bg-brand-50 px-3 py-2 text-xs font-bold text-bordo">
                  Aula encerrada
                </span>
              ) : null}
            </div>
          ) : null}
        </div>

        {error ? (
          <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
            {error}
          </p>
        ) : null}

        {loading ? (
          <p className="mt-10 text-sm text-bordo-soft">Carregando…</p>
        ) : isInProgress ? (
          <div className="mt-8" id="ciclo-kanban">
            <DailyCycleKanban
              tasks={tasks}
              onTasksChange={setTasks}
              enabled={false}
              focusMode
            />
          </div>
        ) : (
          <div className="mt-8 grid gap-6 lg:grid-cols-2 lg:items-start">
            <form onSubmit={handleSubmit} className="space-y-5">
            <VinculoPedagogicoSelector
              disciplinaId={form.disciplina_id}
              onChange={(id, meta) => {
                const sameDisc =
                  String(form.disciplina_id ?? '') === String(id ?? '')
                const tops = parseEmentaTopicos(meta?.ementa || '')
                setForm((prev) => {
                  const nextTopico = (() => {
                    if (!id) return ''
                    if (prev.ementa_topico && tops.includes(prev.ementa_topico)) {
                      return prev.ementa_topico
                    }
                    // Hidratação da mesma disciplina: mantém tópico salvo
                    if (sameDisc) return prev.ementa_topico || ''
                    return ''
                  })()
                  return {
                    ...prev,
                    disciplina_id: id,
                    ementa_texto: meta?.ementa || '',
                    ementa_topico: nextTopico,
                  }
                })
                if (!sameDisc) {
                  dirtyRef.current = true
                  setDirty(true)
                }
              }}
            />

            {ementaTopicos.length > 0 ? (
              <label className="block">
                <span className="field-label">Tópico da ementa</span>
                <select
                  className="field-input mt-1 min-h-11"
                  value={form.ementa_topico}
                  onChange={(e) => {
                    const topico = e.target.value
                    setForm((prev) => ({
                      ...prev,
                      ementa_topico: topico,
                      tema_aula: topico
                        ? topico.slice(0, LIMITS.tema_aula)
                        : prev.tema_aula,
                      conteudo_essencial:
                        topico && !String(prev.conteudo_essencial || '').trim()
                          ? `Ementa: ${topico}`
                          : prev.conteudo_essencial,
                    }))
                    setDirty(true)
                    dirtyRef.current = true
                  }}
                >
                  <option value="">Selecione um item da ementa…</option>
                  {ementaTopicos.map((t) => (
                    <option key={t} value={t}>
                      {t.length > 120 ? `${t.slice(0, 117)}…` : t}
                    </option>
                  ))}
                </select>
                <FieldHelp tip="Itens vêm da ementa da disciplina (uma linha = um tópico). Preenche o tema da aula.">
                  A ementa da disciplina alimenta o plano do dia a dia: escolha o tópico
                  desta aula.
                </FieldHelp>
              </label>
            ) : form.disciplina_id ? (
              <p className="rounded-xl border border-dashed border-brand-200 bg-brand-50/40 px-3 py-2 text-[12px] text-bordo-soft">
                Esta disciplina ainda não tem ementa com tópicos (uma linha por item).
                Cadastre em Instituições → disciplina → Ementa para selecionar aqui.
              </p>
            ) : null}

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <label className="block sm:col-span-2">
                <span className="field-label">Tema da aula</span>
                <input
                  className="field-input mt-1 min-h-11"
                  value={form.tema_aula}
                  onChange={(e) => setField('tema_aula', e.target.value.slice(0, LIMITS.tema_aula))}
                  placeholder="Ex.: Termodinâmica — ou escolha um tópico da ementa"
                  required
                  maxLength={LIMITS.tema_aula}
                />
                <FieldHelp tip="Pode vir da ementa ou ser digitado livremente. Seja específico.">
                  Pode vir da ementa ou ser digitado livremente. Seja específico.
                </FieldHelp>
                <CharHint value={form.tema_aula} max={LIMITS.tema_aula} />
              </label>
              <label className="block">
                <span className="field-label">Data na agenda</span>
                <input
                  type="date"
                  className="field-input mt-1 min-h-11"
                  value={form.data_planejada}
                  onChange={(e) => setField('data_planejada', e.target.value)}
                  required
                />
              </label>
              <label className="block">
                <span className="field-label">Turma (time)</span>
                <input
                  className="field-input mt-1 min-h-11"
                  value={form.turma_nome}
                  onChange={(e) =>
                    setField('turma_nome', e.target.value.slice(0, LIMITS.turma_nome))
                  }
                  placeholder="Ex.: 7º A"
                  maxLength={LIMITS.turma_nome}
                />
                <CharHint value={form.turma_nome} max={LIMITS.turma_nome} />
              </label>
            </div>

            <label className="block">
              <span className="field-label">Meta do ciclo (opcional)</span>
              <textarea
                className="field-input mt-1 min-h-[72px]"
                value={form.objetivo_aprendizagem}
                onChange={(e) =>
                  setField(
                    'objetivo_aprendizagem',
                    e.target.value.slice(0, LIMITS.objetivo_aprendizagem),
                  )
                }
                placeholder="O que o time precisa entregar ao final dos 50 min?"
                maxLength={LIMITS.objetivo_aprendizagem}
              />
              <CharHint value={form.objetivo_aprendizagem} max={LIMITS.objetivo_aprendizagem} />
            </label>

            <label className="block">
              <span className="field-label">1 · Acolhida</span>
              <textarea
                className="field-input mt-1 min-h-[88px]"
                value={form.acolhida}
                onChange={(e) =>
                  setField('acolhida', e.target.value.slice(0, LIMITS.acolhida))
                }
                placeholder="Stand-up curto: conectar o grupo e lembrar a meta do dia"
                maxLength={LIMITS.acolhida}
              />
              <FieldHelp tip="Como você vai fisgar a atenção nos primeiros 5 minutos?">
                Como você vai fisgar a atenção nos primeiros 5 minutos?
              </FieldHelp>
              <CharHint value={form.acolhida} max={LIMITS.acolhida} />
            </label>

            <label className="block">
              <span className="field-label">2 · Conteúdo</span>
              <textarea
                className="field-input mt-1 min-h-[100px]"
                value={form.conteudo_essencial}
                onChange={(e) =>
                  setField(
                    'conteudo_essencial',
                    e.target.value.slice(0, LIMITS.conteudo_essencial),
                  )
                }
                placeholder="O núcleo da aula — o que precisa ficar claro para o time"
                maxLength={LIMITS.conteudo_essencial}
              />
              <CharHint value={form.conteudo_essencial} max={LIMITS.conteudo_essencial} />
            </label>

            <div>
              <div className="flex flex-wrap items-end justify-between gap-2">
                <span className="field-label">3 · Dinâmica</span>
                {!form.dinamica_ativa_id ? (
                  <button
                    type="button"
                    onClick={() => void openPicker()}
                    className="btn-ghost min-h-11 !px-4 !py-2.5 text-sm font-semibold"
                  >
                    Escolher no catálogo
                  </button>
                ) : null}
              </div>
              <DinamicaRoteiroPanel
                nome={form.dinamica_nome}
                etiqueta={form.dinamica_etiqueta}
                contexto={form.dinamica_contexto}
                passos={form.dinamica_passos}
                onEscolher={() => void openPicker()}
                onTrocar={() => void openPicker()}
                onRemover={limparDinamica}
              />
              {form.escola_override_mensagem ? (
                <p className="mt-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs leading-relaxed text-amber-950">
                  <span className="font-semibold">Regra da escola: </span>
                  {form.escola_override_mensagem}
                </p>
              ) : null}
            </div>

            <label className="block">
              <span className="field-label">4 · Fechamento</span>
              <textarea
                className="field-input mt-1 min-h-[88px]"
                value={form.fechamento_checkout}
                onChange={(e) =>
                  setField(
                    'fechamento_checkout',
                    e.target.value.slice(0, LIMITS.fechamento_checkout),
                  )
                }
                placeholder="Checkout rápido: o que consolidar e o que levar para o próximo dia"
                maxLength={LIMITS.fechamento_checkout}
              />
              <CharHint value={form.fechamento_checkout} max={LIMITS.fechamento_checkout} />
            </label>

            <div className="flex flex-wrap gap-3 pt-2">
              <button
                type="submit"
                disabled={saving}
                className="btn-primary min-h-11 !px-5 !py-3 text-sm disabled:opacity-60"
              >
                {saving
                  ? 'Salvando…'
                  : isNew
                    ? 'Salvar e colocar na agenda'
                    : 'Atualizar ciclo e agenda'}
              </button>
              <button
                type="button"
                onClick={() => goTo('/dia-a-dia')}
                className="btn-ghost min-h-11 !px-4 !py-3 text-sm"
              >
                Cancelar
              </button>
            </div>
            </form>

            <div id="ciclo-kanban" className="scroll-mt-24">
              <DailyCycleKanban
                tasks={tasks}
                onTasksChange={setTasks}
                enabled={Boolean(form.tema_aula.trim() && form.data_planejada)}
              />
            </div>
          </div>
        )}
      </main>

      {pickerOpen ? (
        <div
          className="fixed inset-0 z-[90] flex items-end justify-center bg-bordo-deep/50 p-4 sm:items-center"
          role="dialog"
          aria-modal="true"
          aria-labelledby="dinamica-picker-title"
          onClick={(e) => {
            if (e.target === e.currentTarget) closePicker()
          }}
        >
          <div className="max-h-[88vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-brand-200 bg-white p-5 shadow-soft">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
              Kit do ciclo
            </p>
            <h2
              id="dinamica-picker-title"
              className="mt-1 font-display text-xl font-bold text-bordo-deep"
            >
              Dinâmicas rápidas
            </h2>
            <p className="mt-1 text-sm text-bordo-soft">
              {form.tema_aula.trim()
                ? `Sugestões para «${form.tema_aula.trim()}». Ao escolher, o roteiro entra como diretriz protegida (somente leitura).`
                : 'Escolha uma dinâmica do catálogo. O roteiro de execução é diretriz — não é texto livre.'}
            </p>

            <div className="mt-4 flex gap-2">
              <input
                className="field-input min-h-11 flex-1"
                value={pickerTermo}
                onChange={(e) => setPickerTermo(e.target.value)}
                placeholder="Filtrar por nome (ex.: Escape, Pitch, Estações…)"
                autoComplete="off"
                aria-label="Filtrar dinâmicas por nome"
              />
              {pickerTermo ? (
                <button
                  type="button"
                  onClick={limparBuscaPicker}
                  className="btn-ghost min-h-11 !px-4 !py-2 text-sm"
                  aria-label="Limpar busca"
                >
                  Limpar
                </button>
              ) : null}
            </div>
            {!pickerLoading && catalogoDinamicas.length > 0 ? (
              <p className="mt-2 text-xs text-bordo-soft">
                {pickerTermo.trim()
                  ? `${dinamicasVisiveis.length} de ${catalogoDinamicas.length}`
                  : `${catalogoDinamicas.length} dinâmicas`}
              </p>
            ) : null}

            {pickerLoading ? (
              <p className="mt-4 text-sm text-bordo-soft">Carregando…</p>
            ) : null}
            {pickerError ? (
              <p className="mt-4 text-sm text-amber-800">{pickerError}</p>
            ) : null}

            <ul className="mt-4 space-y-3">
              {dinamicasVisiveis.map((d) => (
                <li key={d.id}>
                  <button
                    type="button"
                    onClick={() => selectDinamica(d)}
                    className="w-full rounded-xl border border-brand-200 bg-brand-50/40 px-4 py-3.5 text-left transition hover:border-brand-400 hover:bg-brand-50"
                  >
                    <p className="text-[10px] font-bold uppercase tracking-wide text-brand-600">
                      {d.etiqueta || 'Indutivas'}
                    </p>
                    <p className="mt-0.5 font-display text-base font-bold text-bordo-deep">
                      {d.nome}
                    </p>
                    {d.tem_roteiro_completo ? (
                      <p className="mt-1 text-[11px] font-semibold text-emerald-800">
                        Roteiro completo · {Array.isArray(d.passos) ? d.passos.length : '—'}{' '}
                        passos
                        {d.contexto_execucao ? ` · ${d.contexto_execucao}` : ''}
                      </p>
                    ) : (
                      <p className="mt-1 text-[11px] font-semibold text-amber-800">
                        Sem mecânica detalhada na base — preencha a execução manualmente
                      </p>
                    )}
                    {d.motivo ? (
                      <p className="mt-1 text-sm leading-relaxed text-bordo-deep">
                        {d.motivo}
                      </p>
                    ) : null}
                    {d.descricao_curta && d.descricao_curta !== d.motivo ? (
                      <p className="mt-1 text-xs leading-relaxed text-bordo-soft">
                        {d.descricao_curta}
                      </p>
                    ) : null}
                    {d.escola_override?.mensagem ? (
                      <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50/90 px-2 py-1.5 text-xs leading-relaxed text-amber-950">
                        <span className="font-semibold">Regra da escola: </span>
                        {d.escola_override.mensagem}
                      </p>
                    ) : null}
                  </button>
                </li>
              ))}
            </ul>

            {!pickerLoading && dinamicasVisiveis.length === 0 && !pickerError ? (
              <p className="mt-4 text-sm text-bordo-soft">
                Nenhuma dinâmica encontrada.
                {pickerTermo.trim() ? (
                  <>
                    {' '}
                    <button
                      type="button"
                      onClick={limparBuscaPicker}
                      className="font-semibold text-brand-700 underline underline-offset-2"
                    >
                      Limpar busca
                    </button>
                  </>
                ) : null}
              </p>
            ) : null}

            <button
              type="button"
              onClick={closePicker}
              className="btn-ghost mt-5 min-h-11 w-full !py-3 text-sm"
            >
              Fechar
            </button>
          </div>
        </div>
      ) : null}

      {showFeedback && feedbackAula ? (
        <ClassFeedbackModal
          aula={feedbackAula}
          busy={feedbackBusy}
          onCancel={closeFeedback}
          onSkip={closeFeedback}
          onSubmit={handleSubmitFeedback}
        />
      ) : null}
    </div>
  )
}
