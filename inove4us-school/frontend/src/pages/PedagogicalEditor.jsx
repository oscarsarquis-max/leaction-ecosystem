import { useEffect, useMemo, useState } from 'react'
import PeiEditorTab from './PeiEditorTab'

/** Interino até auth real — instituição de desenvolvimento. */
const INSTITUICAO_ID =
  import.meta.env.VITE_INSTITUICAO_ID || 'a1111111-1111-4111-8111-111111111111'

const PILARES = [
  { id: 'metodologias', label: 'Metodologias' },
  { id: 'pei', label: 'PEI' },
]

const FAMILIAS = ['Indutivas', 'Agilidade', 'Contextuais', 'Dedutivas']

const VETORES = {
  dia_a_dia: {
    id: 'dia_a_dia',
    nome: 'Dia a Dia',
    subtitulo: 'ciclo rápido',
    ajuda:
      'Aula de cerca de 50 minutos, com as 4 estações: Alinhamento, Entrega do dia, Atividade em campo e Retro do ciclo — o mesmo fluxo do professor no inove4us.',
    chip: 'bg-emerald-100 text-emerald-900',
    tab: 'border-emerald-500 text-emerald-800',
    tabIdle: 'border-transparent text-muted hover:text-ink',
    panel: 'border-emerald-200 bg-emerald-50/60',
  },
  desafio: {
    id: 'desafio',
    nome: 'Desafio',
    subtitulo: 'método inove4us',
    ajuda:
      'Projeto mais longo, com investigação, plano e acompanhamento na mesa (Para Fazer → Fazendo → Pronto) — o mesmo Desafio do professor no inove4us.',
    chip: 'bg-amber-100 text-amber-950',
    tab: 'border-amber-500 text-amber-900',
    tabIdle: 'border-transparent text-muted hover:text-ink',
    panel: 'border-amber-200 bg-amber-50/60',
  },
}

function FonteBadge({ fonte, adaptada }) {
  if (fonte === 'da_escola') {
    return (
      <span className="inline-flex items-center rounded-md bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-800">
        Criada pela escola
      </span>
    )
  }
  return (
    <span
      className={[
        'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold',
        adaptada ? 'bg-school-50 text-school-700' : 'bg-slate-100 text-slate-600',
      ].join(' ')}
    >
      {adaptada ? 'Adaptada pela escola' : 'Referência inove4us'}
    </span>
  )
}

