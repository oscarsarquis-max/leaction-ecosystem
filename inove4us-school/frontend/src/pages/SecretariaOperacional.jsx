import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '../lib/auth'

/**
 * Secretaria Acadêmica — painel operacional (CRUD + alocação docente).
 * Substitui a UI antiga "Secretaria" como superfície principal da zona operacional.
 */

const TABS = [
  { id: 'unidades', label: 'Unidades' },
  { id: 'periodos', label: 'Períodos Letivos' },
  { id: 'disciplinas', label: 'Disciplinas' },
  { id: 'alocacao', label: 'Alocação Docente' },
  { id: 'comunicacoes', label: 'Mural / Comunicações' },
]

const COM_TIPOS = [
  { value: 'reuniao_pedagogica', label: 'Reunião pedagógica' },
  { value: 'evento_escolar', label: 'Evento escolar' },
]

const COM_PUBLICOS = [
  { value: 'professores', label: 'Professores' },
  { value: 'toda_instituicao', label: 'Toda a instituição' },
  { value: 'unidade', label: 'Unidade' },
]

function Modal({ title, open, onClose, children }) {
  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2 className="text-lg font-semibold text-ink">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-2.5 py-1 text-sm text-slate-600 hover:bg-slate-50"
          >
            Fechar
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
        {label}
      </span>
      {children}
    </label>
  )
}

const inputCls =
  'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100'

