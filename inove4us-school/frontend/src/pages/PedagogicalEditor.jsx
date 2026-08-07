import { useCallback, useEffect, useMemo, useState } from 'react'
import PeiEditorTab from './PeiEditorTab'
import { tabClassName } from '../lib/tabs'
import { BTN_PRIMARY, BTN_PRIMARY_FULL, CHECKBOX_CLASS } from '../lib/buttons'

/** Interino até auth real — instituição de desenvolvimento. */
const INSTITUICAO_ID =
  import.meta.env.VITE_INSTITUICAO_ID || 'a1111111-1111-4111-8111-111111111111'

const PILARES = [
  { id: 'metodologias', label: 'Metodologias' },
  { id: 'pei', label: 'PEI (Adaptações)' },
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
 * Sinalizador: Incorporar → alimenta a síntese da versão da escola (IA).
 */
function SugestaoCard({ item, busy, incorporada, onIncorporar }) {
  const texto =
    item.teacher_adaptation_text || item.texto || '— (sem texto)'
  const professor = rotuloProfessor(item.professor_nome)
  const contexto =
    item.aula_contexto ||
    item.sugestao_professor_json?.aula_contexto ||
    'Aula sem contexto informado'

  return (
    <article
      className={[
        'overflow-hidden rounded-xl border bg-white shadow-sm',
        incorporada ? 'border-school-300 ring-1 ring-school-100' : 'border-slate-200',
      ].join(' ')}
    >
      <header className="flex items-center gap-3 border-b border-slate-100 px-3 py-2.5">
        <span
          className="flex size-9 shrink-0 items-center justify-center rounded-full bg-school-100 text-xs font-bold text-school-800"
          aria-hidden
        >
          {iniciaisNome(item.professor_nome || 'P')}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold text-ink">{professor}</p>
          <p className="truncate text-xs text-slate-500">Aula: {contexto}</p>
        </div>
        {incorporada ? (
          <span className="shrink-0 rounded-md bg-school-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-school-700">
            Incorporada
          </span>
        ) : null}
      </header>
      <div className="bg-slate-50/80 px-3 py-3">
        <p className="text-sm italic leading-relaxed text-slate-700">
          &ldquo;{texto}&rdquo;
        </p>
      </div>
      <footer className="border-t border-slate-100 px-3 py-2.5">
        <button
          type="button"
          disabled={busy || incorporada}
          onClick={() => onIncorporar(item)}
          className={[
            BTN_PRIMARY_FULL,
            incorporada ? 'bg-slate-400 hover:bg-slate-400' : '',
          ].join(' ')}
        >
          {busy ? 'Incorporando…' : incorporada ? 'Já incorporada' : 'Incorporar'}
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

/** Aceita só o roteiro unificado da IA — descarta blocos fragmentados legados. */
function limparRoteiroIntegrado(raw) {
  const text = String(raw || '').trim()
  if (!text) return ''
  const ban =
    /observações da coordenação|sugestões dos professores|texto integrado da escola\s*\(rascunho|\[canônico|\[observações|\[sugestões|dados de entrada:/i
  const lines = text.split('\n')
  const out = []
  let skipping = false
  for (const ln of lines) {
    const low = ln.trim().toLowerCase()
    if (ban.test(low) || /^—\s*.+\s*—\s*$/.test(ln.trim())) {
      skipping = true
      continue
    }
    if (skipping) {
      if (!ln.trim()) skipping = false
      continue
    }
    out.push(ln)
  }
  const cleaned = out.join('\n').trim()
  return cleaned || text
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

function formatDataModificacao(iso) {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) {
    const [y, m, day] = String(iso).slice(0, 10).split('-')
    if (y && m && day) return `${day}/${m}/${y}`
    return null
  }
  const dd = String(d.getDate()).padStart(2, '0')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const yyyy = d.getFullYear()
  return `${dd}/${mm}/${yyyy}`
}

function IconeCadeado({ className = 'h-4 w-4' }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden className={className}>
      <path
        d="M8 11V8a4 4 0 0 1 8 0v3"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <rect
        x="5"
        y="11"
        width="14"
        height="10"
        rx="2"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <circle cx="12" cy="16" r="1.4" fill="currentColor" />
    </svg>
  )
}

function ModalPadraoCanonico({ open, onClose, texto }) {
  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Padrão original inove4us"
      onClick={onClose}
    >
      <div
        className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-ink">Padrão Original inove4us</h2>
            <p className="mt-1 text-sm italic text-slate-500">
              Este é o modelo original mantido pelo inove4us. Ele não é alterado para
              garantir sua referência pedagógica.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
          >
            Fechar
          </button>
        </div>
        <pre className="flex-1 overflow-y-auto whitespace-pre-wrap bg-slate-50 px-5 py-4 font-sans text-sm leading-relaxed text-ink">
          {texto || '—'}
        </pre>
      </div>
    </div>
  )
}

/**
 * Painel expandido:
 * - Versão da Escola no lugar do canônico (padrão original só no modal)
 * - Coordenação + sugestões editáveis
 * - Toda composição parte do texto atual da escola
 */
function AccordionBody({ row, draft, onDraft, onSaved, onToast }) {
  const id = row.metodologia_id || row.metodologia_catalogo_id
  const canonCatalogo = textoCanonico(row)
  const isCustomizado = Boolean(row.is_customizado ?? draft.is_customizado)
  const dataMod = formatDataModificacao(row.updated_at || draft.updated_at)

  const [sugestoes, setSugestoes] = useState([])
  const [loadingSug, setLoadingSug] = useState(true)
  const [busyId, setBusyId] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')
  const [incorporadas, setIncorporadas] = useState([])
  const [modalCanon, setModalCanon] = useState(false)

  /** Base da IA = texto atual da escola (já nasce como canônico). */
  const baseComposicao = useMemo(
    () => (draft.versao_escola || '').trim() || canonCatalogo,
    [draft.versao_escola, canonCatalogo],
  )

  useEffect(() => {
    setIncorporadas([])
    setErr('')
    if (!(draft.versao_escola || '').trim() && canonCatalogo) {
      onDraft({ versao_escola: canonCatalogo })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- só ao trocar metodologia
  }, [id])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoadingSug(true)
      setSugestoes([])
      setIncorporadas([])
      try {
        const nomeMet = String(row.nome || '').trim()
        if (!nomeMet) {
          if (!cancelled) {
            setSugestoes([])
            setLoadingSug(false)
          }
          return
        }
        const q = encodeURIComponent(nomeMet)
        const res = await fetch(
          `/api/pedagogico/curadoria/pendentes?metodologia_nome=${q}`,
          { credentials: 'include' },
        )
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(body.error || 'Falha ao carregar sugestões')
        const items = Array.isArray(body.items) ? body.items : []
        // Só sugestões desta metodologia (filtro defensivo no cliente)
        const daMetodologia = items.filter((it) => {
          const nome =
            it.metodologia_nome ||
            it.metodologia_usada ||
            it.sugestao_professor_json?.metodologia_nome ||
            ''
          if (!String(nome).trim()) return true // API já filtrou por query
          return (
            String(nome).trim().toLowerCase() === nomeMet.toLowerCase()
          )
        })
        if (!cancelled) setSugestoes(daMetodologia)
      } catch (e) {
        if (!cancelled) {
          setSugestoes([])
          setErr(e.message || 'Não foi possível carregar as sugestões desta metodologia')
        }
      } finally {
        if (!cancelled) setLoadingSug(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [row.nome])

  async function incorporarSugestao(item) {
    if (incorporadas.some((s) => s.id === item.id)) return
    setBusyId(item.id)
    setErr('')
    try {
      if (!item.smoke && !String(item.id).startsWith('smoke-')) {
        const res = await fetch(`/api/pedagogico/curadoria/${item.id}/incorporar`, {
          method: 'POST',
          credentials: 'include',
        })
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(body.error || 'Falha ao incorporar sugestão')
      }
      setIncorporadas((prev) => [...prev, item])
      onToast?.(
        'Sugestão marcada. Use “Gerar metodologia integrada” para a IA compor o texto.',
      )
    } catch (e) {
      setErr(e.message || 'Erro ao incorporar')
    } finally {
      setBusyId(null)
    }
  }

  async function gerarMetodologiaIntegrada() {
    if (!incorporadas.length) {
      setErr('Incorpore ao menos uma sugestão de professor antes de gerar.')
      return
    }
    setGenerating(true)
    setErr('')
    try {
      const sugestoesTxt = incorporadas
        .map((s) => s.teacher_adaptation_text || s.texto || '')
        .map((t) => String(t).trim())
        .filter(Boolean)
      const res = await fetch(`/api/pedagogico/metodologia/${id}/adaptar-ia`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          instituicao_id: INSTITUICAO_ID,
          texto_canonico: baseComposicao,
          observacoes_coordenacao: (draft.observacoes_coordenacao || '').trim(),
          sugestoes: sugestoesTxt,
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha na síntese com IA')
      const texto = limparRoteiroIntegrado(body.versao_escola || '')
      if (!texto) throw new Error('A IA não retornou um roteiro utilizável')
      onDraft({ versao_escola: texto })
      onToast?.('Roteiro gerado. Revise e salve a versão da instituição.')
    } catch (e) {
      setErr(e.message || 'Erro ao gerar')
    } finally {
      setGenerating(false)
    }
  }

  async function salvarVersaoInstituicao() {
    const texto = (draft.versao_escola || '').trim()
    if (!texto) {
      setErr('Informe o texto da Versão da Escola antes de salvar.')
      return
    }
    setSaving(true)
    setErr('')
    try {
      const res = await fetch(
        `/api/instituicoes/${INSTITUICAO_ID}/metodologias/${id}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            versao_escola: texto,
            disponivel_dia_a_dia: draft.disponivel_dia_a_dia,
            disponivel_desafio: draft.disponivel_desafio,
          }),
        },
      )
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível salvar')
      onDraft({
        versao_escola: body.passos_customizados || body.versao_escola || texto,
        is_customizado: body.is_customizado !== false,
        updated_at: body.updated_at || new Date().toISOString(),
      })
      onSaved?.(body)
      onToast?.(`Versão da instituição salva para “${body.nome || row.nome}”.`)
    } catch (e) {
      setErr(e.message || 'Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  const idsIncorporados = useMemo(
    () => new Set(incorporadas.map((s) => s.id)),
    [incorporadas],
  )

  return (
    <div className="border-t border-slate-100 bg-white px-4 py-4 sm:px-5">
      <div className="space-y-4">
        {/* Onde era o canônico: Versão da Escola */}
        <section className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                  Versão da Escola
                </p>
                <button
                  type="button"
                  onClick={() => setModalCanon(true)}
                  className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] font-medium text-slate-600 transition hover:border-school-300 hover:bg-school-50 hover:text-school-700"
                >
                  <IconeCadeado className="h-3.5 w-3.5" />
                  Ver Padrão Original inove4us
                </button>
              </div>
              <p className="mt-0.5 text-[11px] text-slate-500">
                Texto oficial da metodologia nesta escola. O padrão original inove4us fica no
                cadeado ao lado.
              </p>
            </div>
            <p className="shrink-0 text-xs text-slate-500">
              {isCustomizado && dataMod
                ? `Última modificação: ${dataMod}`
                : 'Usando Padrão Inove4us'}
            </p>
          </div>
        </section>

        <label className="block">
          <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
            Observações da coordenação
          </span>
          <textarea
            value={draft.observacoes_coordenacao || ''}
            onChange={(e) => onDraft({ observacoes_coordenacao: e.target.value })}
            rows={3}
            placeholder="Orientações institucionais que devem entrar na síntese da versão da escola."
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-ink outline-none transition placeholder:text-slate-400 focus:border-school-500 focus:ring-2 focus:ring-school-100"
          />
        </label>

        <div className="grid gap-4 lg:grid-cols-[1fr_minmax(17rem,24rem)] lg:items-stretch">
          <div className="flex min-h-[22rem] flex-col">
            <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
              Texto integrado (editável)
            </span>
            <p className="mb-1.5 text-[11px] italic text-slate-500">
              Compose com IA a partir deste texto + coordenação + sugestões; depois revise e salve.
            </p>
            <textarea
              value={draft.versao_escola || ''}
              onChange={(e) => onDraft({ versao_escola: e.target.value })}
              rows={12}
              placeholder="Texto da escola — incorpore sugestões e gere a composição."
              className="min-h-0 w-full flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-ink outline-none transition placeholder:text-slate-400 focus:border-school-500 focus:ring-2 focus:ring-school-100"
            />
          </div>

          <aside className="flex min-h-[22rem] flex-col">
            <div className="mb-2 shrink-0">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                Sugestões dos Professores
              </p>
              <p className="mt-0.5 text-xs text-slate-500">
                Marque com Incorporar. Depois gere o texto integrado.
                {incorporadas.length
                  ? ` (${incorporadas.length} selecionada${incorporadas.length > 1 ? 's' : ''})`
                  : ''}
              </p>
            </div>

            {loadingSug ? (
              <p className="text-xs text-muted">Carregando…</p>
            ) : null}

            {!loadingSug && !sugestoes.length ? (
              <p className="rounded-lg border border-dashed border-slate-200 px-3 py-6 text-center text-xs text-muted">
                Nenhuma sugestão pendente para esta metodologia.
              </p>
            ) : null}

            <ul className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-0.5">
              {sugestoes.map((item) => (
                <li key={item.id}>
                  <SugestaoCard
                    item={item}
                    busy={busyId === item.id}
                    incorporada={idsIncorporados.has(item.id)}
                    onIncorporar={(it) => void incorporarSugestao(it)}
                  />
                </li>
              ))}
            </ul>
          </aside>
        </div>

        <div>
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            <button
              type="button"
              disabled={generating || !incorporadas.length}
              onClick={() => void gerarMetodologiaIntegrada()}
              className={BTN_PRIMARY}
            >
              {generating ? 'Gerando…' : 'Gerar metodologia integrada'}
            </button>
            <button
              type="button"
              disabled={saving || !(draft.versao_escola || '').trim()}
              onClick={() => void salvarVersaoInstituicao()}
              className={BTN_PRIMARY}
            >
              {saving ? 'Salvando…' : 'Salvar Versão da Instituição'}
            </button>
          </div>
          <p className="mt-2 text-[11px] italic leading-relaxed text-slate-500">
            Ao salvar, você ratifica a versão oficial desta metodologia na escola. Na
            integração, o professor verá este texto.
          </p>
        </div>
      </div>

      {err ? (
        <p className="mt-3 text-sm font-medium text-red-700" role="alert">
          {err}
        </p>
      ) : null}

      <ModalPadraoCanonico
        open={modalCanon}
        onClose={() => setModalCanon(false)}
        texto={canonCatalogo}
      />
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
      const customizado = Boolean(row.is_customizado)
      const salvo = (row.passos_customizados || row.versao_escola || '').trim()
      // Por padrão, o primeiro texto da escola é o canônico (até gravar uma versão).
      const inicial = customizado ? salvo : salvo || textoCanonico(row)
      next[id] = {
        versao_escola: inicial,
        observacoes_coordenacao: row.observacoes_coordenacao || '',
        is_customizado: customizado,
        updated_at: row.updated_at || null,
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
              className={tabClassName(active)}
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
              className={BTN_PRIMARY}
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
                    className={CHECKBOX_CLASS}
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
                    className={CHECKBOX_CLASS}
                  />
                  Habilitar no Desafio
                </label>
              </div>
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={creating}
                  className={BTN_PRIMARY}
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
                observacoes_coordenacao: '',
                is_customizado: false,
                updated_at: null,
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
                          className={CHECKBOX_CLASS}
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
                          className={CHECKBOX_CLASS}
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
                            return rid === id ? { ...r, ...body } : r
                          }),
                        )
                        patchDraft(id, {
                          versao_escola:
                            body.passos_customizados || body.versao_escola || '',
                          is_customizado: body.is_customizado !== false,
                          updated_at: body.updated_at || null,
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
