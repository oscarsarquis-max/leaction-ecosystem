import { useCallback, useEffect, useMemo, useState } from 'react'
import PeiEditorTab from './PeiEditorTab'

/** Interino até auth real — instituição de desenvolvimento. */
const INSTITUICAO_ID =
  import.meta.env.VITE_INSTITUICAO_ID || 'a1111111-1111-4111-8111-111111111111'

const PILARES = [
  { id: 'metodologias', label: 'Metodologias' },
  { id: 'pei', label: 'AEE e PEI (Inclusão)' },
]

const FAMILIAS = ['Indutivas', 'Agilidade', 'Contextuais', 'Dedutivas']

function EstrelasUso({ value }) {
  const n = Math.max(0, Math.min(3, Number(value) || 0))
  if (n === 0) {
    return (
      <span
        className="inline-flex items-center gap-0.5 text-slate-300"
        title="Ainda sem sugestões de professores"
        aria-label="Sem estrelas de uso"
      >
        <span aria-hidden>☆☆☆</span>
      </span>
    )
  }
  return (
    <span
      className="inline-flex items-center gap-0.5 text-amber-500"
      title={`${n} de 3 — engajamento dos professores`}
      aria-label={`${n} de 3 estrelas de uso`}
    >
      {[1, 2, 3].map((i) => (
        <span key={i} className={i <= n ? 'opacity-100' : 'opacity-25'} aria-hidden>
          ★
        </span>
      ))}
    </span>
  )
}