function passosToLines(passos) {
  if (!Array.isArray(passos) || passos.length === 0) return ''
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

function linesToPassos(text) {
  return text
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
}

function RoteiroReferencia({ passos }) {
  if (!Array.isArray(passos) || passos.length === 0) {
    return (
      <p className="text-xs text-slate-500">Roteiro de referência ainda sem etapas.</p>
    )
  }
  return (
    <ol className="mt-2 list-decimal space-y-2 pl-5 text-sm text-ink">
      {passos.map((p, idx) => {
        if (typeof p === 'string') {
          return (
            <li key={idx} className="leading-snug">
              {p}
            </li>
          )
        }
        return (
          <li key={idx} className="leading-snug">
            <span className="font-semibold">{p.titulo || `Etapa ${idx + 1}`}</span>
            {p.objetivo ? <span className="block text-muted">{p.objetivo}</span> : null}
            {(p.mecanica_passo_a_passo || p.como_executar_detalhado) ? (
              <span className="block text-muted">
                {p.mecanica_passo_a_passo || p.como_executar_detalhado}
              </span>
            ) : null}
          </li>
        )
      })}
    </ol>
  )
}

/**
 * Caixa de entrada bottom-up: adaptações do professor pendentes de curadoria.
 */
function SugestoesTrincheira({ metodologiaNome, onToast }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError('')
      try {
        const q = encodeURIComponent(metodologiaNome || '')
        const res = await fetch(
          `/api/pedagogico/curadoria/pendentes?metodologia_nome=${q}`,
          { credentials: 'include' },
        )
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(body.error || 'Falha ao carregar sugestões')
        if (!cancelled) setItems(body.items || [])
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Erro ao carregar curadoria')
          setItems([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [metodologiaNome])

  async function agir(id, acao) {
    setBusyId(id)
    setError('')
    try {
      const res = await fetch(`/api/pedagogico/curadoria/${id}/${acao}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível concluir a ação')
      setItems((prev) => prev.filter((it) => it.id !== id))
      onToast?.(
        body.message ||
          (acao === 'incorporar'
            ? 'Sugestão incorporada à metodologia da escola.'
            : 'Sugestão mantida apenas na aula.'),
      )
    } catch (err) {
      setError(err.message || 'Erro na curadoria')
    } finally {
      setBusyId(null)
    }
  }

  if (loading) {
    return (
      <div className="mt-4 rounded-lg border border-dashed border-amber-200 bg-amber-50/40 p-3 text-xs text-amber-900">
        Carregando sugestões da trincheira…
      </div>
    )
  }

  if (!items.length && !error) return null

  return (
    <section className="mt-4 space-y-3 rounded-lg border border-amber-200 bg-amber-50/50 p-3">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-amber-900">
          Sugestões da Trincheira (Pendentes)
        </p>
        <p className="mt-0.5 text-xs text-amber-800/80">
          Adaptações enviadas pelos professores ao concluir a aula.
        </p>
      </div>
      {error ? (
        <p className="text-xs font-semibold text-red-700" role="alert">
          {error}
        </p>
      ) : null}
      <ul className="space-y-3">
        {items.map((item) => (
          <li
            key={item.id}
            className="rounded-lg border border-amber-100 bg-white p-3 shadow-sm"
          >
            <p className="text-sm leading-relaxed text-ink">
              {item.teacher_adaptation_text ||
                '— (sem texto; revise o payload da aula)'}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                disabled={busyId === item.id}
                onClick={() => agir(item.id, 'incorporar')}
                className="rounded-lg bg-school-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-school-600 disabled:opacity-60"
              >
                {busyId === item.id ? '…' : 'Incorporar à Metodologia da Escola'}
              </button>
              <button
                type="button"
                disabled={busyId === item.id}
                onClick={() => agir(item.id, 'rejeitar')}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
              >
                Manter apenas na aula atual
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}

const emptyCreate = {
  nome: '',
  familia: 'Indutivas',
  descricao: '',
  passos: '',
  disponivel_dia_a_dia: true,
  disponivel_desafio: true,
}

export default function PedagogicalEditor() {
  const [pilar, setPilar] = useState('metodologias')
  const [items, setItems] = useState([])
  const [drafts, setDrafts] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')
  const [savingId, setSavingId] = useState(null)
  const [filtro, setFiltro] = useState('')
  const [familiaFiltro, setFamiliaFiltro] = useState('Todas')
  const [vetorAtivo, setVetorAtivo] = useState('dia_a_dia')
  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState(emptyCreate)
  const [creating, setCreating] = useState(false)

  function applyList(data) {
    setItems(data)
    const next = {}
    for (const row of data) {
      const id = row.metodologia_id || row.metodologia_catalogo_id
      next[id] = {
        orientacao: row.orientacao_coordenacao ?? row.diretriz_customizada ?? '',
        is_active: row.is_active,
        roteiro_adaptado: passosToLines(row.roteiro_adaptado ?? row.passos_customizados),
        disponivel_dia_a_dia: row.disponivel_dia_a_dia !== false,
        disponivel_desafio: row.disponivel_desafio !== false,
      }
    }
    setDrafts(next)
  }

  async function load() {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`/api/instituicoes/${INSTITUICAO_ID}/metodologias`)
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.error || `Não foi possível carregar as metodologias`)
      }
      applyList(await res.json())
    } catch (err) {
      setError(err.message || 'Erro ao carregar metodologias')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError('')
      try {
        const res = await fetch(`/api/instituicoes/${INSTITUICAO_ID}/metodologias`)
        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          throw new Error(body.error || 'Não foi possível carregar as metodologias')
        }
        const data = await res.json()
        if (!cancelled) applyList(data)
      } catch (err) {
        if (!cancelled) setError(err.message || 'Erro ao carregar metodologias')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const filtered = useMemo(() => {
    const q = filtro.trim().toLowerCase()
    return items.filter((row) => {
      const familia = row.familia || row.categoria
      if (familiaFiltro !== 'Todas' && familia !== familiaFiltro) return false
      if (vetorAtivo === 'dia_a_dia' && row.vetores && row.vetores.dia_a_dia === false) {
        return false
      }
      if (vetorAtivo === 'desafio' && row.vetores && row.vetores.desafio === false) {
        return false
      }
      if (!q) return true
      return (
        row.nome.toLowerCase().includes(q) ||
        (row.descricao || '').toLowerCase().includes(q)
      )
    })
  }, [items, filtro, familiaFiltro, vetorAtivo])

  const grouped = useMemo(() => {
    const map = new Map()
    for (const row of filtered) {
      const fam = row.familia || row.categoria || 'Outras'
      if (!map.has(fam)) map.set(fam, [])
      map.get(fam).push(row)
    }
    return FAMILIAS.filter((c) => map.has(c)).map((c) => [c, map.get(c)])
  }, [filtered])

  const vetor = VETORES[vetorAtivo]

  function patchDraft(id, patch) {
    setDrafts((prev) => ({
      ...prev,
      [id]: { ...prev[id], ...patch },
    }))
  }

  async function handleSave(id) {
    const draft = drafts[id]
    if (!draft) return
    setSavingId(id)
    setFeedback('')
    setError('')
    try {
      const lines = linesToPassos(draft.roteiro_adaptado || '')
      const payload = {
        orientacao_coordenacao: draft.orientacao.trim() || null,
        is_active: draft.is_active,
        roteiro_adaptado: lines.length ? lines : null,
        disponivel_dia_a_dia: draft.disponivel_dia_a_dia,
        disponivel_desafio: draft.disponivel_desafio,
      }
      const res = await fetch(
        `/api/instituicoes/${INSTITUICAO_ID}/metodologias/${id}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        },
      )
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível salvar')

      const mid = body.metodologia_id || body.metodologia_catalogo_id
      setItems((prev) =>
        prev.map((row) => {
          const rid = row.metodologia_id || row.metodologia_catalogo_id
          return rid === mid ? body : row
        }),
      )
      setDrafts((prev) => ({
        ...prev,
        [id]: {
          orientacao: body.orientacao_coordenacao ?? body.diretriz_customizada ?? '',
          is_active: body.is_active,
          roteiro_adaptado: passosToLines(
            body.roteiro_adaptado ?? body.passos_customizados,
          ),
          disponivel_dia_a_dia: body.disponivel_dia_a_dia !== false,
          disponivel_desafio: body.disponivel_desafio !== false,
        },
      }))
      setFeedback(`“${body.nome}” atualizada para a escola.`)
    } catch (err) {
      setError(err.message || 'Erro ao salvar')
    } finally {
      setSavingId(null)
    }
  }

  async function handleCreate(e) {
    e.preventDefault()
    setCreating(true)
    setFeedback('')
    setError('')
    try {
      const passos = linesToPassos(createForm.passos)
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
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">
            Editor Pedagógico
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            {pilar === 'pei'
              ? 'Pilar 2 — planos gerais de PEI por tipo de neurodivergência.'
              : 'Pilar 1 — roteiro de referência do inove4us. A escola libera no Dia a Dia e no Desafio, adapta se precisar e deixa a orientação da coordenação.'}
          </p>
        </div>
        {pilar === 'metodologias' ? (
          <button
            type="button"
            onClick={() => setCreateOpen((v) => !v)}
            className="shrink-0 rounded-lg bg-school-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-school-600"
          >
            {createOpen ? 'Fechar formulário' : 'Criar metodologia da escola'}
          </button>
        ) : null}
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
        <>
      <div className="flex gap-2 border-b border-slate-200">
        {Object.values(VETORES).map((v) => {
          const active = vetorAtivo === v.id
          return (
            <button
              key={v.id}
              type="button"
              onClick={() => setVetorAtivo(v.id)}
              className={[
                '-mb-px border-b-2 px-3 py-2.5 text-left text-sm font-semibold transition',
                active ? v.tab : v.tabIdle,
              ].join(' ')}
            >
              <span className="block">{v.nome}</span>
              <span className="block text-xs font-normal opacity-80">{v.subtitulo}</span>
            </button>
          )
        })}
      </div>

      <div className={['rounded-xl border p-4 text-sm', vetor.panel].join(' ')}>
        <p className="font-semibold text-ink">
          {vetor.nome} · {vetor.subtitulo}
        </p>
        <p className="mt-1 text-muted">{vetor.ajuda}</p>
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
                onChange={(e) => setCreateForm((f) => ({ ...f, nome: e.target.value }))}
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
              onChange={(e) => setCreateForm((f) => ({ ...f, passos: e.target.value }))}
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
              Disponível no Dia a Dia
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
              Disponível no Desafio
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
          placeholder="Buscar metodologia…"
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

      {!loading && !error ? (
        <p className="text-xs text-muted">
          {filtered.length} metodologia(s) em {vetor.nome} · {items.length} no repertório
          da escola
        </p>
      ) : null}

      <div className="space-y-8">
        {grouped.map(([fam, rows]) => (
          <section key={fam} className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
              Família {fam}
            </h2>
            {rows.map((row) => {
              const id = row.metodologia_id || row.metodologia_catalogo_id
              const draft = drafts[id] || {
                orientacao: '',
                is_active: true,
                roteiro_adaptado: '',
                disponivel_dia_a_dia: true,
                disponivel_desafio: true,
              }
              const saving = savingId === id
              const noVetorAtual =
                vetorAtivo === 'dia_a_dia'
                  ? !draft.disponivel_dia_a_dia
                  : !draft.disponivel_desafio
              return (
                <article
                  key={id}
                  className={[
                    'rounded-xl border bg-white p-4 shadow-panel sm:p-5',
                    noVetorAtual ? 'border-slate-200 opacity-75' : 'border-slate-200',
                  ].join(' ')}
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-lg font-semibold text-ink">{row.nome}</h3>
                        <FonteBadge
                          fonte={row.fonte}
                          adaptada={Boolean(row.adaptada_pela_escola)}
                        />
                        <span className={['rounded-md px-2 py-0.5 text-xs font-semibold', VETORES.dia_a_dia.chip].join(' ')}>
                          Dia a Dia
                        </span>
                        <span className={['rounded-md px-2 py-0.5 text-xs font-semibold', VETORES.desafio.chip].join(' ')}>
                          Desafio
                        </span>
                      </div>
                      <p className="text-sm text-muted">{row.descricao || '—'}</p>
                    </div>
                    <label className="inline-flex shrink-0 items-center gap-2 text-sm text-ink">
                      <input
                        type="checkbox"
                        checked={draft.is_active}
                        onChange={(e) =>
                          patchDraft(id, { is_active: e.target.checked })
                        }
                        className="h-4 w-4 rounded border-slate-300 text-school-600 focus:ring-school-500"
                      />
                      Ativa na escola
                    </label>
                  </div>

                  <div className="mt-4 flex flex-col gap-2 rounded-lg border border-slate-100 bg-slate-50/80 p-3 sm:flex-row sm:gap-6">
                    <label className="inline-flex items-center gap-2 text-sm text-ink">
                      <input
                        type="checkbox"
                        checked={draft.disponivel_dia_a_dia}
                        onChange={(e) =>
                          patchDraft(id, { disponivel_dia_a_dia: e.target.checked })
                        }
                        className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                      />
                      Liberada no Dia a Dia
                    </label>
                    <label className="inline-flex items-center gap-2 text-sm text-ink">
                      <input
                        type="checkbox"
                        checked={draft.disponivel_desafio}
                        onChange={(e) =>
                          patchDraft(id, { disponivel_desafio: e.target.checked })
                        }
                        className="h-4 w-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
                      />
                      Liberada no Desafio
                    </label>
                  </div>

                  <div className="mt-4 rounded-lg border border-slate-100 bg-slate-50/80 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                      Roteiro de referência inove4us
                      {row.fonte !== 'da_escola' ? ' (não editável aqui)' : ''}
                    </p>
                    <RoteiroReferencia
                      passos={row.roteiro_referencia || row.passos_execucao}
                    />
                  </div>

                  <SugestoesTrincheira
                    metodologiaNome={row.nome}
                    onToast={(msg) => setFeedback(msg)}
                  />

                  <label className="mt-4 block">
                    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
                      Adaptação da escola (uma etapa por linha; vazio = usa a referência)
                    </span>
                    <textarea
                      value={draft.roteiro_adaptado}
                      onChange={(e) =>
                        patchDraft(id, { roteiro_adaptado: e.target.value })
                      }
                      rows={4}
                      placeholder="Deixe em branco para manter o roteiro de referência"
                      className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-ink outline-none transition placeholder:text-slate-400 focus:border-school-500 focus:ring-2 focus:ring-school-100"
                    />
                  </label>

                  <label className="mt-4 block">
                    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
                      Orientação da coordenação
                    </span>
                    <textarea
                      value={draft.orientacao}
                      onChange={(e) => patchDraft(id, { orientacao: e.target.value })}
                      rows={2}
                      placeholder="Como a escola quer que os professores usem esta metodologia"
                      className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-ink outline-none transition placeholder:text-slate-400 focus:border-school-500 focus:ring-2 focus:ring-school-100"
                    />
                  </label>

                  <div className="mt-3 flex justify-end">
                    <button
                      type="button"
                      disabled={saving}
                      onClick={() => handleSave(id)}
                      className="rounded-lg bg-school-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-school-600 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {saving ? 'Salvando…' : 'Salvar para a escola'}
                    </button>
                  </div>
                </article>
              )
            })}
          </section>
        ))}
      </div>
        </>
      ) : null}
    </div>
  )
}
