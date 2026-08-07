import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../lib/auth'
import { tabClassNameCompact } from '../lib/tabs'

const FALLBACK_INSTITUICAO_ID =
  import.meta.env.VITE_INSTITUICAO_ID || 'a1111111-1111-4111-8111-111111111111'

const TABS = [
  { id: 'unidades', label: 'Unidades' },
  { id: 'periodos', label: 'Períodos letivos' },
  { id: 'cursos', label: 'Cursos' },
  { id: 'disciplinas', label: 'Disciplinas / ementas' },
  { id: 'calendario', label: 'Calendário' },
  { id: 'comunicacoes', label: 'Comunicações' },
]

const TIPOS_PERIODO = [
  { value: 'anual', label: 'Anual' },
  { value: 'semestral', label: 'Semestral' },
  { value: 'trimestral', label: 'Trimestral' },
  { value: 'modular', label: 'Modular' },
]

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

const CAL_TIPOS = [
  { value: 'letivo', label: 'Letivo' },
  { value: 'feriado', label: 'Feriado' },
  { value: 'avaliacao', label: 'Avaliação' },
  { value: 'evento', label: 'Evento' },
]

const COM_TIPOS = [
  { value: 'reuniao_pedagogica', label: 'Reunião pedagógica' },
  { value: 'evento_escolar', label: 'Evento escolar' },
]

const PUBLICOS = [
  { value: 'toda_instituicao', label: 'Toda a instituição' },
  { value: 'unidade', label: 'Unidade' },
  { value: 'professores', label: 'Professores' },
]

const inputCls =
  'w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100'
const labelCls = 'mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted'

function formatDate(iso) {
  if (!iso) return '—'
  const [y, m, d] = String(iso).slice(0, 10).split('-')
  return `${d}/${m}/${y}`
}

