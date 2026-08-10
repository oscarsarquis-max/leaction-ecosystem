import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import BrandLogo from '../components/BrandLogo'
import CursosDisciplinasPanel from '../components/CursosDisciplinasPanel'
import { useAuth } from '../lib/auth'
import {
  atualizarInstituicao,
  atualizarPeriodo,
  criarInstituicao,
  criarPeriodo,
  desativarInstituicao,
  desativarPeriodo,
  isSchemaPendingError,
  listarInstituicoes,
  listarPeriodos,
  marcarPeriodoEmCurso,
} from '../services/instituicoesService'

const TIPOS_INST = [
  { value: 'escola', label: 'Escola' },
  { value: 'faculdade_universidade', label: 'Faculdade / Universidade' },
  { value: 'curso_tecnico', label: 'Curso técnico' },
  { value: 'curso_livre', label: 'Curso livre' },
  { value: 'corporativo', label: 'Corporativo' },
  { value: 'outro', label: 'Outro' },
]

const TIPOS_PERIODO = [
  { value: 'anual', label: 'Anual' },
  { value: 'semestral', label: 'Semestral' },
  { value: 'trimestral', label: 'Trimestral' },
  { value: 'modular', label: 'Modular' },
]

const STATUS_PERIODO = [
  { value: 'planejamento', label: 'Planejamento' },
  { value: 'em_andamento', label: 'Em andamento' },
  { value: 'encerrado', label: 'Encerrado' },
]

const emptyInst = {
  nome: '',
  tipo_instituicao: 'escola',
  segmento: '',
  rede: 'nao_informado',
  cidade: '',
  uf: '',
  pais: 'BR',
  observacoes: '',
}

function emptyPeriodo() {
  const year = new Date().getFullYear()
  return {
    rotulo: `Ano Letivo ${year}`,
    ano_letivo: year,
    tipo_periodo: 'anual',
    etapa: '',
    data_inicio: `${year}-02-01`,
    data_fim: `${year}-12-15`,
    carga_horaria_total_horas: '',
    duracao_padrao_aula_min: 50,
    status: 'planejamento',
    em_curso: false,
  }
}

function tipoLabel(value) {
  return TIPOS_INST.find((t) => t.value === value)?.label || value
}

function statusTone(status) {
  if (status === 'em_andamento') return 'bg-emerald-50 text-emerald-800'
  if (status === 'encerrado') return 'bg-stone-100 text-stone-600'
  return 'bg-amber-50 text-amber-900'
}

