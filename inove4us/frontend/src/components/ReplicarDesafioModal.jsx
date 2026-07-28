import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import VinculoPedagogicoSelector from './VinculoPedagogicoSelector'
import {
  criarCurso,
  listarCursos,
  listarInstituicoes,
  listarPeriodos,
} from '../services/instituicoesService'

const TURNO_OPTS = [
  { id: 'manha', label: 'Manhã' },
  { id: 'tarde', label: 'Tarde' },
  { id: 'noite', label: 'Noite' },
]

function hojeISO() {
  const d = new Date()
  const p = (n) => (n < 10 ? `0${n}` : String(n))
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function addDaysISO(iso, days) {
  const [y, m, d] = String(iso).slice(0, 10).split('-').map(Number)
  const dt = new Date(y, m - 1, d + days)
  const p = (n) => (n < 10 ? `0${n}` : String(n))
  return `${dt.getFullYear()}-${p(dt.getMonth() + 1)}-${p(dt.getDate())}`
}

/**
 * Modal: replicar desafio para outra turma — sem IA.
 * Reaproveita hipótese/causas/tema; cria nova cadeia + Kanban independentes.
 */
export default function ReplicarDesafioModal({
  open,
  onClose,
  desafioId,
  sourceEventoId,
  suggestFromDesafio = false,
  onDone,
}) {
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [erro, setErro] = useState('')
  const [turma, setTurma] = useState('')
  const [turnoPadrao, setTurnoPadrao] = useState('tarde')
  const [disciplinaId, setDisciplinaId] = useState(null)
  const [aulas, setAulas] = useState([])
  const [showNovoCurso, setShowNovoCurso] = useState(false)
  const [novoCursoNome, setNovoCursoNome] = useState('')
  const [periodoIdNovo, setPeriodoIdNovo] = useState('')
  const [periodosOpts, setPeriodosOpts] = useState([])
  const [cursosOpts, setCursosOpts] = useState([])
  const [cursoSel, setCursoSel] = useState('')

  useEffect(() => {
    if (!open) return
    if (!sourceEventoId && !desafioId) return
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setErro('')
      try {
        const base = hojeISO()
        if (sourceEventoId) {
          const kb = await api.getAgendaKanban(sourceEventoId)
          if (cancelled) return
          const src = kb.aulas || []
          setAulas(
            src.length
              ? src.map((a, i) => ({
                  key: `a-${i}`,
                  titulo: (a.titulo || `Aula ${i + 1}`).replace(/\s·\s.*$/, '').trim(),
                  data: addDaysISO(base, i * 7),
                  turno: a.turno || 'tarde',
                  modo_execucao: i === 0 ? 'reinicio' : 'continuidade',
                }))
              : [
                  {
                    key: 'a-0',
                    titulo: 'Aula 1',
                    data: base,
                    turno: 'tarde',
                    modo_execucao: 'reinicio',
                  },
                ],
          )
          setTurnoPadrao(src[0]?.turno || 'tarde')
        } else if (desafioId || suggestFromDesafio) {
          const dRes = await api.getDesafio(desafioId)
          if (cancelled) return
          const plano = dRes.desafio?.plan_data?.plano || dRes.desafio?.plan_data?.plano_eduscrum
          const missao = plano?.missao || dRes.desafio?.titulo || 'Aula 1'
          setAulas([
            {
              key: 'a-0',
              titulo: String(missao).slice(0, 120),
              data: base,
              turno: 'tarde',
              modo_execucao: 'reinicio',
            },
          ])
          setTurnoPadrao('tarde')
        }
      } catch (err) {
        if (!cancelled) setErro(err.message || 'Falha ao carregar estrutura sugerida.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [open, sourceEventoId, desafioId, suggestFromDesafio])

  useEffect(() => {
    if (!open) return
    let cancelled = false
    ;(async () => {
      try {
        const insts = await listarInstituicoes()
        const list = Array.isArray(insts?.instituicoes) ? insts.instituicoes : []
        const pers = []
        for (const inst of list) {
          try {
            const pd = await listarPeriodos(inst.id)
            const rows = Array.isArray(pd?.periodos) ? pd.periodos : []
            for (const p of rows) {
              pers.push({
                id: p.id,
                label: `${inst.nome || 'Instituição'} · ${p.rotulo || p.ano_letivo || p.id}`,
              })
            }
          } catch {
            /* skip */
          }
        }
        if (!cancelled) setPeriodosOpts(pers)
      } catch {
        if (!cancelled) setPeriodosOpts([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [open])

  useEffect(() => {
    if (!periodoIdNovo) {
      setCursosOpts([])
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const data = await listarCursos(periodoIdNovo)
        if (!cancelled) setCursosOpts(Array.isArray(data?.cursos) ? data.cursos : [])
      } catch {
        if (!cancelled) setCursosOpts([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [periodoIdNovo])

  function updateAula(key, patch) {
    setAulas((prev) => prev.map((a) => (a.key === key ? { ...a, ...patch } : a)))
  }

  function addAula() {
    setAulas((prev) => [
      ...prev,
      {
        key: `a-${Date.now()}`,
        titulo: `Aula ${prev.length + 1}`,
        data: addDaysISO(prev[prev.length - 1]?.data || hojeISO(), 7),
        turno: turnoPadrao,
        modo_execucao: 'continuidade',
      },
    ])
  }

  function removeAula(key) {
    setAulas((prev) => (prev.length <= 1 ? prev : prev.filter((a) => a.key !== key)))
  }

  async function handleCriarCurso() {
    setErro('')
    if (!periodoIdNovo || !novoCursoNome.trim()) {
      setErro('Informe período e nome do curso.')
      return
    }
    try {
      const data = await criarCurso(periodoIdNovo, {
        nome: novoCursoNome.trim(),
        turma_turno: turma.trim() || novoCursoNome.trim(),
      })
      const c = data?.curso
      if (c?.id) {
        setCursosOpts((prev) => [...prev, c])
        setCursoSel(String(c.id))
        if (!turma.trim() && (c.turma_turno || c.nome)) {
          setTurma(c.turma_turno || c.nome)
        }
        setShowNovoCurso(false)
        setNovoCursoNome('')
      }
    } catch (err) {
      setErro(err.message || 'Falha ao criar curso.')
    }
  }

  async function handleSubmit(e) {
    e?.preventDefault?.()
    setErro('')
    if (!desafioId) {
      setErro('Desafio ainda não resolvido. Tente novamente.')
      return
    }
    if (!turma.trim()) {
      setErro('Informe a turma de destino.')
      return
    }
    for (const a of aulas) {
      if (!a.data) {
        setErro('Cada aula precisa de uma data.')
        return
      }
    }
    setBusy(true)
    try {
      const payload = {
        turma: turma.trim(),
        turno: turnoPadrao,
        aulas: aulas.map((a) => ({
          titulo: a.titulo,
          data: a.data,
          turno: a.turno || turnoPadrao,
          modo_execucao: a.modo_execucao,
        })),
        ...(disciplinaId != null ? { disciplina_id: disciplinaId } : {}),
      }
      const data = await api.replicarDesafio(desafioId, payload)
      onDone?.(data)
      onClose?.()
    } catch (err) {
      setErro(err.message || 'Falha ao replicar.')
    } finally {
      setBusy(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-3 sm:items-center">
      <div
        className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-brand-200 bg-white p-5 shadow-xl"
        role="dialog"
        aria-labelledby="replicar-titulo"
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
              Sem nova chamada de IA
            </p>
            <h2 id="replicar-titulo" className="font-display text-xl font-bold text-bordo-deep">
              Replicar para outra turma
            </h2>
            <p className="mt-1 text-xs text-bordo-soft">
              Copia hipótese, causas e tema. Cria aulas e Kanban novos, independentes.
            </p>
          </div>
          <button type="button" className="btn-ghost !px-2 !py-1 text-xs" onClick={onClose}>
            Fechar
          </button>
        </div>

        {loading ? (
          <p className="py-8 text-center text-sm text-bordo-soft">Carregando estrutura…</p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <label className="block">
              <span className="text-[10px] font-bold uppercase tracking-wide text-bordo">
                Turma de destino
              </span>
              <input
                className="field-input mt-1"
                value={turma}
                onChange={(e) => setTurma(e.target.value)}
                placeholder="Ex.: 8º ano B"
                required
              />
            </label>

            <label className="block">
              <span className="text-[10px] font-bold uppercase tracking-wide text-bordo">
                Turno padrão
              </span>
              <select
                className="field-input mt-1"
                value={turnoPadrao}
                onChange={(e) => setTurnoPadrao(e.target.value)}
              >
                {TURNO_OPTS.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="rounded-xl border border-brand-100 bg-brand-50/50 p-3">
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-bordo">
                Curso / disciplina (opcional)
              </p>
              <VinculoPedagogicoSelector
                disciplinaId={disciplinaId}
                onChange={(id) => setDisciplinaId(id)}
                autoDefault={false}
              />
              <div className="mt-3 space-y-2 border-t border-brand-100 pt-3">
                <label className="block">
                  <span className="text-[10px] font-bold uppercase text-bordo-soft">
                    Ou escolher curso cadastrado
                  </span>
                  <select
                    className="field-input mt-1"
                    value={periodoIdNovo}
                    onChange={(e) => {
                      setPeriodoIdNovo(e.target.value)
                      setCursoSel('')
                    }}
                  >
                    <option value="">Período letivo…</option>
                    {periodosOpts.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                </label>
                {periodoIdNovo ? (
                  <select
                    className="field-input"
                    value={cursoSel}
                    onChange={(e) => {
                      const id = e.target.value
                      setCursoSel(id)
                      const c = cursosOpts.find((x) => String(x.id) === String(id))
                      if (c && (c.turma_turno || c.nome)) {
                        setTurma(c.turma_turno || c.nome)
                      }
                    }}
                  >
                    <option value="">Curso…</option>
                    {cursosOpts.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nome}
                        {c.turma_turno ? ` · ${c.turma_turno}` : ''}
                      </option>
                    ))}
                  </select>
                ) : null}
                <button
                  type="button"
                  className="text-[11px] font-bold text-brand-700 hover:underline"
                  onClick={() => setShowNovoCurso((v) => !v)}
                >
                  {showNovoCurso ? 'Cancelar novo curso' : '+ Cadastrar curso neste período'}
                </button>
                {showNovoCurso ? (
                  <div className="flex flex-wrap gap-2">
                    <input
                      className="field-input min-w-[140px] flex-1 !py-2 text-sm"
                      placeholder="Nome do curso"
                      value={novoCursoNome}
                      onChange={(e) => setNovoCursoNome(e.target.value)}
                    />
                    <button
                      type="button"
                      className="btn-ghost !px-3 !py-2 text-xs"
                      onClick={handleCriarCurso}
                    >
                      Criar
                    </button>
                  </div>
                ) : null}
              </div>
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="text-[10px] font-bold uppercase tracking-wide text-bordo">
                  Aulas da nova execução
                </p>
                <button type="button" className="text-[11px] font-bold text-brand-700" onClick={addAula}>
                  + Aula
                </button>
              </div>
              <ul className="space-y-2">
                {aulas.map((a, idx) => (
                  <li
                    key={a.key}
                    className="rounded-xl border border-brand-100 bg-white p-3"
                  >
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <span className="text-[10px] font-bold uppercase text-bordo-soft">
                        Aula {idx + 1}
                      </span>
                      {aulas.length > 1 ? (
                        <button
                          type="button"
                          className="text-[10px] font-bold text-rose-600"
                          onClick={() => removeAula(a.key)}
                        >
                          Remover
                        </button>
                      ) : null}
                    </div>
                    <input
                      className="field-input mb-2 !py-2 text-sm"
                      value={a.titulo}
                      onChange={(e) => updateAula(a.key, { titulo: e.target.value })}
                      placeholder="Título"
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="date"
                        className="field-input !py-2 text-sm"
                        value={a.data}
                        onChange={(e) => updateAula(a.key, { data: e.target.value })}
                        required
                      />
                      <select
                        className="field-input !py-2 text-sm"
                        value={a.turno}
                        onChange={(e) => updateAula(a.key, { turno: e.target.value })}
                      >
                        {TURNO_OPTS.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {erro ? (
              <p className="rounded-lg bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-800">
                {erro}
              </p>
            ) : null}

            <div className="flex flex-wrap justify-end gap-2 pt-1">
              <button type="button" className="btn-ghost !px-4 !py-2 text-sm" onClick={onClose}>
                Cancelar
              </button>
              <button
                type="submit"
                className="btn-primary !px-4 !py-2 text-sm"
                disabled={busy}
              >
                {busy ? 'Replicando…' : 'Confirmar réplica'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