function formatWhen(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export default function Secretaria() {
  const { user } = useAuth()
  const instituicaoId = user?.instituicao_id || FALLBACK_INSTITUICAO_ID

  const [tab, setTab] = useState('unidades')
  const [unidades, setUnidades] = useState([])
  const [periodos, setPeriodos] = useState([])
  const [cursos, setCursos] = useState([])
  const [disciplinas, setDisciplinas] = useState([])
  const [calendario, setCalendario] = useState([])
  const [comunicacoes, setComunicacoes] = useState([])
  const [periodoId, setPeriodoId] = useState('')
  const [cursoId, setCursoId] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')

  const [uniForm, setUniForm] = useState({ nome: '', codigo: '', cidade: '', uf: '' })
  const [perForm, setPerForm] = useState({
    rotulo: '',
    ano_letivo: String(new Date().getFullYear()),
    tipo_periodo: 'semestral',
    data_inicio: '',
    data_fim: '',
    unidade_id: '',
  })
  const [curForm, setCurForm] = useState({ nome: '', nivel: '', turma_turno: '' })
  const [discForm, setDiscForm] = useState({ nome: '', codigo: '', ementa: '' })
  const [calForm, setCalForm] = useState({
    titulo: '',
    tipo: 'letivo',
    data_inicio: '',
    data_fim: '',
    unidade_id: '',
  })
  const [comForm, setComForm] = useState({
    titulo: '',
    descricao: '',
    tipo: 'reuniao_pedagogica',
    publico_alvo: 'professores',
    data_hora_inicio: '',
    data_hora_fim: '',
    unidade_id: '',
  })

  const loadBase = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [u, p, c, co] = await Promise.all([
        fetch(`/api/instituicoes/${instituicaoId}/unidades-gestao`, { credentials: 'include' }),
        fetch(`/api/instituicoes/${instituicaoId}/periodos-letivos`, { credentials: 'include' }),
        fetch(`/api/instituicoes/${instituicaoId}/calendario-letivo`, { credentials: 'include' }),
        fetch(`/api/instituicoes/${instituicaoId}/comunicacoes`, { credentials: 'include' }),
      ])
      const [uj, pj, cj, coj] = await Promise.all([u.json(), p.json(), c.json(), co.json()])
      if (!u.ok) throw new Error(uj.error || 'Falha ao carregar unidades')
      if (!p.ok) throw new Error(pj.error || 'Falha ao carregar períodos')
      setUnidades(uj.items || [])
      const pers = pj.items || []
      setPeriodos(pers)
      setCalendario(cj.items || [])
      setComunicacoes(coj.items || [])
      if (!periodoId && pers[0]) setPeriodoId(pers[0].id)
    } catch (err) {
      setError(err.message || 'Erro ao carregar')
    } finally {
      setLoading(false)
    }
  }, [instituicaoId, periodoId])

  useEffect(() => {
    loadBase()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [instituicaoId])

  useEffect(() => {
    if (!periodoId) {
      setCursos([])
      setCursoId('')
      return
    }
    ;(async () => {
      try {
        const res = await fetch(`/api/periodos-letivos/${periodoId}/cursos`, {
          credentials: 'include',
        })
        const body = await res.json()
        if (!res.ok) throw new Error(body.error || 'Falha ao carregar cursos')
        const list = body.items || []
        setCursos(list)
        if (!list.find((c) => c.id === cursoId)) setCursoId(list[0]?.id || '')
      } catch (err) {
        setError(err.message)
      }
    })()
  }, [periodoId, cursoId])

  useEffect(() => {
    if (!cursoId) {
      setDisciplinas([])
      return
    }
    ;(async () => {
      try {
        const res = await fetch(`/api/cursos/${cursoId}/disciplinas`, {
          credentials: 'include',
        })
        const body = await res.json()
        if (!res.ok) throw new Error(body.error || 'Falha ao carregar disciplinas')
        setDisciplinas(body.items || [])
      } catch (err) {
        setError(err.message)
      }
    })()
  }, [cursoId])

  async function postJson(path, body) {
    const res = await fetch(path, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify(body),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.error || 'Falha ao salvar')
    return data
  }

  async function onSubmit(e, action, okMsg) {
    e.preventDefault()
    setBusy(true)
    setError('')
    setFeedback('')
    try {
      await action()
      setFeedback(okMsg)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Secretaria</h1>
        <p className="mt-1 text-sm text-muted">
          Hierarquia alinhada ao inove4us: instituição → unidade → período letivo → curso →
          disciplina (ementa). Sem cadastro de alunos.
        </p>
      </div>

      <div className="flex flex-wrap gap-1 border-b border-slate-200 pb-px">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={tabClassNameCompact(tab === t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {feedback ? <p className="text-sm text-school-700">{feedback}</p> : null}
      {error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
      {loading ? <p className="text-sm text-muted">Carregando…</p> : null}

      {!loading && tab === 'unidades' ? (
        <section className="space-y-4">
          <form
            onSubmit={(e) =>
              onSubmit(
                e,
                async () => {
                  const data = await postJson(
                    `/api/instituicoes/${instituicaoId}/unidades`,
                    uniForm,
                  )
                  setUnidades((prev) => [data.item, ...prev])
                  setUniForm({ nome: '', codigo: '', cidade: '', uf: '' })
                },
                'Unidade cadastrada.',
              )
            }
            className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-panel sm:grid-cols-2"
          >
            <label>
              <span className={labelCls}>Nome</span>
              <input required className={inputCls} value={uniForm.nome} onChange={(e) => setUniForm({ ...uniForm, nome: e.target.value })} />
            </label>
            <label>
              <span className={labelCls}>Código</span>
              <input className={inputCls} value={uniForm.codigo} onChange={(e) => setUniForm({ ...uniForm, codigo: e.target.value })} />
            </label>
            <label>
              <span className={labelCls}>Cidade</span>
              <input className={inputCls} value={uniForm.cidade} onChange={(e) => setUniForm({ ...uniForm, cidade: e.target.value })} />
            </label>
            <label>
              <span className={labelCls}>UF</span>
              <input className={inputCls} maxLength={2} value={uniForm.uf} onChange={(e) => setUniForm({ ...uniForm, uf: e.target.value.toUpperCase() })} />
            </label>
            <div>
              <button type="submit" disabled={busy} className="rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-60">
                Nova unidade
              </button>
            </div>
          </form>
          <DataTable
            columns={['Nome', 'Código', 'Cidade/UF', 'Status']}
            rows={unidades.map((u) => [
              u.nome,
              u.codigo || '—',
              [u.cidade, u.uf].filter(Boolean).join('/') || '—',
              u.ativo ? 'Ativa' : 'Inativa',
            ])}
            empty="Nenhuma unidade."
          />
        </section>
      ) : null}

      {!loading && tab === 'periodos' ? (
        <section className="space-y-4">
          <form
            onSubmit={(e) =>
              onSubmit(
                e,
                async () => {
                  const data = await postJson(
                    `/api/instituicoes/${instituicaoId}/periodos-letivos`,
                    {
                      ...perForm,
                      ano_letivo: Number(perForm.ano_letivo),
                      unidade_id: perForm.unidade_id || null,
                    },
                  )
                  setPeriodos((prev) => [data.item, ...prev])
                  setPeriodoId(data.item.id)
                  setPerForm({
                    rotulo: '',
                    ano_letivo: String(new Date().getFullYear()),
                    tipo_periodo: 'semestral',
                    data_inicio: '',
                    data_fim: '',
                    unidade_id: '',
                  })
                },
                'Período letivo cadastrado.',
              )
            }
            className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-panel sm:grid-cols-2"
          >
            <label className="sm:col-span-2">
              <span className={labelCls}>Rótulo</span>
              <input required className={inputCls} placeholder="2º semestre 2026" value={perForm.rotulo} onChange={(e) => setPerForm({ ...perForm, rotulo: e.target.value })} />
            </label>
            <label>
              <span className={labelCls}>Ano letivo</span>
              <input required type="number" className={inputCls} value={perForm.ano_letivo} onChange={(e) => setPerForm({ ...perForm, ano_letivo: e.target.value })} />
            </label>
            <label>
              <span className={labelCls}>Tipo</span>
              <select className={inputCls} value={perForm.tipo_periodo} onChange={(e) => setPerForm({ ...perForm, tipo_periodo: e.target.value })}>
                {TIPOS_PERIODO.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </label>
            <label>
              <span className={labelCls}>Início</span>
              <input required type="date" className={inputCls} value={perForm.data_inicio} onChange={(e) => setPerForm({ ...perForm, data_inicio: e.target.value })} />
            </label>
            <label>
              <span className={labelCls}>Fim</span>
              <input required type="date" className={inputCls} value={perForm.data_fim} onChange={(e) => setPerForm({ ...perForm, data_fim: e.target.value })} />
            </label>
            <label>
              <span className={labelCls}>Unidade</span>
              <select className={inputCls} value={perForm.unidade_id} onChange={(e) => setPerForm({ ...perForm, unidade_id: e.target.value })}>
                <option value="">Instituição inteira</option>
                {unidades.map((u) => (
                  <option key={u.id} value={u.id}>{u.nome}</option>
                ))}
              </select>
            </label>
            <div className="flex items-end">
              <button type="submit" disabled={busy} className="rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-60">
                Novo período
              </button>
            </div>
          </form>
          <DataTable
            columns={['Rótulo', 'Ano', 'Tipo', 'Início', 'Fim', 'Unidade']}
            rows={periodos.map((p) => [
              p.rotulo,
              p.ano_letivo,
              p.tipo_periodo,
              formatDate(p.data_inicio),
              formatDate(p.data_fim),
              p.unidade_nome || 'Instituição',
            ])}
            empty="Nenhum período letivo."
          />
        </section>
      ) : null}

      {!loading && tab === 'cursos' ? (
        <section className="space-y-4">
          <label className="block max-w-md">
            <span className={labelCls}>Período letivo</span>
            <select className={inputCls} value={periodoId} onChange={(e) => setPeriodoId(e.target.value)}>
              <option value="">Selecione…</option>
              {periodos.map((p) => (
                <option key={p.id} value={p.id}>{p.rotulo}</option>
              ))}
            </select>
          </label>
          <form
            onSubmit={(e) =>
              onSubmit(
                e,
                async () => {
                  if (!periodoId) throw new Error('Selecione um período letivo')
                  const data = await postJson(`/api/periodos-letivos/${periodoId}/cursos`, {
                    ...curForm,
                    nivel: curForm.nivel || null,
                  })
                  setCursos((prev) => [data.item, ...prev])
                  setCursoId(data.item.id)
                  setCurForm({ nome: '', nivel: '', turma_turno: '' })
                },
                'Curso cadastrado.',
              )
            }
            className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-panel sm:grid-cols-2"
          >
            <label className="sm:col-span-2">
              <span className={labelCls}>Nome do curso</span>
              <input required className={inputCls} value={curForm.nome} onChange={(e) => setCurForm({ ...curForm, nome: e.target.value })} placeholder="Ensino Fundamental — 6º ano" />
            </label>
            <label>
              <span className={labelCls}>Nível</span>
              <select className={inputCls} value={curForm.nivel} onChange={(e) => setCurForm({ ...curForm, nivel: e.target.value })}>
                {NIVEIS.map((n) => (
                  <option key={n.value || 'x'} value={n.value}>{n.label}</option>
                ))}
              </select>
            </label>
            <label>
              <span className={labelCls}>Turma / turno</span>
              <input className={inputCls} value={curForm.turma_turno} onChange={(e) => setCurForm({ ...curForm, turma_turno: e.target.value })} placeholder="Manhã" />
            </label>
            <div>
              <button type="submit" disabled={busy || !periodoId} className="rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-60">
                Novo curso
              </button>
            </div>
          </form>
          <DataTable
            columns={['Nome', 'Nível', 'Turma/turno', 'Status']}
            rows={cursos.map((c) => [c.nome, c.nivel || '—', c.turma_turno || '—', c.ativo ? 'Ativo' : 'Inativo'])}
            empty="Nenhum curso neste período."
          />
        </section>
      ) : null}

      {!loading && tab === 'disciplinas' ? (
        <section className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <label>
              <span className={labelCls}>Período</span>
              <select className={inputCls} value={periodoId} onChange={(e) => setPeriodoId(e.target.value)}>
                <option value="">Selecione…</option>
                {periodos.map((p) => (
                  <option key={p.id} value={p.id}>{p.rotulo}</option>
                ))}
              </select>
            </label>
            <label>
              <span className={labelCls}>Curso</span>
              <select className={inputCls} value={cursoId} onChange={(e) => setCursoId(e.target.value)}>
                <option value="">Selecione…</option>
                {cursos.map((c) => (
                  <option key={c.id} value={c.id}>{c.nome}</option>
                ))}
              </select>
            </label>
          </div>
          <form
            onSubmit={(e) =>
              onSubmit(
                e,
                async () => {
                  if (!cursoId) throw new Error('Selecione um curso')
                  const data = await postJson(`/api/cursos/${cursoId}/disciplinas`, discForm)
                  setDisciplinas((prev) => [data.item, ...prev])
                  setDiscForm({ nome: '', codigo: '', ementa: '' })
                },
                'Disciplina cadastrada com ementa.',
              )
            }
            className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-panel sm:grid-cols-2"
          >
            <label>
              <span className={labelCls}>Disciplina</span>
              <input required className={inputCls} value={discForm.nome} onChange={(e) => setDiscForm({ ...discForm, nome: e.target.value })} />
            </label>
            <label>
              <span className={labelCls}>Código</span>
              <input className={inputCls} value={discForm.codigo} onChange={(e) => setDiscForm({ ...discForm, codigo: e.target.value })} />
            </label>
            <label className="sm:col-span-2">
              <span className={labelCls}>Ementa (do curso)</span>
              <textarea rows={4} className={inputCls} value={discForm.ementa} onChange={(e) => setDiscForm({ ...discForm, ementa: e.target.value })} placeholder="Ementa da disciplina neste curso" />
            </label>
            <div>
              <button type="submit" disabled={busy || !cursoId} className="rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-60">
                Nova disciplina
              </button>
            </div>
          </form>
          <ul className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
            {disciplinas.length === 0 ? (
              <li className="px-4 py-8 text-center text-sm text-muted">Nenhuma disciplina neste curso.</li>
            ) : (
              disciplinas.map((d) => (
                <li key={d.id} className="px-4 py-4">
                  <p className="font-medium text-ink">
                    {d.nome}
                    {d.codigo ? <span className="ml-2 text-xs text-muted">({d.codigo})</span> : null}
                  </p>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-muted">
                    {d.ementa || 'Sem ementa cadastrada.'}
                  </p>
                </li>
              ))
            )}
          </ul>
        </section>
      ) : null}

      {!loading && tab === 'calendario' ? (
        <section className="space-y-4">
          <form
            onSubmit={(e) =>
              onSubmit(
                e,
                async () => {
                  const data = await postJson(
                    `/api/instituicoes/${instituicaoId}/calendario-letivo`,
                    { ...calForm, data_fim: calForm.data_fim || null, unidade_id: calForm.unidade_id || null },
                  )
                  setCalendario((prev) => [data.item, ...prev])
                  setCalForm({ titulo: '', tipo: 'letivo', data_inicio: '', data_fim: '', unidade_id: '' })
                },
                'Evento de calendário cadastrado.',
              )
            }
            className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-panel sm:grid-cols-2"
          >
            <label className="sm:col-span-2">
              <span className={labelCls}>Título</span>
              <input required className={inputCls} value={calForm.titulo} onChange={(e) => setCalForm({ ...calForm, titulo: e.target.value })} />
            </label>
            <label>
              <span className={labelCls}>Tipo</span>
              <select className={inputCls} value={calForm.tipo} onChange={(e) => setCalForm({ ...calForm, tipo: e.target.value })}>
                {CAL_TIPOS.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </label>
            <label>
              <span className={labelCls}>Unidade</span>
              <select className={inputCls} value={calForm.unidade_id} onChange={(e) => setCalForm({ ...calForm, unidade_id: e.target.value })}>
                <option value="">Instituição inteira</option>
                {unidades.map((u) => (
                  <option key={u.id} value={u.id}>{u.nome}</option>
                ))}
              </select>
            </label>
            <label>
              <span className={labelCls}>Início</span>
              <input required type="date" className={inputCls} value={calForm.data_inicio} onChange={(e) => setCalForm({ ...calForm, data_inicio: e.target.value })} />
            </label>
            <label>
              <span className={labelCls}>Fim</span>
              <input type="date" className={inputCls} value={calForm.data_fim} onChange={(e) => setCalForm({ ...calForm, data_fim: e.target.value })} />
            </label>
            <div>
              <button type="submit" disabled={busy} className="rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-60">
                Novo evento
              </button>
            </div>
          </form>
          <DataTable
            columns={['Título', 'Tipo', 'Início', 'Fim']}
            rows={calendario.map((c) => [c.titulo, c.tipo, formatDate(c.data_inicio), formatDate(c.data_fim)])}
            empty="Nenhum evento no calendário."
          />
        </section>
      ) : null}

      {!loading && tab === 'comunicacoes' ? (
        <section className="space-y-4">
          <form
            onSubmit={(e) =>
              onSubmit(
                e,
                async () => {
                  const data = await postJson(`/api/instituicoes/${instituicaoId}/comunicacoes`, {
                    ...comForm,
                    unidade_id: comForm.unidade_id || null,
                    data_hora_fim: comForm.data_hora_fim || null,
                    criado_por_gestor_id: user?.id || null,
                  })
                  setComunicacoes((prev) => [data.item, ...prev])
                  setComForm({
                    titulo: '',
                    descricao: '',
                    tipo: 'reuniao_pedagogica',
                    publico_alvo: 'professores',
                    data_hora_inicio: '',
                    data_hora_fim: '',
                    unidade_id: '',
                  })
                },
                'Comunicação cadastrada.',
              )
            }
            className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-panel sm:grid-cols-2"
          >
            <label className="sm:col-span-2">
              <span className={labelCls}>Título</span>
              <input required className={inputCls} value={comForm.titulo} onChange={(e) => setComForm({ ...comForm, titulo: e.target.value })} />
            </label>
            <label className="sm:col-span-2">
              <span className={labelCls}>Descrição</span>
              <textarea rows={2} className={inputCls} value={comForm.descricao} onChange={(e) => setComForm({ ...comForm, descricao: e.target.value })} />
            </label>
            <label>
              <span className={labelCls}>Tipo</span>
              <select className={inputCls} value={comForm.tipo} onChange={(e) => setComForm({ ...comForm, tipo: e.target.value })}>
                {COM_TIPOS.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </label>
            <label>
              <span className={labelCls}>Público</span>
              <select className={inputCls} value={comForm.publico_alvo} onChange={(e) => setComForm({ ...comForm, publico_alvo: e.target.value })}>
                {PUBLICOS.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </label>
            <label>
              <span className={labelCls}>Início</span>
              <input required type="datetime-local" className={inputCls} value={comForm.data_hora_inicio} onChange={(e) => setComForm({ ...comForm, data_hora_inicio: e.target.value })} />
            </label>
            <label>
              <span className={labelCls}>Fim</span>
              <input type="datetime-local" className={inputCls} value={comForm.data_hora_fim} onChange={(e) => setComForm({ ...comForm, data_hora_fim: e.target.value })} />
            </label>
            <div className="sm:col-span-2">
              <button type="submit" disabled={busy} className="rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-60">
                Salvar comunicação
              </button>
            </div>
          </form>
          <ul className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
            {comunicacoes.length === 0 ? (
              <li className="px-4 py-8 text-center text-sm text-muted">Nenhuma comunicação.</li>
            ) : (
              comunicacoes.map((item) => (
                <li key={item.id} className="px-4 py-4">
                  <p className="font-medium text-ink">{item.titulo}</p>
                  <p className="text-xs text-muted">
                    {item.tipo_label} · {item.publico_label} · {item.status_label}
                  </p>
                  <p className="mt-1 text-sm text-muted">{formatWhen(item.data_hora_inicio)}</p>
                </li>
              ))
            )}
          </ul>
        </section>
      ) : null}
    </div>
  )
}

function DataTable({ columns, rows, empty }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-muted">
            <tr>
              {columns.map((c) => (
                <th key={c} className="px-4 py-3">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center text-muted">
                  {empty}
                </td>
              </tr>
            ) : (
              rows.map((row, i) => (
                <tr key={i} className="border-b border-slate-100 last:border-0">
                  {row.map((cell, j) => (
                    <td key={j} className="px-4 py-3 text-ink">{cell}</td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
