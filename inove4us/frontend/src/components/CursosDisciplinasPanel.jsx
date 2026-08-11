import { useCallback, useEffect, useRef, useState } from 'react'
import {
  atualizarCurso,
  atualizarDisciplina,
  atualizarTurma,
  criarCurso,
  criarDisciplina,
  criarTurma,
  desativarCurso,
  desativarDisciplina,
  desativarTurma,
  isSchemaPendingError,
  listarCursos,
  listarDisciplinas,
  listarTurmas,
} from '../services/instituicoesService'

const NIVEIS = [
  { value: '', label: '—' },
  { value: 'fundamental', label: 'Fundamental' },
  { value: 'medio', label: 'Médio' },
  { value: 'tecnico', label: 'Técnico' },
  { value: 'superior', label: 'Superior' },
  { value: 'livre', label: 'Livre' },
  { value: 'corporativo', label: 'Corporativo' },
  { value: 'idiomas', label: 'Idiomas' },
  { value: 'outro', label: 'Outro' },
]

const emptyCurso = {
  nome: '',
  nivel: '',
  carga_horaria_total_horas: '',
  observacoes: '',
}

const emptyDisc = {
  nome: '',
  codigo: '',
  carga_horaria_horas: '',
  ementa: '',
}

const emptyTurma = {
  nome: '',
  turno: '',
}

/**
 * Drill-down: período → cursos → turmas (1:N) + disciplinas.
 */
