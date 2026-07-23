import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import BrandLogo from '../components/BrandLogo'
import DailyCycleKanban, {
  buildCycleTasks,
  cycleKanbanPayload,
} from '../components/DailyCycleKanban'
import {
  atualizarAula,
  buscarAula,
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
    fechamento_checkout: '',
    status: 'draft',
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
    dinamica_texto: f.dinamica_texto || '',
    fechamento_checkout: f.fechamento_checkout || '',
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

/** Filtro local do catálogo — limpar o termo devolve a lista completa na hora. */
function filtrarDinamicas(items, termo) {
  const q = normalizeBusca(termo)
  if (!q) return items
  return items.filter((d) => {
    const blob = normalizeBusca(
      [d.id, d.nome, d.descricao_curta, d.etiqueta].filter(Boolean).join(' '),
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
      let dinamicaTexto = ''
      let dinamicaNome = ''
      const dinId = aula.dinamica_ativa_id || ''
      if (dinId) {
        try {
          const sug = await sugerirDinamicas('')
          const found = (sug?.dinamicas || []).find((d) => d.id === dinId)
          if (found) {
            dinamicaNome = found.nome || ''
            dinamicaTexto = `${found.nome}\n\n${found.descricao_curta || ''}`.trim()
          } else {
            dinamicaTexto = dinId
          }
        } catch {
          dinamicaTexto = dinId
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
          dinamica_ativa_id: dinId,
          dinamica_nome: dinamicaNome,
          dinamica_texto: dinamicaTexto,
          fechamento_checkout: aula.fechamento_checkout || '',
          status: aula.status || 'draft',
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
      const data = await sugerirDinamicas('')
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
    const texto = `${item.nome}\n\n${item.descricao_curta || ''}`.trim().slice(0, LIMITS.dinamica_texto)
    setForm((prev) => ({
      ...prev,
      dinamica_ativa_id: item.id,
      dinamica_nome: item.nome || '',
      dinamica_texto: texto,
    }))
    closePicker()
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

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-brand-200/80 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Link
            to="/dia-a-dia"
            className="flex items-center gap-3"
            aria-label="Dia a Dia"
            onClick={handleLeaveClick}
          >
            <BrandLogo
              variant="internal"
              className="h-16 w-auto max-w-[200px] object-contain sm:max-w-[240px]"
            />
          </Link>
          <div className="flex items-center gap-2">
            {dirty ? (
              <span className="hidden text-[11px] font-semibold text-amber-800 sm:inline">
                Não salvo
              </span>
            ) : null}
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
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-brand-600">
          Vetor Dia a Dia · sprint de uma aula
        </p>
        <h1 className="font-display text-3xl font-bold text-bordo-deep">
          {isNew ? 'Montar o ciclo do dia' : 'Ajustar o ciclo do dia'}
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-bordo-soft">
          Esquerda: planejar as 4 estações. Direita: mover no Kanban (Para Fazer → Fazendo → Pronto).
          Cada migração exige observação — como no Desafio.
        </p>

        {loading ? (
          <p className="mt-10 text-sm text-bordo-soft">Carregando…</p>
        ) : (
          <div className="mt-8 grid gap-6 lg:grid-cols-2 lg:items-start">
            <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <label className="block sm:col-span-2">
                <span className="field-label">Tema da aula (backlog do dia)</span>
                <input
                  className="field-input mt-1 min-h-11"
                  value={form.tema_aula}
                  onChange={(e) => setField('tema_aula', e.target.value.slice(0, LIMITS.tema_aula))}
                  placeholder="Ex.: Frações equivalentes"
                  required
                  maxLength={LIMITS.tema_aula}
                />
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
              <span className="field-label">1 · Alinhamento (abertura)</span>
              <textarea
                className="field-input mt-1 min-h-[88px]"
                value={form.acolhida}
                onChange={(e) =>
                  setField('acolhida', e.target.value.slice(0, LIMITS.acolhida))
                }
                placeholder="Stand-up curto: conectar o grupo e lembrar a meta do dia"
                maxLength={LIMITS.acolhida}
              />
              <CharHint value={form.acolhida} max={LIMITS.acolhida} />
            </label>

            <label className="block">
              <span className="field-label">2 · Entrega do dia</span>
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
                <span className="field-label">3 · Atividade em campo</span>
                <button
                  type="button"
                  onClick={() => void openPicker()}
                  className="btn-ghost min-h-11 !px-4 !py-2.5 text-sm font-semibold"
                >
                  💡 Sugerir dinâmica rápida
                </button>
              </div>
              <textarea
                className="field-input mt-1 min-h-[100px]"
                value={form.dinamica_texto}
                onChange={(e) => {
                  const v = e.target.value.slice(0, LIMITS.dinamica_texto)
                  setField('dinamica_texto', v)
                  if (!v.trim()) {
                    setField('dinamica_ativa_id', '')
                    setField('dinamica_nome', '')
                  }
                }}
                placeholder="Como o time pratica a entrega (selecione uma sugestão ou descreva)"
                maxLength={LIMITS.dinamica_texto}
              />
              <CharHint value={form.dinamica_texto} max={LIMITS.dinamica_texto} />
              {form.dinamica_ativa_id ? (
                <p className="mt-1 text-[11px] text-bordo-soft">
                  Dinâmica no board:{' '}
                  <span className="font-semibold text-bordo">
                    {form.dinamica_nome || 'selecionada'}
                  </span>
                </p>
              ) : null}
            </div>

            <label className="block">
              <span className="field-label">4 · Retro do ciclo</span>
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

            {error ? (
              <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
                {error}
              </p>
            ) : null}

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
              Catálogo completo de dinâmicas (por nome). Digite para filtrar; limpe para ver tudo de novo.
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
                    <p className="mt-1 text-sm leading-relaxed text-bordo-soft">
                      {d.descricao_curta}
                    </p>
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
    </div>
  )
}