export default function InstituicoesPage() {
  const { user, logout } = useAuth()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [schemaPending, setSchemaPending] = useState(false)
  const [form, setForm] = useState(emptyInst)
  const [editingId, setEditingId] = useState(null)
  const [busy, setBusy] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [periodos, setPeriodos] = useState([])
  const [periodoForm, setPeriodoForm] = useState(emptyPeriodo())
  const [editingPeriodoId, setEditingPeriodoId] = useState(null)
  const [periodosLoading, setPeriodosLoading] = useState(false)
  const [selectedPeriodoId, setSelectedPeriodoId] = useState(null)

  const markSchemaPending = useCallback(() => setSchemaPending(true), [])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    setSchemaPending(false)
    try {
      const data = await listarInstituicoes()
      setItems(Array.isArray(data?.instituicoes) ? data.instituicoes : [])
    } catch (err) {
      if (isSchemaPendingError(err)) {
        setSchemaPending(true)
        setItems([])
      } else {
        setError(err?.message || 'Não foi possível carregar as instituições.')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  const loadPeriodos = useCallback(async (instituicaoId) => {
    if (!instituicaoId) {
      setPeriodos([])
      return
    }
    setPeriodosLoading(true)
    try {
      const data = await listarPeriodos(instituicaoId)
      setPeriodos(Array.isArray(data?.periodos) ? data.periodos : [])
    } catch (err) {
      if (isSchemaPendingError(err)) setSchemaPending(true)
      else window.alert(err?.message || 'Falha ao carregar períodos')
      setPeriodos([])
    } finally {
      setPeriodosLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    setSelectedPeriodoId(null)
    void loadPeriodos(selectedId)
  }, [selectedId, loadPeriodos])

  function startEdit(inst) {
    setEditingId(inst.id)
    setForm({
      nome: inst.nome || '',
      tipo_instituicao: inst.tipo_instituicao || 'escola',
      segmento: inst.segmento || '',
      rede: inst.rede || 'nao_informado',
      cidade: inst.cidade || '',
      uf: inst.uf || '',
      pais: inst.pais || 'BR',
      observacoes: inst.observacoes || '',
    })
    setSelectedId(inst.id)
  }

  function resetForm() {
    setEditingId(null)
    setForm(emptyInst)
  }

  async function handleSaveInst(e) {
    e.preventDefault()
    setBusy(true)
    try {
      if (editingId) {
        await atualizarInstituicao(editingId, form)
      } else {
        const created = await criarInstituicao(form)
        const id = created?.instituicao?.id
        if (id) setSelectedId(id)
      }
      resetForm()
      await load()
    } catch (err) {
      if (isSchemaPendingError(err)) setSchemaPending(true)
      else window.alert(err?.message || 'Falha ao salvar instituição')
    } finally {
      setBusy(false)
    }
  }

  async function handleDeleteInst(inst) {
    if (!window.confirm(`Desativar “${inst.nome}”? Os períodos associados serão desativados.`)) {
      return
    }
    setBusy(true)
    try {
      await desativarInstituicao(inst.id)
      if (selectedId === inst.id) setSelectedId(null)
      if (editingId === inst.id) resetForm()
      await load()
    } catch (err) {
      window.alert(err?.message || 'Falha ao desativar')
    } finally {
      setBusy(false)
    }
  }

  function startEditPeriodo(p) {
    setEditingPeriodoId(p.id)
    setPeriodoForm({
      rotulo: p.rotulo || '',
      ano_letivo: p.ano_letivo,
      tipo_periodo: p.tipo_periodo || 'anual',
      etapa: p.etapa || '',
      data_inicio: String(p.data_inicio || '').slice(0, 10),
      data_fim: String(p.data_fim || '').slice(0, 10),
      carga_horaria_total_horas: p.carga_horaria_total_horas ?? '',
      duracao_padrao_aula_min: p.duracao_padrao_aula_min ?? 50,
      status: p.status || 'planejamento',
      em_curso: Boolean(p.em_curso),
    })
  }

  function resetPeriodoForm() {
    setEditingPeriodoId(null)
    setPeriodoForm(emptyPeriodo())
  }

  async function handleSavePeriodo(e) {
    e.preventDefault()
    if (!selectedId) return
    setBusy(true)
    const payload = {
      ...periodoForm,
      ano_letivo: Number(periodoForm.ano_letivo),
      duracao_padrao_aula_min: Number(periodoForm.duracao_padrao_aula_min) || 50,
      carga_horaria_total_horas:
        periodoForm.carga_horaria_total_horas === ''
          ? null
          : Number(periodoForm.carga_horaria_total_horas),
    }
    try {
      if (editingPeriodoId) {
        await atualizarPeriodo(editingPeriodoId, payload)
      } else {
        await criarPeriodo(selectedId, payload)
      }
      resetPeriodoForm()
      await loadPeriodos(selectedId)
      await load()
    } catch (err) {
      window.alert(err?.message || 'Falha ao salvar período')
    } finally {
      setBusy(false)
    }
  }

  async function handleMarcarEmCurso(periodoId) {
    setBusy(true)
    try {
      await marcarPeriodoEmCurso(periodoId)
      await loadPeriodos(selectedId)
      await load()
    } catch (err) {
      window.alert(err?.message || 'Falha ao marcar em curso')
    } finally {
      setBusy(false)
    }
  }

  async function handleDeletePeriodo(p) {
    if (!window.confirm(`Desativar o período “${p.rotulo}”?`)) return
    setBusy(true)
    try {
      await desativarPeriodo(p.id)
      if (editingPeriodoId === p.id) resetPeriodoForm()
      if (selectedPeriodoId === p.id) setSelectedPeriodoId(null)
      await loadPeriodos(selectedId)
      await load()
    } catch (err) {
      window.alert(err?.message || 'Falha ao desativar período')
    } finally {
      setBusy(false)
    }
  }

  const selected = items.find((i) => i.id === selectedId) || null
  const selectedPeriodo = periodos.find((p) => p.id === selectedPeriodoId) || null

  return (
    <div className="min-h-screen bg-[#faf7f2]">
      <header className="sticky top-0 z-40 border-b border-brand-200/80 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Link to="/mesa-do-inovador" className="flex items-center gap-3" aria-label="inove4us — início">
            <BrandLogo
              variant="internal"
              className="h-20 w-auto max-w-[240px] object-contain sm:max-w-[280px]"
            />
          </Link>
          <div className="flex flex-wrap items-center gap-2">
            <span className="hidden text-sm text-bordo-soft sm:inline">
              {user?.nome_clie || 'professor'}
            </span>
            <Link to="/mesa-do-inovador" className="btn-ghost !px-3 !py-1.5 text-xs">
              Mesa
            </Link>
            <button type="button" onClick={logout} className="btn-ghost !px-3 !py-1.5 text-xs">
              Sair
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-brand-600">
          Configurações
        </p>
        <h1 className="font-display text-3xl font-bold text-bordo-deep">
          Instituições, períodos, cursos e disciplinas
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-bordo-soft">
          Cadastro opcional da estruturação pedagógica (versão ampliada). Continua sendo possível
          criar aulas avulsas sem vincular instituição, período, curso ou disciplina.
        </p>

        {schemaPending ? (
          <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
            Schema pendente — aplique as migrations{' '}
            <code className="font-mono text-xs">008</code> e{' '}
            <code className="font-mono text-xs">009_inove_cursos_disciplinas.sql</code>.
          </div>
        ) : null}
        {error ? (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            {error}
          </div>
        ) : null}

        <div className="mt-8 grid gap-8 lg:grid-cols-2">
          {/* Coluna instituições */}
          <section className="space-y-4">
            <form
              onSubmit={handleSaveInst}
              className="rounded-2xl border border-brand-100 bg-white p-4 shadow-sm sm:p-5"
            >
              <h2 className="text-sm font-bold text-bordo">
                {editingId ? 'Editar instituição' : 'Nova instituição'}
              </h2>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <label className="sm:col-span-2 block text-xs font-semibold text-bordo-soft">
                  Nome *
                  <input
                    required
                    className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                    value={form.nome}
                    onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
                  />
                </label>
                <label className="block text-xs font-semibold text-bordo-soft">
                  Tipo *
                  <select
                    className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                    value={form.tipo_instituicao}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, tipo_instituicao: e.target.value }))
                    }
                  >
                    {TIPOS_INST.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-xs font-semibold text-bordo-soft">
                  Rede
                  <select
                    className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                    value={form.rede}
                    onChange={(e) => setForm((f) => ({ ...f, rede: e.target.value }))}
                  >
                    <option value="nao_informado">Não informado</option>
                    <option value="publica">Pública</option>
                    <option value="privada">Privada</option>
                  </select>
                </label>
                <label className="block text-xs font-semibold text-bordo-soft">
                  Segmento
                  <input
                    className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                    placeholder="ex.: ensino médio, superior…"
                    value={form.segmento}
                    onChange={(e) => setForm((f) => ({ ...f, segmento: e.target.value }))}
                  />
                </label>
                <label className="block text-xs font-semibold text-bordo-soft">
                  Cidade
                  <input
                    className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                    value={form.cidade}
                    onChange={(e) => setForm((f) => ({ ...f, cidade: e.target.value }))}
                  />
                </label>
                <label className="block text-xs font-semibold text-bordo-soft">
                  UF
                  <input
                    className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm uppercase"
                    maxLength={8}
                    value={form.uf}
                    onChange={(e) => setForm((f) => ({ ...f, uf: e.target.value }))}
                  />
                </label>
                <label className="sm:col-span-2 block text-xs font-semibold text-bordo-soft">
                  Observações
                  <textarea
                    rows={2}
                    className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                    value={form.observacoes}
                    onChange={(e) => setForm((f) => ({ ...f, observacoes: e.target.value }))}
                  />
                </label>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <button type="submit" disabled={busy || schemaPending} className="btn-primary !px-4 !py-2 text-sm">
                  {editingId ? 'Salvar' : 'Cadastrar'}
                </button>
                {editingId ? (
                  <button type="button" onClick={resetForm} className="btn-ghost !px-4 !py-2 text-sm">
                    Cancelar
                  </button>
                ) : null}
              </div>
            </form>

            <div className="rounded-2xl border border-brand-100 bg-white p-4 shadow-sm sm:p-5">
              <h2 className="text-sm font-bold text-bordo">Suas instituições</h2>
              {loading ? (
                <p className="mt-3 text-sm text-bordo-soft">Carregando…</p>
              ) : items.length === 0 ? (
                <p className="mt-3 text-sm text-bordo-soft">Nenhuma instituição cadastrada ainda.</p>
              ) : (
                <ul className="mt-3 divide-y divide-brand-100">
                  {items.map((inst) => (
                    <li key={inst.id} className="flex flex-wrap items-start justify-between gap-2 py-3">
                      <button
                        type="button"
                        onClick={() => setSelectedId(inst.id)}
                        className={`min-w-0 flex-1 text-left ${
                          selectedId === inst.id ? 'text-bordo' : 'text-bordo-soft'
                        }`}
                      >
                        <p className="font-semibold text-bordo-deep">{inst.nome}</p>
                        <p className="text-xs">
                          {tipoLabel(inst.tipo_instituicao)}
                          {inst.cidade ? ` · ${inst.cidade}` : ''}
                          {inst.uf ? `/${inst.uf}` : ''}
                          {inst.periodo_em_curso_id
                            ? ' · período em curso'
                            : ` · ${inst.periodos_count || 0} período(s)`}
                        </p>
                      </button>
                      <div className="flex gap-1">
                        <button
                          type="button"
                          className="btn-ghost !px-2 !py-1 text-xs"
                          onClick={() => startEdit(inst)}
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          className="btn-ghost !px-2 !py-1 text-xs text-red-700"
                          onClick={() => handleDeleteInst(inst)}
                          disabled={busy}
                        >
                          Desativar
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          {/* Coluna períodos */}
          <section className="space-y-4">
            {!selected ? (
              <div className="rounded-2xl border border-dashed border-brand-200 bg-white/60 px-5 py-10 text-center text-sm text-bordo-soft">
                Selecione uma instituição para gerenciar períodos letivos.
              </div>
            ) : (
              <>
                <div className="rounded-2xl border border-brand-100 bg-white p-4 shadow-sm sm:p-5">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-brand-600">
                    Períodos letivos
                  </p>
                  <h2 className="font-display text-xl font-bold text-bordo-deep">{selected.nome}</h2>

                  <form onSubmit={handleSavePeriodo} className="mt-4 grid gap-3 sm:grid-cols-2">
                    <label className="sm:col-span-2 block text-xs font-semibold text-bordo-soft">
                      Rótulo *
                      <input
                        required
                        className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                        value={periodoForm.rotulo}
                        onChange={(e) =>
                          setPeriodoForm((f) => ({ ...f, rotulo: e.target.value }))
                        }
                      />
                    </label>
                    <label className="block text-xs font-semibold text-bordo-soft">
                      Ano letivo *
                      <input
                        type="number"
                        required
                        min={1990}
                        max={2100}
                        className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                        value={periodoForm.ano_letivo}
                        onChange={(e) =>
                          setPeriodoForm((f) => ({ ...f, ano_letivo: e.target.value }))
                        }
                      />
                    </label>
                    <label className="block text-xs font-semibold text-bordo-soft">
                      Tipo *
                      <select
                        className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                        value={periodoForm.tipo_periodo}
                        onChange={(e) =>
                          setPeriodoForm((f) => ({ ...f, tipo_periodo: e.target.value }))
                        }
                      >
                        {TIPOS_PERIODO.map((t) => (
                          <option key={t.value} value={t.value}>
                            {t.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    {periodoForm.tipo_periodo !== 'anual' ? (
                      <label className="sm:col-span-2 block text-xs font-semibold text-bordo-soft">
                        Etapa
                        <input
                          className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                          placeholder="ex.: 1º semestre"
                          value={periodoForm.etapa}
                          onChange={(e) =>
                            setPeriodoForm((f) => ({ ...f, etapa: e.target.value }))
                          }
                        />
                      </label>
                    ) : null}
                    <label className="block text-xs font-semibold text-bordo-soft">
                      Início *
                      <input
                        type="date"
                        required
                        className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                        value={periodoForm.data_inicio}
                        onChange={(e) =>
                          setPeriodoForm((f) => ({ ...f, data_inicio: e.target.value }))
                        }
                      />
                    </label>
                    <label className="block text-xs font-semibold text-bordo-soft">
                      Fim *
                      <input
                        type="date"
                        required
                        className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                        value={periodoForm.data_fim}
                        onChange={(e) =>
                          setPeriodoForm((f) => ({ ...f, data_fim: e.target.value }))
                        }
                      />
                    </label>
                    <label className="block text-xs font-semibold text-bordo-soft">
                      Duração padrão da aula (min)
                      <input
                        type="number"
                        min={5}
                        max={480}
                        className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                        value={periodoForm.duracao_padrao_aula_min}
                        onChange={(e) =>
                          setPeriodoForm((f) => ({
                            ...f,
                            duracao_padrao_aula_min: e.target.value,
                          }))
                        }
                      />
                    </label>
                    <label className="block text-xs font-semibold text-bordo-soft">
                      Status
                      <select
                        className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                        value={periodoForm.status}
                        onChange={(e) =>
                          setPeriodoForm((f) => ({ ...f, status: e.target.value }))
                        }
                      >
                        {STATUS_PERIODO.map((s) => (
                          <option key={s.value} value={s.value}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="sm:col-span-2 flex items-center gap-2 text-xs font-semibold text-bordo">
                      <input
                        type="checkbox"
                        checked={Boolean(periodoForm.em_curso)}
                        onChange={(e) =>
                          setPeriodoForm((f) => ({ ...f, em_curso: e.target.checked }))
                        }
                      />
                      Marcar como período em curso desta instituição
                    </label>
                    <div className="sm:col-span-2 flex flex-wrap gap-2">
                      <button
                        type="submit"
                        disabled={busy}
                        className="btn-primary !px-4 !py-2 text-sm"
                      >
                        {editingPeriodoId ? 'Salvar período' : 'Adicionar período'}
                      </button>
                      {editingPeriodoId ? (
                        <button
                          type="button"
                          onClick={resetPeriodoForm}
                          className="btn-ghost !px-4 !py-2 text-sm"
                        >
                          Cancelar
                        </button>
                      ) : null}
                    </div>
                  </form>
                </div>

                <div className="rounded-2xl border border-brand-100 bg-white p-4 shadow-sm sm:p-5">
                  <h3 className="text-sm font-bold text-bordo">Períodos cadastrados</h3>
                  {periodosLoading ? (
                    <p className="mt-3 text-sm text-bordo-soft">Carregando…</p>
                  ) : periodos.length === 0 ? (
                    <p className="mt-3 text-sm text-bordo-soft">Nenhum período ainda.</p>
                  ) : (
                    <ul className="mt-3 space-y-3">
                      {periodos.map((p) => (
                        <li
                          key={p.id}
                          className="rounded-xl border border-brand-100 px-3 py-3"
                        >
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div>
                              <p className="font-semibold text-bordo-deep">
                                {p.rotulo}
                                {p.em_curso ? (
                                  <span className="ml-2 rounded-full bg-bordo px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
                                    Em curso
                                  </span>
                                ) : null}
                              </p>
                              <p className="mt-1 text-xs text-bordo-soft">
                                {p.ano_letivo} · {p.tipo_periodo}
                                {p.etapa ? ` · ${p.etapa}` : ''} ·{' '}
                                {String(p.data_inicio).slice(0, 10)} →{' '}
                                {String(p.data_fim).slice(0, 10)}
                              </p>
                              <span
                                className={`mt-2 inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusTone(
                                  p.status
                                )}`}
                              >
                                {STATUS_PERIODO.find((s) => s.value === p.status)?.label ||
                                  p.status}
                              </span>
                            </div>
                            <div className="flex flex-wrap gap-1">
                              <button
                                type="button"
                                className={`btn-ghost !px-2 !py-1 text-xs ${
                                  selectedPeriodoId === p.id ? 'font-bold text-bordo' : ''
                                }`}
                                onClick={() =>
                                  setSelectedPeriodoId((cur) => (cur === p.id ? null : p.id))
                                }
                              >
                                {selectedPeriodoId === p.id ? 'Ocultar cursos' : 'Cursos'}
                              </button>
                              {!p.em_curso ? (
                                <button
                                  type="button"
                                  className="btn-ghost !px-2 !py-1 text-xs"
                                  disabled={busy}
                                  onClick={() => handleMarcarEmCurso(p.id)}
                                >
                                  Marcar em curso
                                </button>
                              ) : null}
                              <button
                                type="button"
                                className="btn-ghost !px-2 !py-1 text-xs"
                                onClick={() => startEditPeriodo(p)}
                              >
                                Editar
                              </button>
                              <button
                                type="button"
                                className="btn-ghost !px-2 !py-1 text-xs text-red-700"
                                disabled={busy}
                                onClick={() => handleDeletePeriodo(p)}
                              >
                                Desativar
                              </button>
                            </div>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {selectedPeriodo ? (
                  <CursosDisciplinasPanel
                    periodo={selectedPeriodo}
                    onSchemaPending={markSchemaPending}
                  />
                ) : null}
              </>
            )}
          </section>
        </div>
      </main>
    </div>
  )
}