export default function CursosDisciplinasPanel({ periodo, onSchemaPending, readOnly = false }) {
  const [cursos, setCursos] = useState([])
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [cursoForm, setCursoForm] = useState(emptyCurso)
  const [editingCursoId, setEditingCursoId] = useState(null)
  const [selectedCursoId, setSelectedCursoId] = useState(null)
  const [disciplinas, setDisciplinas] = useState([])
  const [discLoading, setDiscLoading] = useState(false)
  const [discForm, setDiscForm] = useState(emptyDisc)
  const [editingDiscId, setEditingDiscId] = useState(null)
  const [turmas, setTurmas] = useState([])
  const [turmasLoading, setTurmasLoading] = useState(false)
  const [turmaForm, setTurmaForm] = useState(emptyTurma)
  const [editingTurmaId, setEditingTurmaId] = useState(null)

  const onSchemaPendingRef = useRef(onSchemaPending)
  onSchemaPendingRef.current = onSchemaPending

  const periodoId = periodo?.id ?? null

  const loadCursos = useCallback(async () => {
    if (!periodoId) {
      setCursos([])
      return
    }
    setLoading(true)
    try {
      const data = await listarCursos(periodoId)
      setCursos(Array.isArray(data?.cursos) ? data.cursos : [])
    } catch (err) {
      if (isSchemaPendingError(err)) onSchemaPendingRef.current?.()
      else window.alert(err?.message || 'Falha ao carregar cursos')
      setCursos([])
    } finally {
      setLoading(false)
    }
  }, [periodoId])

  const loadDisciplinas = useCallback(async (cursoId) => {
    if (!cursoId) {
      setDisciplinas([])
      return
    }
    setDiscLoading(true)
    try {
      const data = await listarDisciplinas(cursoId)
      setDisciplinas(Array.isArray(data?.disciplinas) ? data.disciplinas : [])
    } catch (err) {
      if (isSchemaPendingError(err)) onSchemaPendingRef.current?.()
      else window.alert(err?.message || 'Falha ao carregar disciplinas')
      setDisciplinas([])
    } finally {
      setDiscLoading(false)
    }
  }, [])

  const loadTurmas = useCallback(async (cursoId) => {
    if (!cursoId) {
      setTurmas([])
      return
    }
    setTurmasLoading(true)
    try {
      const data = await listarTurmas(cursoId)
      setTurmas(Array.isArray(data?.turmas) ? data.turmas : [])
    } catch (err) {
      if (isSchemaPendingError(err)) onSchemaPendingRef.current?.()
      else window.alert(err?.message || 'Falha ao carregar turmas')
      setTurmas([])
    } finally {
      setTurmasLoading(false)
    }
  }, [])

  useEffect(() => {
    setSelectedCursoId(null)
    setEditingCursoId(null)
    setCursoForm(emptyCurso)
    setEditingDiscId(null)
    setDiscForm(emptyDisc)
    setEditingTurmaId(null)
    setTurmaForm(emptyTurma)
    void loadCursos()
  }, [periodoId, loadCursos])

  useEffect(() => {
    setEditingDiscId(null)
    setDiscForm(emptyDisc)
    setEditingTurmaId(null)
    setTurmaForm(emptyTurma)
    void loadDisciplinas(selectedCursoId)
    void loadTurmas(selectedCursoId)
  }, [selectedCursoId, loadDisciplinas, loadTurmas])

  if (!periodo) return null

  const selectedCurso = cursos.find((c) => c.id === selectedCursoId) || null

  async function handleSaveCurso(e) {
    e.preventDefault()
    setBusy(true)
    const payload = {
      ...cursoForm,
      nivel: cursoForm.nivel || null,
      carga_horaria_total_horas:
        cursoForm.carga_horaria_total_horas === ''
          ? null
          : Number(cursoForm.carga_horaria_total_horas),
    }
    try {
      if (editingCursoId) {
        await atualizarCurso(editingCursoId, payload)
      } else {
        const created = await criarCurso(periodo.id, payload)
        const id = created?.curso?.id
        if (id) setSelectedCursoId(id)
      }
      setEditingCursoId(null)
      setCursoForm(emptyCurso)
      await loadCursos()
    } catch (err) {
      if (isSchemaPendingError(err)) onSchemaPending?.()
      else window.alert(err?.message || 'Falha ao salvar curso')
    } finally {
      setBusy(false)
    }
  }

  async function handleDeleteCurso(curso) {
    if (!window.confirm(`Desativar o curso “${curso.nome}”?`)) return
    setBusy(true)
    try {
      await desativarCurso(curso.id)
      if (selectedCursoId === curso.id) setSelectedCursoId(null)
      if (editingCursoId === curso.id) {
        setEditingCursoId(null)
        setCursoForm(emptyCurso)
      }
      await loadCursos()
    } catch (err) {
      window.alert(err?.message || 'Falha ao desativar curso')
    } finally {
      setBusy(false)
    }
  }

  async function handleSaveTurma(e) {
    e.preventDefault()
    if (!selectedCursoId) return
    setBusy(true)
    const payload = {
      nome: (turmaForm.nome || '').trim(),
      turno: (turmaForm.turno || '').trim() || null,
    }
    try {
      if (editingTurmaId) {
        await atualizarTurma(editingTurmaId, payload)
      } else {
        await criarTurma(selectedCursoId, payload)
      }
      setEditingTurmaId(null)
      setTurmaForm(emptyTurma)
      await loadTurmas(selectedCursoId)
      await loadCursos()
    } catch (err) {
      window.alert(err?.message || 'Falha ao salvar turma')
    } finally {
      setBusy(false)
    }
  }

  async function handleDeleteTurma(t) {
    if (!window.confirm(`Desativar a turma “${t.nome}”?`)) return
    setBusy(true)
    try {
      await desativarTurma(t.id)
      if (editingTurmaId === t.id) {
        setEditingTurmaId(null)
        setTurmaForm(emptyTurma)
      }
      await loadTurmas(selectedCursoId)
      await loadCursos()
    } catch (err) {
      window.alert(err?.message || 'Falha ao desativar turma')
    } finally {
      setBusy(false)
    }
  }

  async function handleSaveDisc(e) {
    e.preventDefault()
    if (!selectedCursoId) return
    setBusy(true)
    const payload = {
      ...discForm,
      carga_horaria_horas:
        discForm.carga_horaria_horas === '' ? null : Number(discForm.carga_horaria_horas),
    }
    try {
      if (editingDiscId) {
        await atualizarDisciplina(editingDiscId, payload)
      } else {
        await criarDisciplina(selectedCursoId, payload)
      }
      setEditingDiscId(null)
      setDiscForm(emptyDisc)
      await loadDisciplinas(selectedCursoId)
      await loadCursos()
    } catch (err) {
      window.alert(err?.message || 'Falha ao salvar disciplina')
    } finally {
      setBusy(false)
    }
  }

  async function handleDeleteDisc(d) {
    if (!window.confirm(`Desativar a disciplina “${d.nome}”?`)) return
    setBusy(true)
    try {
      await desativarDisciplina(d.id)
      if (editingDiscId === d.id) {
        setEditingDiscId(null)
        setDiscForm(emptyDisc)
      }
      await loadDisciplinas(selectedCursoId)
      await loadCursos()
    } catch (err) {
      window.alert(err?.message || 'Falha ao desativar disciplina')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mt-4 space-y-4 rounded-2xl border border-bordo/20 bg-bordo/[0.03] p-4 sm:p-5">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-wider text-brand-600">
          Cursos, turmas e disciplinas
        </p>
        <h3 className="font-display text-lg font-bold text-bordo-deep">
          {periodo.rotulo}
        </h3>
        <p className="text-xs text-bordo-soft">
          {readOnly
            ? 'Estrutura espelhada da escola — somente consulta.'
            : 'Um curso pode ter várias turmas. Cadastro opcional — não bloqueia aulas avulsas no plano gratuito.'}
        </p>
      </div>

      {readOnly ? null : (
      <form onSubmit={handleSaveCurso} className="grid gap-3 rounded-xl border border-brand-100 bg-white p-3 sm:grid-cols-2">
        <label className="sm:col-span-2 block text-xs font-semibold text-bordo-soft">
          {editingCursoId ? 'Editar curso' : 'Novo curso'} *
          <input
            required
            className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
            value={cursoForm.nome}
            onChange={(e) => setCursoForm((f) => ({ ...f, nome: e.target.value }))}
            placeholder="ex.: Ensino Médio — 3º ano"
          />
        </label>
        <label className="block text-xs font-semibold text-bordo-soft">
          Nível
          <select
            className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
            value={cursoForm.nivel}
            onChange={(e) => setCursoForm((f) => ({ ...f, nivel: e.target.value }))}
          >
            {NIVEIS.map((n) => (
              <option key={n.value || 'empty'} value={n.value}>
                {n.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-xs font-semibold text-bordo-soft">
          Carga total (horas)
          <input
            type="number"
            min={0}
            step="0.5"
            className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
            value={cursoForm.carga_horaria_total_horas}
            onChange={(e) =>
              setCursoForm((f) => ({ ...f, carga_horaria_total_horas: e.target.value }))
            }
          />
        </label>
        <div className="sm:col-span-2 flex flex-wrap gap-2">
          <button type="submit" disabled={busy} className="btn-primary !px-3 !py-1.5 text-xs">
            {editingCursoId ? 'Salvar curso' : 'Adicionar curso'}
          </button>
          {editingCursoId ? (
            <button
              type="button"
              className="btn-ghost !px-3 !py-1.5 text-xs"
              onClick={() => {
                setEditingCursoId(null)
                setCursoForm(emptyCurso)
              }}
            >
              Cancelar
            </button>
          ) : null}
        </div>
      </form>
      )}

      <div className="rounded-xl border border-brand-100 bg-white p-3">
        <h4 className="text-xs font-bold text-bordo">Cursos do período</h4>
        {loading ? (
          <p className="mt-2 text-xs text-bordo-soft">Carregando…</p>
        ) : cursos.length === 0 ? (
          <p className="mt-2 text-xs text-bordo-soft">Nenhum curso ainda.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {cursos.map((c) => (
              <li
                key={c.id}
                className={`rounded-lg border px-3 py-2 ${
                  selectedCursoId === c.id ? 'border-bordo/40 bg-brand-50/50' : 'border-brand-100'
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <button
                    type="button"
                    className="min-w-0 flex-1 text-left"
                    onClick={() => setSelectedCursoId(c.id)}
                  >
                    <p className="text-sm font-semibold text-bordo-deep">{c.nome}</p>
                    <p className="text-[11px] text-bordo-soft">
                      {c.nivel || 'nível —'}
                      {` · ${c.turmas_count || 0} turma(s)`}
                      {` · ${c.disciplinas_count || 0} disciplina(s)`}
                    </p>
                  </button>
                  {readOnly ? null : (
                  <div className="flex gap-1">
                    <button
                      type="button"
                      className="btn-ghost !px-2 !py-1 text-[11px]"
                      onClick={() => {
                        setSelectedCursoId(c.id)
                        setEditingCursoId(c.id)
                        setCursoForm({
                          nome: c.nome || '',
                          nivel: c.nivel || '',
                          carga_horaria_total_horas: c.carga_horaria_total_horas ?? '',
                          observacoes: c.observacoes || '',
                        })
                      }}
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      className="btn-ghost !px-2 !py-1 text-[11px] text-red-700"
                      disabled={busy}
                      onClick={() => handleDeleteCurso(c)}
                    >
                      Desativar
                    </button>
                  </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {selectedCurso ? (
        <div className="space-y-4">
          <div className="space-y-3 rounded-xl border border-brand-100 bg-white p-3">
            <h4 className="text-xs font-bold text-bordo">Turmas — {selectedCurso.nome}</h4>
            <p className="text-[11px] text-bordo-soft">
              {readOnly
                ? 'Turmas alocadas pela escola.'
                : 'Um curso pode ter várias turmas (ex.: 3ºA manhã, 3ºB tarde).'}
            </p>

            {readOnly ? null : (
            <form onSubmit={handleSaveTurma} className="grid gap-2 sm:grid-cols-2">
              <label className="block text-xs font-semibold text-bordo-soft">
                {editingTurmaId ? 'Editar turma' : 'Nova turma'} *
                <input
                  required
                  className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                  value={turmaForm.nome}
                  onChange={(e) => setTurmaForm((f) => ({ ...f, nome: e.target.value }))}
                  placeholder="ex.: 3ºA"
                />
              </label>
              <label className="block text-xs font-semibold text-bordo-soft">
                Turno
                <input
                  className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                  value={turmaForm.turno}
                  onChange={(e) => setTurmaForm((f) => ({ ...f, turno: e.target.value }))}
                  placeholder="ex.: manhã"
                />
              </label>
              <div className="sm:col-span-2 flex flex-wrap gap-2">
                <button type="submit" disabled={busy} className="btn-primary !px-3 !py-1.5 text-xs">
                  {editingTurmaId ? 'Salvar turma' : 'Adicionar turma'}
                </button>
                {editingTurmaId ? (
                  <button
                    type="button"
                    className="btn-ghost !px-3 !py-1.5 text-xs"
                    onClick={() => {
                      setEditingTurmaId(null)
                      setTurmaForm(emptyTurma)
                    }}
                  >
                    Cancelar
                  </button>
                ) : null}
              </div>
            </form>
            )}

            {turmasLoading ? (
              <p className="text-xs text-bordo-soft">Carregando turmas…</p>
            ) : turmas.length === 0 ? (
              <p className="text-xs text-bordo-soft">
                {readOnly ? 'Nenhuma turma alocada ainda.' : 'Nenhuma turma ainda — adicione pelo menos uma.'}
              </p>
            ) : (
              <ul className="space-y-2">
                {turmas.map((t) => (
                  <li
                    key={t.id}
                    className="flex flex-wrap items-start justify-between gap-2 rounded-lg border border-brand-100 px-3 py-2"
                  >
                    <div>
                      <p className="text-sm font-semibold text-bordo-deep">{t.nome}</p>
                      {t.turno ? (
                        <p className="text-[11px] text-bordo-soft">{t.turno}</p>
                      ) : null}
                    </div>
                    {readOnly ? null : (
                    <div className="flex gap-1">
                      <button
                        type="button"
                        className="btn-ghost !px-2 !py-1 text-[11px]"
                        onClick={() => {
                          setEditingTurmaId(t.id)
                          setTurmaForm({
                            nome: t.nome || '',
                            turno: t.turno || '',
                          })
                        }}
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        className="btn-ghost !px-2 !py-1 text-[11px] text-red-700"
                        disabled={busy}
                        onClick={() => handleDeleteTurma(t)}
                      >
                        Desativar
                      </button>
                    </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="space-y-3 rounded-xl border border-brand-100 bg-white p-3">
            <h4 className="text-xs font-bold text-bordo">
              Disciplinas — {selectedCurso.nome}
            </h4>

            {readOnly ? null : (
            <form onSubmit={handleSaveDisc} className="grid gap-2 sm:grid-cols-2">
              <label className="sm:col-span-2 block text-xs font-semibold text-bordo-soft">
                {editingDiscId ? 'Editar disciplina' : 'Nova disciplina'} *
                <input
                  required
                  className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                  value={discForm.nome}
                  onChange={(e) => setDiscForm((f) => ({ ...f, nome: e.target.value }))}
                />
              </label>
              <label className="block text-xs font-semibold text-bordo-soft">
                Código
                <input
                  className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                  value={discForm.codigo}
                  onChange={(e) => setDiscForm((f) => ({ ...f, codigo: e.target.value }))}
                />
              </label>
              <label className="block text-xs font-semibold text-bordo-soft">
                Carga (horas)
                <input
                  type="number"
                  min={0}
                  step="0.5"
                  className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                  value={discForm.carga_horaria_horas}
                  onChange={(e) =>
                    setDiscForm((f) => ({ ...f, carga_horaria_horas: e.target.value }))
                  }
                />
              </label>
              <label className="sm:col-span-2 block text-xs font-semibold text-bordo-soft">
                Ementa
                <textarea
                  rows={4}
                  className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                  value={discForm.ementa}
                  onChange={(e) => setDiscForm((f) => ({ ...f, ementa: e.target.value }))}
                  placeholder={'Um tópico por linha, ex.:\nLeis de Newton\nEnergia mecânica\nTermodinâmica'}
                />
                <span className="mt-1 block text-[11px] font-normal leading-relaxed text-bordo-soft/90">
                  Uma linha = um tópico. No Dia a Dia, o professor escolhe o item da ementa
                  no plano da aula.
                </span>
              </label>
              <div className="sm:col-span-2 flex flex-wrap gap-2">
                <button type="submit" disabled={busy} className="btn-primary !px-3 !py-1.5 text-xs">
                  {editingDiscId ? 'Salvar disciplina' : 'Adicionar disciplina'}
                </button>
                {editingDiscId ? (
                  <button
                    type="button"
                    className="btn-ghost !px-3 !py-1.5 text-xs"
                    onClick={() => {
                      setEditingDiscId(null)
                      setDiscForm(emptyDisc)
                    }}
                  >
                    Cancelar
                  </button>
                ) : null}
              </div>
            </form>
            )}

            {discLoading ? (
              <p className="text-xs text-bordo-soft">Carregando disciplinas…</p>
            ) : disciplinas.length === 0 ? (
              <p className="text-xs text-bordo-soft">
                {readOnly ? 'Nenhuma disciplina alocada ainda.' : 'Nenhuma disciplina ainda.'}
              </p>
            ) : (
              <ul className="space-y-2">
                {disciplinas.map((d) => (
                  <li
                    key={d.id}
                    className="flex flex-wrap items-start justify-between gap-2 rounded-lg border border-brand-100 px-3 py-2"
                  >
                    <div>
                      <p className="text-sm font-semibold text-bordo-deep">
                        {d.nome}
                        {d.codigo ? (
                          <span className="ml-2 text-[11px] font-normal text-bordo-soft">
                            ({d.codigo})
                          </span>
                        ) : null}
                      </p>
                      {d.carga_horaria_horas != null ? (
                        <p className="text-[11px] text-bordo-soft">{d.carga_horaria_horas} h</p>
                      ) : null}
                    </div>
                    {readOnly ? null : (
                    <div className="flex gap-1">
                      <button
                        type="button"
                        className="btn-ghost !px-2 !py-1 text-[11px]"
                        onClick={() => {
                          setEditingDiscId(d.id)
                          setDiscForm({
                            nome: d.nome || '',
                            codigo: d.codigo || '',
                            carga_horaria_horas: d.carga_horaria_horas ?? '',
                            ementa: d.ementa || '',
                          })
                        }}
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        className="btn-ghost !px-2 !py-1 text-[11px] text-red-700"
                        disabled={busy}
                        onClick={() => handleDeleteDisc(d)}
                      >
                        Desativar
                      </button>
                    </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : (
        <p className="text-xs text-bordo-soft">
          Selecione um curso para {readOnly ? 'consultar' : 'gerenciar'} turmas e disciplinas.
        </p>
      )}
    </div>
  )
}