function iniciaisNome(nome) {
  const parts = String(nome || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
  if (!parts.length) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
}

function rotuloProfessor(nome) {
  const raw = String(nome || '').trim()
  if (!raw) return 'Professor(a)'
  if (/^prof\.?\s/i.test(raw)) return raw
  return `Prof. ${raw}`
}

/**
 * Card rico de sugestão do professor (curadoria).
 */
function SugestaoCard({ item, busy, onAdaptar }) {
  const texto =
    item.teacher_adaptation_text || item.texto || '— (sem texto)'
  const professor = rotuloProfessor(item.professor_nome)
  const contexto =
    item.aula_contexto ||
    item.sugestao_professor_json?.aula_contexto ||
    'Aula sem contexto informado'

  return (
    <article className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <header className="flex items-center gap-3 border-b border-slate-100 px-3 py-2.5">
        <span
          className="flex size-9 shrink-0 items-center justify-center rounded-full bg-school-100 text-xs font-bold text-school-800"
          aria-hidden
        >
          {iniciaisNome(item.professor_nome || 'P')}
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-ink">{professor}</p>
          <p className="truncate text-xs text-slate-500">Aula: {contexto}</p>
        </div>
      </header>
      <div className="bg-slate-50/80 px-3 py-3">
        <p className="text-sm italic leading-relaxed text-slate-700">
          &ldquo;{texto}&rdquo;
        </p>
      </div>
      <footer className="border-t border-slate-100 px-3 py-2.5">
        <button
          type="button"
          disabled={busy}
          onClick={() => onAdaptar(item)}
          className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-school-500 px-3 py-2.5 text-sm font-bold text-white shadow-sm transition hover:opacity-95 disabled:opacity-60"
        >
          {busy ? 'Adaptando…' : '🤖 Adaptar com IA'}
        </button>
      </footer>
    </article>
  )
}

function textoCanonico(row) {
  if (row.texto_canonico) return String(row.texto_canonico)
  const passos = row.roteiro_referencia || row.passos_execucao || []
  if (!Array.isArray(passos)) return String(passos || '')
  return passos
    .map((p) => {
      if (typeof p === 'string') return p
      const titulo = (p.titulo || '').trim()
      const mec = (p.mecanica_passo_a_passo || p.como_executar_detalhado || '').trim()
      if (titulo && mec && titulo !== mec) return `${titulo}: ${mec}`
      return titulo || mec
    })
    .filter(Boolean)
    .join('\n')
}

function descricaoCurta(row) {
  const d = String(row.descricao || '').trim()
  if (d) return d
  const canon = textoCanonico(row)
  if (!canon) return 'Sem descrição.'
  const line = canon.split('\n').find((l) => l.trim()) || ''
  return line.length > 140 ? `${line.slice(0, 137)}…` : line
}

const emptyCreate = {
  nome: '',
  familia: 'Indutivas',
  descricao: '',
  passos: '',
  disponivel_dia_a_dia: true,
  disponivel_desafio: true,
}

/**
 * Painel expandido: canônico + sugestões + Versão da Escola (IA).
 */
function AccordionBody({ row, draft, onDraft, onSaved, onToast }) {
  const id = row.metodologia_id || row.metodologia_catalogo_id
  const canon = textoCanonico(row)
  const [sugestoes, setSugestoes] = useState([])
  const [loadingSug, setLoadingSug] = useState(true)
  const [busyId, setBusyId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoadingSug(true)
      setErr('')
      try {
        const q = encodeURIComponent(row.nome || '')
        const res = await fetch(
          `/api/pedagogico/curadoria/pendentes?metodologia_nome=${q}`,
          { credentials: 'include' },
        )
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(body.error || 'Falha ao carregar sugestões')
        if (!cancelled) setSugestoes(body.items || [])
      } catch (e) {
        if (!cancelled) {
          setErr(e.message || 'Erro ao carregar sugestões')
          setSugestoes([])
        }
      } finally {
        if (!cancelled) setLoadingSug(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [row.nome])

  async function adaptarComIa(item) {
    setBusyId(item.id)
    setErr('')
    try {
      const textoSug =
        item.teacher_adaptation_text || item.texto || ''
      const res = await fetch(`/api/pedagogico/metodologia/${id}/adaptar-ia`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          instituicao_id: INSTITUICAO_ID,
          texto_canonico: canon,
          sugestao: textoSug,
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha na adaptação com IA')
      onDraft({ versao_escola: body.versao_escola || '' })
      onToast?.('Rascunho gerado pela IA — revise e salve a versão da instituição.')
    } catch (e) {
      setErr(e.message || 'Erro na IA')
    } finally {
      setBusyId(null)
    }
  }

  async function salvarVersao() {
    setSaving(true)
    setErr('')
    try {
      const res = await fetch(
        `/api/instituicoes/${INSTITUICAO_ID}/metodologias/${id}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            versao_escola: (draft.versao_escola || '').trim() || null,
            disponivel_dia_a_dia: draft.disponivel_dia_a_dia,
            disponivel_desafio: draft.disponivel_desafio,
          }),
        },
      )
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível salvar')
      onSaved?.(body)
      onToast?.(`Versão da instituição salva para “${body.nome}”.`)
    } catch (e) {
      setErr(e.message || 'Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="border-t border-slate-100 bg-white px-4 py-4 sm:px-5">
      <div className="grid gap-4 lg:grid-cols-[1fr_minmax(17rem,24rem)]">
        <div className="space-y-4">
          <section className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">
              Texto canônico (somente leitura)
            </p>
            <pre className="mt-2 whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink">
              {canon || '—'}
            </pre>
          </section>

          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
              Versão da Escola
            </span>
            <textarea
              value={draft.versao_escola || ''}
              onChange={(e) => onDraft({ versao_escola: e.target.value })}
              rows={10}
              placeholder="Texto unificado da instituição — gere com IA a partir de uma sugestão ou escreva manualmente."
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-ink outline-none transition placeholder:text-slate-400 focus:border-school-500 focus:ring-2 focus:ring-school-100"
            />
          </label>

          <div className="flex justify-end">
            <button
              type="button"
              disabled={saving}
              onClick={() => void salvarVersao()}
              className="rounded-lg bg-school-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-school-600 disabled:opacity-60"
            >
              {saving ? 'Salvando…' : 'Salvar Versão da Instituição'}
            </button>
          </div>
        </div>

        <aside className="space-y-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">
              Sugestões dos Professores
            </p>
            <p className="mt-0.5 text-xs text-slate-500">
              Cada card traz o contexto da aula e o relato do professor.
            </p>
          </div>

          {loadingSug ? (
            <p className="text-xs text-muted">Carregando…</p>
          ) : null}

          {!loadingSug && !sugestoes.length ? (
            <p className="rounded-lg border border-dashed border-slate-200 px-3 py-6 text-center text-xs text-muted">
              Nenhuma sugestão pendente.
            </p>
          ) : null}

          <ul className="max-h-[28rem] space-y-3 overflow-y-auto pr-0.5">
            {sugestoes.map((item) => (
              <li key={item.id}>
                <SugestaoCard
                  item={item}
                  busy={busyId === item.id}
                  onAdaptar={(it) => void adaptarComIa(it)}
                />
              </li>
            ))}
          </ul>
        </aside>
      </div>

      {err ? (
        <p className="mt-3 text-sm font-medium text-red-700" role="alert">
          {err}
        </p>
      ) : null}
    </div>
  )
}

export default function PedagogicalEditor() {
  const [pilar, setPilar] = useState('metodologias')
  const [items, setItems] = useState([])
  const [drafts, setDrafts] = useState({})
  const [expandedId, setExpandedId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')
  const [filtro, setFiltro] = useState('')
  const [familiaFiltro, setFamiliaFiltro] = useState('Todas')
  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState(emptyCreate)
  const [creating, setCreating] = useState(false)
  const [togglingId, setTogglingId] = useState(null)

  const applyList = useCallback((data) => {
    setItems(data)
    const next = {}
    for (const row of data) {
      const id = row.metodologia_id || row.metodologia_catalogo_id
      next[id] = {
        versao_escola: row.versao_escola || row.passos_customizados || '',
        disponivel_dia_a_dia: row.disponivel_dia_a_dia !== false,
        disponivel_desafio: row.disponivel_desafio !== false,
        uso_estrelas: row.uso_estrelas || 1,
      }
    }
    setDrafts(next)
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`/api/instituicoes/${INSTITUICAO_ID}/metodologias`)
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.error || 'Não foi possível carregar as metodologias')
      }
      applyList(await res.json())
    } catch (err) {
      setError(err.message || 'Erro ao carregar metodologias')
    } finally {
      setLoading(false)
    }
  }, [applyList])

  useEffect(() => {
    void load()
  }, [load])

  const filtered = useMemo(() => {
    const q = filtro.trim().toLowerCase()
    return items.filter((row) => {
      const familia = row.familia || row.categoria
      if (familiaFiltro !== 'Todas' && familia !== familiaFiltro) return false
      if (!q) return true
      return (
        row.nome.toLowerCase().includes(q) ||
        (row.descricao || '').toLowerCase().includes(q)
      )
    })
  }, [items, filtro, familiaFiltro])

  function patchDraft(id, patch) {
    setDrafts((prev) => ({
      ...prev,
      [id]: { ...prev[id], ...patch },
    }))
  }

  async function toggleVetor(id, field, value) {
    patchDraft(id, { [field]: value })
    setTogglingId(id)
    setError('')
    try {
      const draft = { ...drafts[id], [field]: value }
      const res = await fetch(
        `/api/instituicoes/${INSTITUICAO_ID}/metodologias/${id}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            disponivel_dia_a_dia: draft.disponivel_dia_a_dia,
            disponivel_desafio: draft.disponivel_desafio,
          }),
        },
      )
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível atualizar')
      setItems((prev) =>
        prev.map((row) => {
          const rid = row.metodologia_id || row.metodologia_catalogo_id
          return rid === id ? body : row
        }),
      )
      patchDraft(id, {
        disponivel_dia_a_dia: body.disponivel_dia_a_dia !== false,
        disponivel_desafio: body.disponivel_desafio !== false,
        versao_escola: body.versao_escola || drafts[id]?.versao_escola || '',
        uso_estrelas: body.uso_estrelas || drafts[id]?.uso_estrelas || 1,
      })
    } catch (err) {
      // reverte
      patchDraft(id, { [field]: !value })
      setError(err.message || 'Erro ao salvar disponibilidade')
    } finally {
      setTogglingId(null)
    }
  }

  async function handleCreate(e) {
    e.preventDefault()
    setCreating(true)
    setFeedback('')
    setError('')
    try {
      const passos = createForm.passos
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean)
      if (!createForm.nome.trim()) throw new Error('Informe o nome da metodologia.')
      if (!passos.length) throw new Error('Inclua ao menos uma etapa no roteiro.')
      const res = await fetch(`/api/instituicoes/${INSTITUICAO_ID}/metodologias`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nome: createForm.nome.trim(),
          familia: createForm.familia,
          descricao: createForm.descricao.trim() || null,
          roteiro: passos,
          disponivel_dia_a_dia: createForm.disponivel_dia_a_dia,
          disponivel_desafio: createForm.disponivel_desafio,
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível criar a metodologia')
      setCreateForm(emptyCreate)
      setCreateOpen(false)
      setFeedback(`Metodologia “${body.nome}” criada pela escola.`)
      await load()
    } catch (err) {
      setError(err.message || 'Erro ao criar')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Editor Pedagógico
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-muted">
          {pilar === 'pei'
            ? 'Diretrizes AEE por condição, PEIs individuais e adaptações metodológicas na prática.'
            : 'Adapte as metodologias de referência à sua instituição e incorpore sugestões dos professores com apoio de IA.'}
        </p>
      </div>

      <div className="flex gap-2 border-b border-slate-200">
        {PILARES.map((p) => {
          const active = pilar === p.id
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => {
                setPilar(p.id)
                setError('')
                setFeedback('')
              }}
              className={[
                '-mb-px border-b-2 px-4 py-2.5 text-sm font-semibold transition',
                active
                  ? 'border-school-500 text-school-800'
                  : 'border-transparent text-muted hover:text-ink',
              ].join(' ')}
            >
              {p.label}
            </button>
          )
        })}
      </div>

      {pilar === 'pei' ? <PeiEditorTab /> : null}

      {pilar === 'metodologias' ? (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => setCreateOpen((v) => !v)}
              className="rounded-lg bg-school-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-school-600"
            >
              {createOpen ? 'Fechar formulário' : 'Criar Metodologia da Escola'}
            </button>
            {!loading ? (
              <p className="text-xs text-muted">
                {filtered.length} de {items.length} metodologia(s)
              </p>
            ) : null}
          </div>

          {createOpen ? (
            <form
              onSubmit={handleCreate}
              className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-panel"
            >
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
                Nova metodologia da escola
              </h2>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
                    Nome
                  </span>
                  <input
                    value={createForm.nome}
                    onChange={(e) =>
                      setCreateForm((f) => ({ ...f, nome: e.target.value }))
                    }
                    className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100"
                    required
                  />
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
                    Família
                  </span>
                  <select
                    value={createForm.familia}
                    onChange={(e) =>
                      setCreateForm((f) => ({ ...f, familia: e.target.value }))
                    }
                    className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100"
                  >
                    {FAMILIAS.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
                  Descrição
                </span>
                <input
                  value={createForm.descricao}
                  onChange={(e) =>
                    setCreateForm((f) => ({ ...f, descricao: e.target.value }))
                  }
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100"
                />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
                  Roteiro (uma etapa por linha)
                </span>
                <textarea
                  value={createForm.passos}
                  onChange={(e) =>
                    setCreateForm((f) => ({ ...f, passos: e.target.value }))
                  }
                  rows={4}
                  required
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100"
                />
              </label>
              <div className="flex flex-col gap-2 sm:flex-row sm:gap-6">
                <label className="inline-flex items-center gap-2 text-sm text-ink">
                  <input
                    type="checkbox"
                    checked={createForm.disponivel_dia_a_dia}
                    onChange={(e) =>
                      setCreateForm((f) => ({
                        ...f,
                        disponivel_dia_a_dia: e.target.checked,
                      }))
                    }
                    className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                  />
                  Habilitar no Dia a Dia
                </label>
                <label className="inline-flex items-center gap-2 text-sm text-ink">
                  <input
                    type="checkbox"
                    checked={createForm.disponivel_desafio}
                    onChange={(e) =>
                      setCreateForm((f) => ({
                        ...f,
                        disponivel_desafio: e.target.checked,
                      }))
                    }
                    className="h-4 w-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
                  />
                  Habilitar no Desafio
                </label>
              </div>
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={creating}
                  className="rounded-lg bg-school-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-school-600 disabled:opacity-60"
                >
                  {creating ? 'Criando…' : 'Criar metodologia'}
                </button>
              </div>
            </form>
          ) : null}

          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              type="search"
              value={filtro}
              onChange={(e) => setFiltro(e.target.value)}
              placeholder="Buscar metodologia pelo nome…"
              className="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100"
            />
            <select
              value={familiaFiltro}
              onChange={(e) => setFamiliaFiltro(e.target.value)}
              className="rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100"
            >
              <option value="Todas">Todas as famílias</option>
              {FAMILIAS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {loading ? (
            <p className="text-sm text-muted" role="status">
              Carregando metodologias…
            </p>
          ) : null}

          {error ? (
            <p className="text-sm text-red-700" role="alert">
              {error}
            </p>
          ) : null}

          {feedback ? (
            <p className="text-sm text-school-700" role="status">
              {feedback}
            </p>
          ) : null}

          <div className="space-y-2">
            {filtered.map((row) => {
              const id = row.metodologia_id || row.metodologia_catalogo_id
              const draft = drafts[id] || {
                versao_escola: '',
                disponivel_dia_a_dia: true,
                disponivel_desafio: true,
                uso_estrelas: 1,
              }
              const open = expandedId === id
              const busyToggle = togglingId === id

              return (
                <article
                  key={id}
                  className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
                >
                  <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-start sm:gap-4">
                    <button
                      type="button"
                      onClick={() => setExpandedId(open ? null : id)}
                      className="min-w-0 flex-1 text-left"
                      aria-expanded={open}
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className="text-slate-400"
                          aria-hidden
                        >
                          {open ? '▾' : '▸'}
                        </span>
                        <h3 className="text-base font-semibold text-ink">{row.nome}</h3>
                        <EstrelasUso value={row.uso_estrelas} />
                      </div>
                      <p className="mt-1 line-clamp-2 pl-5 text-sm text-muted">
                        {descricaoCurta(row)}
                      </p>
                    </button>

                    <div className="flex shrink-0 flex-col gap-2 pl-5 sm:pl-0">
                      <label className="inline-flex items-center gap-2 text-xs font-medium text-ink">
                        <input
                          type="checkbox"
                          disabled={busyToggle}
                          checked={draft.disponivel_dia_a_dia}
                          onChange={(e) =>
                            void toggleVetor(id, 'disponivel_dia_a_dia', e.target.checked)
                          }
                          className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                        />
                        Habilitar no Dia a Dia
                      </label>
                      <label className="inline-flex items-center gap-2 text-xs font-medium text-ink">
                        <input
                          type="checkbox"
                          disabled={busyToggle}
                          checked={draft.disponivel_desafio}
                          onChange={(e) =>
                            void toggleVetor(id, 'disponivel_desafio', e.target.checked)
                          }
                          className="h-4 w-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
                        />
                        Habilitar no Desafio
                      </label>
                    </div>
                  </div>

                  {open ? (
                    <AccordionBody
                      row={row}
                      draft={draft}
                      onDraft={(patch) => patchDraft(id, patch)}
                      onToast={setFeedback}
                      onSaved={(body) => {
                        setItems((prev) =>
                          prev.map((r) => {
                            const rid = r.metodologia_id || r.metodologia_catalogo_id
                            return rid === id ? body : r
                          }),
                        )
                        patchDraft(id, {
                          versao_escola: body.versao_escola || '',
                          disponivel_dia_a_dia: body.disponivel_dia_a_dia !== false,
                          disponivel_desafio: body.disponivel_desafio !== false,
                          uso_estrelas: body.uso_estrelas || 1,
                        })
                      }}
                    />
                  ) : null}
                </article>
              )
            })}
          </div>

          {!loading && !filtered.length ? (
            <p className="rounded-xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-muted">
              Nenhuma metodologia encontrada para este filtro.
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