export default function SecretariaOperacional() {
  const { user } = useAuth()
  const [tab, setTab] = useState('unidades')
  const [feedback, setFeedback] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const [unidades, setUnidades] = useState([])
  const [periodos, setPeriodos] = useState([])
  const [disciplinas, setDisciplinas] = useState([])
  const [alocacoes, setAlocacoes] = useState([])
  const [professores, setProfessores] = useState([])
  const [loading, setLoading] = useState(true)

  const [modal, setModal] = useState(null) // unidades | periodos | disciplinas
  const [formUnidade, setFormUnidade] = useState({ nome: '', endereco: '' })
  const [formPeriodo, setFormPeriodo] = useState({
    nome: '',
    data_inicio: '',
    data_fim: '',
  })
  const [formDisc, setFormDisc] = useState({
    nome: '',
    ementa_macro: '',
    carga_horaria: '',
  })
  const [formAloc, setFormAloc] = useState({
    unidade_id: '',
    periodo_id: '',
    disciplina_id: '',
    professor_id: '',
  })
  const [comunicacoes, setComunicacoes] = useState([])
  const [formCom, setFormCom] = useState({
    titulo: '',
    descricao: '',
    tipo: 'reuniao_pedagogica',
    publico_alvo: 'professores',
    data_hora_inicio: '',
    data_hora_fim: '',
    unidade_id: '',
  })

  const loadAll = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [u, p, d, a, pr, co] = await Promise.all([
        fetch('/api/secretaria/unidades', { credentials: 'include' }),
        fetch('/api/secretaria/periodos', { credentials: 'include' }),
        fetch('/api/secretaria/disciplinas', { credentials: 'include' }),
        fetch('/api/secretaria/alocacoes', { credentials: 'include' }),
        fetch('/api/secretaria/professores', { credentials: 'include' }),
        fetch('/api/secretaria/comunicacoes', { credentials: 'include' }),
      ])
      const ju = await u.json().catch(() => ({}))
      const jp = await p.json().catch(() => ({}))
      const jd = await d.json().catch(() => ({}))
      const ja = await a.json().catch(() => ({}))
      const jpr = await pr.json().catch(() => ({}))
      const jco = await co.json().catch(() => ({}))
      if (!u.ok) throw new Error(ju.error || 'Falha ao carregar unidades')
      if (!p.ok) throw new Error(jp.error || 'Falha ao carregar períodos')
      if (!d.ok) throw new Error(jd.error || 'Falha ao carregar disciplinas')
      if (!a.ok) throw new Error(ja.error || 'Falha ao carregar alocações')
      if (!pr.ok) throw new Error(jpr.error || 'Falha ao carregar professores')
      setUnidades(ju.items || [])
      setPeriodos(jp.items || [])
      setDisciplinas(jd.items || [])
      setAlocacoes(ja.items || [])
      setProfessores(jpr.items || [])
      setComunicacoes(co.ok ? jco.items || [] : [])
    } catch (err) {
      setError(err.message || 'Erro ao carregar Secretaria Acadêmica')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  async function postJson(url, body) {
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.error || 'Falha ao salvar')
    return data
  }

  async function handleCreateUnidade(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await postJson('/api/secretaria/unidades', formUnidade)
      setFormUnidade({ nome: '', endereco: '' })
      setModal(null)
      setFeedback('Unidade cadastrada.')
      await loadAll()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleCreatePeriodo(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await postJson('/api/secretaria/periodos', formPeriodo)
      setFormPeriodo({ nome: '', data_inicio: '', data_fim: '' })
      setModal(null)
      setFeedback('Período letivo cadastrado.')
      await loadAll()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleCreateDisc(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await postJson('/api/secretaria/disciplinas', {
        ...formDisc,
        carga_horaria: formDisc.carga_horaria
          ? Number(formDisc.carga_horaria)
          : null,
      })
      setFormDisc({ nome: '', ementa_macro: '', carga_horaria: '' })
      setModal(null)
      setFeedback('Disciplina cadastrada.')
      await loadAll()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleAlocar(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    setFeedback('')
    try {
      const data = await postJson('/api/secretaria/alocacoes', formAloc)
      setFeedback(
        data.message ||
          'Professor alocado com sucesso. Ambiente do professor já foi notificado.',
      )
      setFormAloc({
        unidade_id: '',
        periodo_id: '',
        disciplina_id: '',
        professor_id: '',
      })
      await loadAll()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleCreateComunicacao(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    setFeedback('')
    try {
      const data = await postJson('/api/secretaria/comunicacoes', {
        ...formCom,
        unidade_id: formCom.unidade_id || null,
        data_hora_fim: formCom.data_hora_fim || null,
        status: 'publicado',
      })
      setFeedback(data.message || 'Comunicado publicado no mural.')
      setFormCom({
        titulo: '',
        descricao: '',
        tipo: 'reuniao_pedagogica',
        publico_alvo: 'professores',
        data_hora_inicio: '',
        data_hora_fim: '',
        unidade_id: '',
      })
      await loadAll()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const escola = useMemo(
    () => user?.instituicao_nome || user?.nome || 'Instituição',
    [user],
  )

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Secretaria Acadêmica
        </h1>
        <p className="mt-1 text-sm text-muted">
          Unidades, períodos, disciplinas, alocação e mural de comunicações —{' '}
          {escola}. Publicações vão para o mural do professor no inove4us.
        </p>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => {
              setTab(t.id)
              setFeedback('')
              setError('')
            }}
            className={[
              'rounded-lg px-3 py-2 text-sm font-semibold transition',
              tab === t.id
                ? 'bg-school-500 text-white'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200',
            ].join(' ')}
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
        <section className="space-y-3">
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => setModal('unidades')}
              className="rounded-lg bg-school-500 px-4 py-2 text-sm font-semibold text-white hover:bg-school-600"
            >
              Novo
            </button>
          </div>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-muted">
                <tr>
                  <th className="px-4 py-3">Nome</th>
                  <th className="px-4 py-3">Endereço</th>
                </tr>
              </thead>
              <tbody>
                {unidades.length === 0 ? (
                  <tr>
                    <td colSpan={2} className="px-4 py-8 text-center text-muted">
                      Nenhuma unidade cadastrada.
                    </td>
                  </tr>
                ) : (
                  unidades.map((u) => (
                    <tr key={u.id} className="border-b border-slate-100 last:border-0">
                      <td className="px-4 py-3 font-medium text-ink">{u.nome}</td>
                      <td className="px-4 py-3 text-muted">{u.endereco || '—'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {!loading && tab === 'periodos' ? (
        <section className="space-y-3">
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => setModal('periodos')}
              className="rounded-lg bg-school-500 px-4 py-2 text-sm font-semibold text-white hover:bg-school-600"
            >
              Novo
            </button>
          </div>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-muted">
                <tr>
                  <th className="px-4 py-3">Nome</th>
                  <th className="px-4 py-3">Início</th>
                  <th className="px-4 py-3">Fim</th>
                </tr>
              </thead>
              <tbody>
                {periodos.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-4 py-8 text-center text-muted">
                      Nenhum período cadastrado.
                    </td>
                  </tr>
                ) : (
                  periodos.map((p) => (
                    <tr key={p.id} className="border-b border-slate-100 last:border-0">
                      <td className="px-4 py-3 font-medium text-ink">{p.nome}</td>
                      <td className="px-4 py-3 text-muted">{p.data_inicio || '—'}</td>
                      <td className="px-4 py-3 text-muted">{p.data_fim || '—'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {!loading && tab === 'disciplinas' ? (
        <section className="space-y-3">
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => setModal('disciplinas')}
              className="rounded-lg bg-school-500 px-4 py-2 text-sm font-semibold text-white hover:bg-school-600"
            >
              Novo
            </button>
          </div>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-muted">
                <tr>
                  <th className="px-4 py-3">Nome</th>
                  <th className="px-4 py-3">Carga horária</th>
                  <th className="px-4 py-3">Ementa</th>
                </tr>
              </thead>
              <tbody>
                {disciplinas.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-4 py-8 text-center text-muted">
                      Nenhuma disciplina cadastrada.
                    </td>
                  </tr>
                ) : (
                  disciplinas.map((d) => (
                    <tr key={d.id} className="border-b border-slate-100 last:border-0">
                      <td className="px-4 py-3 font-medium text-ink">{d.nome}</td>
                      <td className="px-4 py-3 text-muted">
                        {d.carga_horaria != null ? `${d.carga_horaria} h` : '—'}
                      </td>
                      <td className="px-4 py-3 text-muted line-clamp-2 max-w-md">
                        {d.ementa_macro || '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {!loading && tab === 'alocacao' ? (
        <section className="space-y-4">
          <form
            onSubmit={handleAlocar}
            className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-panel sm:grid-cols-2"
          >
            <Field label="Unidade">
              <select
                className={inputCls}
                required
                value={formAloc.unidade_id}
                onChange={(e) =>
                  setFormAloc((f) => ({ ...f, unidade_id: e.target.value }))
                }
              >
                <option value="">Selecionar unidade</option>
                {unidades.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.nome}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Período">
              <select
                className={inputCls}
                required
                value={formAloc.periodo_id}
                onChange={(e) =>
                  setFormAloc((f) => ({ ...f, periodo_id: e.target.value }))
                }
              >
                <option value="">Selecionar período</option>
                {periodos.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.nome}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Disciplina">
              <select
                className={inputCls}
                required
                value={formAloc.disciplina_id}
                onChange={(e) =>
                  setFormAloc((f) => ({ ...f, disciplina_id: e.target.value }))
                }
              >
                <option value="">Selecionar disciplina</option>
                {disciplinas.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.nome}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Professor da equipe">
              <select
                className={inputCls}
                required
                value={formAloc.professor_id}
                onChange={(e) =>
                  setFormAloc((f) => ({ ...f, professor_id: e.target.value }))
                }
              >
                <option value="">Selecionar professor</option>
                {professores.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label} ({p.status})
                  </option>
                ))}
              </select>
            </Field>
            <div className="sm:col-span-2">
              <button
                type="submit"
                disabled={busy}
                className="rounded-lg bg-school-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-school-600 disabled:opacity-60"
              >
                {busy ? 'Alocando…' : 'Alocar'}
              </button>
            </div>
          </form>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-muted">
                <tr>
                  <th className="px-4 py-3">Unidade</th>
                  <th className="px-4 py-3">Período</th>
                  <th className="px-4 py-3">Disciplina</th>
                  <th className="px-4 py-3">Professor</th>
                  <th className="px-4 py-3">B2C</th>
                </tr>
              </thead>
              <tbody>
                {alocacoes.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-muted">
                      Nenhuma alocação ainda.
                    </td>
                  </tr>
                ) : (
                  alocacoes.map((a) => (
                    <tr key={a.id} className="border-b border-slate-100 last:border-0">
                      <td className="px-4 py-3">{a.unidade_nome}</td>
                      <td className="px-4 py-3">{a.periodo_nome}</td>
                      <td className="px-4 py-3">{a.disciplina_nome}</td>
                      <td className="px-4 py-3">{a.professor_email || a.professor_id}</td>
                      <td className="px-4 py-3">
                        {a.notificado_b2c ? (
                          <span className="text-xs font-semibold text-school-700">
                            Notificado
                          </span>
                        ) : (
                          <span className="text-xs text-amber-700">Pendente</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {!loading && tab === 'comunicacoes' ? (
        <section className="space-y-4">
          <p className="text-sm text-muted">
            Publique avisos e eventos no mural da página inicial logada do
            inove4us (professores vinculados).
          </p>
          <form
            onSubmit={handleCreateComunicacao}
            className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-panel sm:grid-cols-2"
          >
            <Field label="Título">
              <input
                required
                className={inputCls}
                value={formCom.titulo}
                onChange={(e) => setFormCom({ ...formCom, titulo: e.target.value })}
              />
            </Field>
            <Field label="Tipo">
              <select
                className={inputCls}
                value={formCom.tipo}
                onChange={(e) => setFormCom({ ...formCom, tipo: e.target.value })}
              >
                {COM_TIPOS.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </Field>
            <label className="block text-sm sm:col-span-2">
              <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
                Descrição
              </span>
              <textarea
                rows={3}
                className={inputCls}
                value={formCom.descricao}
                onChange={(e) => setFormCom({ ...formCom, descricao: e.target.value })}
              />
            </label>
            <Field label="Público">
              <select
                className={inputCls}
                value={formCom.publico_alvo}
                onChange={(e) =>
                  setFormCom({ ...formCom, publico_alvo: e.target.value })
                }
              >
                {COM_PUBLICOS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </Field>
            {formCom.publico_alvo === 'unidade' ? (
              <Field label="Unidade">
                <select
                  required
                  className={inputCls}
                  value={formCom.unidade_id}
                  onChange={(e) =>
                    setFormCom({ ...formCom, unidade_id: e.target.value })
                  }
                >
                  <option value="">Selecione…</option>
                  {unidades.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.nome}
                    </option>
                  ))}
                </select>
              </Field>
            ) : (
              <div />
            )}
            <Field label="Início">
              <input
                required
                type="datetime-local"
                className={inputCls}
                value={formCom.data_hora_inicio}
                onChange={(e) =>
                  setFormCom({ ...formCom, data_hora_inicio: e.target.value })
                }
              />
            </Field>
            <Field label="Fim (opcional)">
              <input
                type="datetime-local"
                className={inputCls}
                value={formCom.data_hora_fim}
                onChange={(e) =>
                  setFormCom({ ...formCom, data_hora_fim: e.target.value })
                }
              />
            </Field>
            <div className="sm:col-span-2">
              <button
                type="submit"
                disabled={busy}
                className="rounded-lg bg-school-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-school-600 disabled:opacity-60"
              >
                {busy ? 'Publicando…' : 'Publicar no mural'}
              </button>
            </div>
          </form>

          <ul className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
            {comunicacoes.length === 0 ? (
              <li className="px-4 py-8 text-center text-sm text-muted">
                Nenhum comunicado ainda.
              </li>
            ) : (
              comunicacoes.map((item) => (
                <li key={item.id} className="px-4 py-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="font-medium text-ink">{item.titulo}</p>
                      <p className="text-xs text-muted">
                        {item.tipo_label} · {item.publico_label} ·{' '}
                        {item.status_label}
                        {item.replicado_b2c ? ' · No mural B2C' : ''}
                      </p>
                      {item.descricao ? (
                        <p className="mt-1 text-sm text-muted">{item.descricao}</p>
                      ) : null}
                    </div>
                    <p className="text-xs text-muted">
                      {item.data_hora_inicio
                        ? new Date(item.data_hora_inicio).toLocaleString('pt-BR')
                        : '—'}
                    </p>
                  </div>
                </li>
              ))
            )}
          </ul>
        </section>
      ) : null}

      <Modal
        title="Nova unidade"
        open={modal === 'unidades'}
        onClose={() => setModal(null)}
      >
        <form onSubmit={handleCreateUnidade} className="space-y-3">
          <Field label="Nome">
            <input
              className={inputCls}
              required
              value={formUnidade.nome}
              onChange={(e) =>
                setFormUnidade((f) => ({ ...f, nome: e.target.value }))
              }
            />
          </Field>
          <Field label="Endereço">
            <input
              className={inputCls}
              value={formUnidade.endereco}
              onChange={(e) =>
                setFormUnidade((f) => ({ ...f, endereco: e.target.value }))
              }
            />
          </Field>
          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-school-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            Salvar
          </button>
        </form>
      </Modal>

      <Modal
        title="Novo período letivo"
        open={modal === 'periodos'}
        onClose={() => setModal(null)}
      >
        <form onSubmit={handleCreatePeriodo} className="space-y-3">
          <Field label="Nome">
            <input
              className={inputCls}
              required
              value={formPeriodo.nome}
              onChange={(e) =>
                setFormPeriodo((f) => ({ ...f, nome: e.target.value }))
              }
            />
          </Field>
          <Field label="Data início">
            <input
              type="date"
              className={inputCls}
              required
              value={formPeriodo.data_inicio}
              onChange={(e) =>
                setFormPeriodo((f) => ({ ...f, data_inicio: e.target.value }))
              }
            />
          </Field>
          <Field label="Data fim">
            <input
              type="date"
              className={inputCls}
              required
              value={formPeriodo.data_fim}
              onChange={(e) =>
                setFormPeriodo((f) => ({ ...f, data_fim: e.target.value }))
              }
            />
          </Field>
          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-school-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            Salvar
          </button>
        </form>
      </Modal>

      <Modal
        title="Nova disciplina"
        open={modal === 'disciplinas'}
        onClose={() => setModal(null)}
      >
        <form onSubmit={handleCreateDisc} className="space-y-3">
          <Field label="Nome">
            <input
              className={inputCls}
              required
              value={formDisc.nome}
              onChange={(e) => setFormDisc((f) => ({ ...f, nome: e.target.value }))}
            />
          </Field>
          <Field label="Carga horária (horas)">
            <input
              type="number"
              min="0"
              step="0.5"
              className={inputCls}
              value={formDisc.carga_horaria}
              onChange={(e) =>
                setFormDisc((f) => ({ ...f, carga_horaria: e.target.value }))
              }
            />
          </Field>
          <Field label="Ementa macro">
            <textarea
              className={inputCls}
              rows={4}
              value={formDisc.ementa_macro}
              onChange={(e) =>
                setFormDisc((f) => ({ ...f, ementa_macro: e.target.value }))
              }
            />
          </Field>
          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-school-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            Salvar
          </button>
        </form>
      </Modal>
    </div>
  )
}
