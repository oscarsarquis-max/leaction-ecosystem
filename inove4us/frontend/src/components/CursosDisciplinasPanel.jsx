import { useCallback, useEffect, useState } from 'react'
import {
  atualizarCurso,
  atualizarDisciplina,
  criarCurso,
  criarDisciplina,
  desativarCurso,
  desativarDisciplina,
  isSchemaPendingError,
  listarCursos,
  listarDisciplinas,
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
  turma_turno: '',
  carga_horaria_total_horas: '',
  observacoes: '',
}

const emptyDisc = {
  nome: '',
  codigo: '',
  carga_horaria_horas: '',
  ementa: '',
}

/**
 * Drill-down: período → cursos → disciplinas (Etapa 2).
 */
export default function CursosDisciplinasPanel({ periodo, onSchemaPending }) {
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

  const loadCursos = useCallback(async () => {
    if (!periodo?.id) {
      setCursos([])
      return
    }
    setLoading(true)
    try {
      const data = await listarCursos(periodo.id)
      setCursos(Array.isArray(data?.cursos) ? data.cursos : [])
    } catch (err) {
      if (isSchemaPendingError(err)) onSchemaPending?.()
      else window.alert(err?.message || 'Falha ao carregar cursos')
      setCursos([])
    } finally {
      setLoading(false)
    }
  }, [periodo?.id, onSchemaPending])

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
      if (isSchemaPendingError(err)) onSchemaPending?.()
      else window.alert(err?.message || 'Falha ao carregar disciplinas')
      setDisciplinas([])
    } finally {
      setDiscLoading(false)
    }
  }, [onSchemaPending])

  useEffect(() => {
    setSelectedCursoId(null)
    setEditingCursoId(null)
    setCursoForm(emptyCurso)
    void loadCursos()
  }, [loadCursos])

  useEffect(() => {
    setEditingDiscId(null)
    setDiscForm(emptyDisc)
    void loadDisciplinas(selectedCursoId)
  }, [selectedCursoId, loadDisciplinas])

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
          Cursos e disciplinas
        </p>
        <h3 className="font-display text-lg font-bold text-bordo-deep">
          {periodo.rotulo}
        </h3>
        <p className="text-xs text-bordo-soft">
          Cadastro opcional — não bloqueia aulas avulsas no freemium.
        </p>
      </div>

      <form onSubmit={handleSaveCurso} className="grid gap-3 rounded-xl border border-brand-100 bg-white p-3 sm:grid-cols-2">
        <label className="sm:col-span-2 block text-xs font-semibold text-bordo-soft">
          {editingCursoId ? 'Editar curso' : 'Novo curso'} *
          <input
            required
            className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
            value={cursoForm.nome}
            onChange={(e) => setCursoForm((f) => ({ ...f, nome: e.target.value }))}
            placeholder='ex.: Ensino Médio — 3º ano'
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
          Turma / turno
          <input
            className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
            value={cursoForm.turma_turno}
            onChange={(e) => setCursoForm((f) => ({ ...f, turma_turno: e.target.value }))}
            placeholder="ex.: 3ºA — manhã"
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
                      {c.turma_turno ? ` · ${c.turma_turno}` : ''}
                      {` · ${c.disciplinas_count || 0} disciplina(s)`}
                    </p>
                  </button>
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
                          turma_turno: c.turma_turno || '',
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
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {selectedCurso ? (
        <div className="space-y-3 rounded-xl border border-brand-100 bg-white p-3">
          <h4 className="text-xs font-bold text-bordo">
            Disciplinas — {selectedCurso.nome}
          </h4>

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
                rows={2}
                className="mt-1 w-full rounded-lg border border-brand-200 px-3 py-2 text-sm"
                value={discForm.ementa}
                onChange={(e) => setDiscForm((f) => ({ ...f, ementa: e.target.value }))}
              />
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

          {discLoading ? (
            <p className="text-xs text-bordo-soft">Carregando disciplinas…</p>
          ) : disciplinas.length === 0 ? (
            <p className="text-xs text-bordo-soft">Nenhuma disciplina ainda.</p>
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
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <p className="text-xs text-bordo-soft">Selecione um curso para gerenciar disciplinas.</p>
      )}
    </div>
  )
}
