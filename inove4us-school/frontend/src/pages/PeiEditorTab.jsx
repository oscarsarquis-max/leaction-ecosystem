import { useCallback, useEffect, useMemo, useState } from 'react'
import ModalHistoricoVersoes from '../components/ModalHistoricoVersoes'

const INSTITUICAO_ID =
  import.meta.env.VITE_INSTITUICAO_ID || 'a1111111-1111-4111-8111-111111111111'

const SUBS = [
  { id: 'aee', label: '1. Diretrizes AEE (Por Condição)' },
  { id: 'pei', label: '2. PEIs Individuais' },
  { id: 'metodologicas', label: '3. Adaptações Metodológicas na Prática' },
]

const STATUS_LABEL = {
  rascunho: 'Rascunho',
  aguardando_assinaturas: 'Aguardando assinaturas',
  ativo: 'Ativo',
  arquivado: 'Arquivado',
}

const inputClass =
  'w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100'
const areaClass = `${inputClass} min-h-[7rem] resize-y`

const emptyPei = {
  nome_completo: '',
  matricula: '',
  nome_responsavel: '',
  condicao_categoria: 'TEA',
  perfil_atual_habilidades: '',
  barreiras_identificadas: '',
  metas_desenvolvimento: '',
  recursos_assistivos: '',
  criterios_avaliacao_flexibilizados: '',
  experiencias_adaptadas_individuais: '',
}

function statusBadge(status) {
  const map = {
    rascunho: 'bg-slate-100 text-slate-700',
    aguardando_assinaturas: 'bg-amber-100 text-amber-800',
    ativo: 'bg-emerald-100 text-emerald-800',
    arquivado: 'bg-slate-100 text-slate-500',
  }
  return map[status] || map.rascunho
}

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

/* -------------------------------------------------------------------------- */
/* Aba 1 — Diretrizes AEE                                                     */
/* -------------------------------------------------------------------------- */

function DiretrizesAeePanel({ onToast }) {
  const [condicoes, setCondicoes] = useState([])
  const [condicao, setCondicao] = useState('TEA')
  const [data, setData] = useState(null)
  const [textoEscola, setTextoEscola] = useState('')
  const [camposEscola, setCamposEscola] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [historicoOpen, setHistoricoOpen] = useState(false)

  useEffect(() => {
    ;(async () => {
      try {
        const res = await fetch('/api/aee/condicoes', { credentials: 'include' })
        const body = await res.json().catch(() => [])
        if (res.ok && Array.isArray(body) && body.length) {
          setCondicoes(body.map((c) => c.condicao_categoria))
          setCondicao(body[0].condicao_categoria)
        }
      } catch {
        /* fallback hardcoded abaixo */
      }
    })()
  }, [])

  const carregar = useCallback(async (cond) => {
    setLoading(true)
    setError('')
    try {
      const q = encodeURIComponent(cond)
      const res = await fetch(`/api/aee/matriz?condicao=${q}`, { credentials: 'include' })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha ao carregar matriz AEE')
      setData(body)
      const edit = body.editavel || body.atual
      setTextoEscola(edit?.texto_escola || '')
      setCamposEscola(edit?.campos_experiencia_metodologica || '')
    } catch (e) {
      setError(e.message || 'Erro ao carregar')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (condicao) carregar(condicao)
  }, [condicao, carregar])

  const editavel = data?.editavel
  const aguardando = data?.aguardando
  const ativa = data?.ativa
  const timeline = data?.timeline || []
  const canonTexto = data?.canonico?.descricao_base_canonica || ''
  const canonCampos = data?.canonico?.campos_experiencia_metodologica_canonica || ''

  async function salvarRascunho() {
    if (!editavel?.id) return
    setBusy('salvar')
    setError('')
    try {
      const res = await fetch(`/api/aee/matriz/${editavel.id}`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          texto_escola: textoEscola,
          campos_experiencia_metodologica: camposEscola,
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha ao salvar')
      onToast?.('Rascunho AEE salvo.')
      await carregar(condicao)
    } catch (e) {
      setError(e.message || 'Erro')
    } finally {
      setBusy('')
    }
  }

  async function enviarAprovacao() {
    if (!editavel?.id) return
    if (!window.confirm('Enviar para aprovação cria uma nova versão desta condição. Continuar?'))
      return
    setBusy('enviar')
    setError('')
    try {
      const res = await fetch(`/api/aee/matriz/${editavel.id}/enviar-aprovacao`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          texto_escola: textoEscola,
          campos_experiencia_metodologica: camposEscola,
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha ao enviar')
      onToast?.(body.message || 'Enviado para assinaturas.')
      await carregar(condicao)
    } catch (e) {
      setError(e.message || 'Erro')
    } finally {
      setBusy('')
    }
  }

  async function assinar(papel) {
    if (!aguardando?.id) return
    setBusy(`assinar-${papel}`)
    setError('')
    try {
      const res = await fetch(`/api/aee/matriz/assinar/${papel}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          matriz_id: aguardando.id,
          condicao_categoria: condicao,
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha na assinatura')
      onToast?.(body.message || 'Assinatura registrada.')
      await carregar(condicao)
    } catch (e) {
      setError(e.message || 'Erro')
    } finally {
      setBusy('')
    }
  }

  const listaCond = condicoes.length
    ? condicoes
    : [
        'TEA',
        'TDAH',
        'Altas Habilidades',
        'Deficiência Intelectual',
        'Deficiência Visual',
        'Deficiência Auditiva',
        'Deficiência Física',
        'Outras Dificuldades Severas',
      ]

  return (
    <div className="space-y-5">
      {historicoOpen ? (
        <ModalHistoricoVersoes
          tipo="aee"
          titulo={`Diretriz AEE — ${condicao}`}
          fetchUrl={`/api/aee/matrizes/${encodeURIComponent(condicao)}/historico`}
          onClose={() => setHistoricoOpen(false)}
        />
      ) : null}

      <div className="flex flex-wrap items-end gap-3">
        <label className="block min-w-[16rem] flex-1">
          <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
            Condição / categoria AEE
          </span>
          <select
            className={inputClass}
            value={condicao}
            onChange={(e) => setCondicao(e.target.value)}
          >
            {listaCond.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <div className="flex flex-wrap gap-2 pb-0.5">
          {ativa ? (
            <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusBadge('ativo')}`}>
              Ativa: v{ativa.versao}
            </span>
          ) : (
            <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">
              Sem matriz ativa nesta condição
            </span>
          )}
          {aguardando ? (
            <span
              className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusBadge('aguardando_assinaturas')}`}
            >
              v{aguardando.versao} aguardando
            </span>
          ) : null}
          <button
            type="button"
            onClick={() => setHistoricoOpen(true)}
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-ink hover:bg-slate-50"
          >
            ⏱️ Ver Histórico de Versões
          </button>
        </div>
      </div>

      {error ? (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </p>
      ) : null}

      {loading ? (
        <p className="text-sm text-muted">Carregando diretriz AEE…</p>
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Canônico */}
            <section className="space-y-3 rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <h3 className="text-sm font-bold text-ink">Canônico Inove4us (somente leitura)</h3>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                  Texto geral / política
                </p>
                <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink">
                  {canonTexto || '—'}
                </pre>
              </div>
              <div className="rounded-lg border border-violet-200 bg-violet-50/60 p-3">
                <p className="text-xs font-bold uppercase tracking-wide text-violet-800">
                  Campos de Experiência (Adaptações Metodológicas)
                </p>
                <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap font-sans text-sm leading-relaxed text-violet-950">
                  {canonCampos || '—'}
                </pre>
              </div>
            </section>

            {/* Escola */}
            <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
              <h3 className="text-sm font-bold text-ink">
                Versão da Escola
                {editavel ? ' (editável — rascunho)' : ' (somente leitura)'}
              </h3>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
                  Texto geral / política da escola
                </span>
                <textarea
                  className={`${areaClass} min-h-[10rem]`}
                  value={textoEscola}
                  disabled={!editavel || Boolean(busy)}
                  onChange={(e) => setTextoEscola(e.target.value)}
                />
              </label>
              <label className="block rounded-lg border border-school-200 bg-school-50/40 p-3">
                <span className="mb-1.5 block text-xs font-bold uppercase tracking-wide text-school-800">
                  Campos de Experiência (Adaptações Metodológicas)
                </span>
                <textarea
                  className={`${areaClass} min-h-[9rem] bg-white`}
                  value={camposEscola}
                  disabled={!editavel || Boolean(busy)}
                  onChange={(e) => setCamposEscola(e.target.value)}
                  placeholder="Roteiro prático: como adaptar PBL, Sala Invertida, etc. para esta condição…"
                />
              </label>
              {editavel ? (
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={Boolean(busy)}
                    onClick={salvarRascunho}
                    className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-ink hover:bg-slate-50 disabled:opacity-60"
                  >
                    {busy === 'salvar' ? 'Salvando…' : 'Salvar rascunho'}
                  </button>
                  <button
                    type="button"
                    disabled={Boolean(busy)}
                    onClick={enviarAprovacao}
                    className="rounded-xl bg-school-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-school-700 disabled:opacity-60"
                  >
                    {busy === 'enviar' ? 'Enviando…' : 'Enviar para aprovação'}
                  </button>
                </div>
              ) : null}
            </section>
          </div>

          <section className="rounded-xl border border-slate-200 bg-white p-4">
            <h3 className="text-sm font-bold text-ink">Timeline de versionamento — {condicao}</h3>
            <ul className="mt-3 space-y-2">
              {timeline.map((v) => (
                <li
                  key={v.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-100 px-3 py-2.5"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-ink">v{v.versao}</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-semibold ${statusBadge(v.status)}`}
                    >
                      {STATUS_LABEL[v.status] || v.status}
                    </span>
                    {v.assinado_coordenador ? (
                      <span className="text-xs text-emerald-700">Coord. ✓</span>
                    ) : null}
                    {v.assinado_psicopedagogo ? (
                      <span className="text-xs text-emerald-700">Psicoped. ✓</span>
                    ) : null}
                  </div>
                  <span className="text-xs text-muted">
                    {v.created_at ? new Date(v.created_at).toLocaleString('pt-BR') : ''}
                  </span>
                </li>
              ))}
            </ul>
            {aguardando ? (
              <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-100 pt-4">
                <button
                  type="button"
                  disabled={Boolean(busy) || aguardando.assinado_coordenador}
                  onClick={() => assinar('coordenador')}
                  className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {aguardando.assinado_coordenador
                    ? 'Coordenador já assinou'
                    : 'Assinar como Coordenador'}
                </button>
                <button
                  type="button"
                  disabled={Boolean(busy) || aguardando.assinado_psicopedagogo}
                  onClick={() => assinar('psicopedagogo')}
                  className="rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-violet-700 disabled:opacity-50"
                >
                  {aguardando.assinado_psicopedagogo
                    ? 'Psicopedagogo já assinou'
                    : 'Assinar como Psicopedagogo'}
                </button>
              </div>
            ) : null}
          </section>
        </>
      )}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/* Aba 2 — PEIs Individuais                                                   */
/* -------------------------------------------------------------------------- */

function Field({ label, hint, children, highlight }) {
  return (
    <label className={`block ${highlight ? 'rounded-lg border border-school-200 bg-school-50/50 p-3' : ''}`}>
      <span
        className={`mb-1.5 block text-xs font-semibold uppercase tracking-wide ${
          highlight ? 'text-school-800' : 'text-muted'
        }`}
      >
        {label}
      </span>
      {hint ? <p className="mb-1.5 text-xs text-muted">{hint}</p> : null}
      {children}
    </label>
  )
}

function PeisIndividuaisPanel({ onToast }) {
  const [lista, setLista] = useState([])
  const [condicoes, setCondicoes] = useState([])
  const [form, setForm] = useState(emptyPei)
  const [editId, setEditId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [historicoAlunoId, setHistoricoAlunoId] = useState(null)
  const [historicoTitulo, setHistoricoTitulo] = useState('')

  const carregar = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [resP, resC] = await Promise.all([
        fetch('/api/pei/alunos', { credentials: 'include' }),
        fetch('/api/aee/condicoes', { credentials: 'include' }),
      ])
      const bodyP = await resP.json().catch(() => [])
      const bodyC = await resC.json().catch(() => [])
      if (!resP.ok) throw new Error(bodyP.error || 'Falha ao listar PEIs')
      setLista(Array.isArray(bodyP) ? bodyP : [])
      if (Array.isArray(bodyC) && bodyC.length) {
        setCondicoes(bodyC.map((c) => c.condicao_categoria))
      }
    } catch (e) {
      setError(e.message || 'Erro')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    carregar()
  }, [carregar])

  function abrirNovo() {
    setEditId(null)
    setForm({
      ...emptyPei,
      condicao_categoria: condicoes[0] || 'TEA',
    })
    setShowForm(true)
  }

  function abrirEditar(row) {
    setEditId(row.id)
    setForm({
      nome_completo: row.nome_completo || '',
      matricula: row.matricula || '',
      nome_responsavel: row.nome_responsavel || '',
      condicao_categoria: row.condicao_categoria || 'TEA',
      perfil_atual_habilidades: row.perfil_atual_habilidades || '',
      barreiras_identificadas: row.barreiras_identificadas || '',
      metas_desenvolvimento: row.metas_desenvolvimento || '',
      recursos_assistivos: row.recursos_assistivos || '',
      criterios_avaliacao_flexibilizados: row.criterios_avaliacao_flexibilizados || '',
      experiencias_adaptadas_individuais: row.experiencias_adaptadas_individuais || '',
    })
    setShowForm(true)
  }

  function setField(key, value) {
    setForm((s) => ({ ...s, [key]: value }))
  }

  async function salvar(e) {
    e.preventDefault()
    setBusy('salvar')
    setError('')
    try {
      const url = editId ? `/api/pei/alunos/${editId}` : '/api/pei/alunos'
      const method = editId ? 'PUT' : 'POST'
      const payload = { ...form }
      if (editId) delete payload.condicao_categoria
      const res = await fetch(url, {
        method,
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha ao salvar PEI')
      onToast?.(editId ? 'PEI atualizado.' : `PEI criado para ${body.nome_completo}.`)
      setShowForm(false)
      await carregar()
    } catch (err) {
      setError(err.message || 'Erro')
    } finally {
      setBusy('')
    }
  }

  async function assinar(id, papel) {
    setBusy(`assinar-${papel}-${id}`)
    setError('')
    try {
      const res = await fetch(`/api/pei/alunos/${id}/assinar/${papel}`, {
        method: 'POST',
        credentials: 'include',
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha na assinatura')
      onToast?.(
        body.valido
          ? 'PEI válido — ambas as assinaturas concluídas.'
          : 'Assinatura registrada.',
      )
      await carregar()
    } catch (e) {
      setError(e.message || 'Erro')
    } finally {
      setBusy('')
    }
  }

  async function novaVersao(row) {
    if (!window.confirm(`Criar nova versão do PEI de ${row.nome_completo}? A versão atual será arquivada.`))
      return
    setBusy(`nova-${row.id}`)
    setError('')
    try {
      const res = await fetch(`/api/pei/alunos/${row.id}/nova-versao`, {
        method: 'POST',
        credentials: 'include',
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha ao criar nova versão')
      onToast?.(`Nova versão v${body.versao} criada — edite e assine.`)
      await carregar()
      abrirEditar(body)
    } catch (e) {
      setError(e.message || 'Erro')
    } finally {
      setBusy('')
    }
  }

  const listaCond = condicoes.length
    ? condicoes
    : ['TEA', 'TDAH', 'Altas Habilidades', 'Deficiência Intelectual']

  return (
    <div className="space-y-4">
      {historicoAlunoId ? (
        <ModalHistoricoVersoes
          tipo="pei"
          titulo={historicoTitulo}
          fetchUrl={`/api/pei/alunos/${historicoAlunoId}/historico`}
          onClose={() => setHistoricoAlunoId(null)}
        />
      ) : null}

      {error ? (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted">
          O PEI vincula-se à matriz AEE <strong>ativa</strong> da condição escolhida.
        </p>
        <button
          type="button"
          onClick={abrirNovo}
          className="rounded-xl bg-school-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-school-700"
        >
          Novo PEI individual
        </button>
      </div>

      {showForm ? (
        <form
          onSubmit={salvar}
          className="space-y-4 rounded-xl border border-slate-200 bg-white p-4"
        >
          <h3 className="text-sm font-bold text-ink">
            {editId ? 'Editar PEI' : 'Criar PEI individual'}
          </h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Nome completo">
              <input
                className={inputClass}
                required
                value={form.nome_completo}
                onChange={(e) => setField('nome_completo', e.target.value)}
              />
            </Field>
            <Field label="Matrícula">
              <input
                className={inputClass}
                value={form.matricula}
                onChange={(e) => setField('matricula', e.target.value)}
              />
            </Field>
            <Field label="Nome do responsável">
              <input
                className={inputClass}
                value={form.nome_responsavel}
                onChange={(e) => setField('nome_responsavel', e.target.value)}
              />
            </Field>
            {!editId ? (
              <Field label="Condição AEE">
                <select
                  className={inputClass}
                  value={form.condicao_categoria}
                  onChange={(e) => setField('condicao_categoria', e.target.value)}
                >
                  {listaCond.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </Field>
            ) : (
              <Field label="Condição AEE">
                <input className={inputClass} disabled value={form.condicao_categoria} />
              </Field>
            )}
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            <Field label="Perfil atual / habilidades">
              <textarea
                className={areaClass}
                value={form.perfil_atual_habilidades}
                onChange={(e) => setField('perfil_atual_habilidades', e.target.value)}
              />
            </Field>
            <Field label="Barreiras identificadas">
              <textarea
                className={areaClass}
                value={form.barreiras_identificadas}
                onChange={(e) => setField('barreiras_identificadas', e.target.value)}
              />
            </Field>
            <Field label="Metas de desenvolvimento">
              <textarea
                className={areaClass}
                value={form.metas_desenvolvimento}
                onChange={(e) => setField('metas_desenvolvimento', e.target.value)}
              />
            </Field>
            <Field label="Recursos assistivos">
              <textarea
                className={areaClass}
                value={form.recursos_assistivos}
                onChange={(e) => setField('recursos_assistivos', e.target.value)}
              />
            </Field>
            <Field label="Critérios de avaliação flexibilizados" className="lg:col-span-2">
              <textarea
                className={areaClass}
                value={form.criterios_avaliacao_flexibilizados}
                onChange={(e) =>
                  setField('criterios_avaliacao_flexibilizados', e.target.value)
                }
              />
            </Field>
          </div>

          <Field
            label="Campos de Experiência (Adaptação Metodológica Individual)"
            hint="Como o professor deve adaptar metodologias no dia a dia deste aluno."
            highlight
          >
            <textarea
              className={`${areaClass} min-h-[9rem] bg-white`}
              value={form.experiencias_adaptadas_individuais}
              onChange={(e) =>
                setField('experiencias_adaptadas_individuais', e.target.value)
              }
            />
          </Field>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="submit"
              disabled={Boolean(busy)}
              className="rounded-xl bg-school-600 px-4 py-2.5 text-sm font-bold text-white disabled:opacity-60"
            >
              {busy === 'salvar' ? 'Salvando…' : 'Salvar PEI'}
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold"
            >
              Cancelar
            </button>
            {editId ? (
              <button
                type="button"
                onClick={() => {
                  setHistoricoTitulo(`PEI — ${form.nome_completo || 'Aluno'}`)
                  setHistoricoAlunoId(editId)
                }}
                className="ml-auto rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold hover:bg-slate-50"
              >
                ⏱️ Ver Histórico de Versões
              </button>
            ) : null}
          </div>
        </form>
      ) : null}

      {loading ? (
        <p className="text-sm text-muted">Carregando PEIs…</p>
      ) : (
        <ul className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200 bg-white">
          {lista.map((a) => (
            <li key={a.id} className="flex flex-wrap items-start justify-between gap-3 px-4 py-3">
              <div className="min-w-0">
                <p className="font-semibold text-ink">{a.nome_completo}</p>
                <p className="text-xs text-muted">
                  {a.condicao_categoria} · v{a.versao || 1} · Matriz AEE v{a.aee_versao} ·
                  Matrícula: {a.matricula || '—'}
                  {a.valido ? (
                    <span className="ml-2 font-semibold text-emerald-700">Válido</span>
                  ) : (
                    <span className="ml-2 text-amber-700">Aguardando assinaturas</span>
                  )}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setHistoricoTitulo(`PEI — ${a.nome_completo}`)
                    setHistoricoAlunoId(a.id)
                  }}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold"
                >
                  ⏱️ Histórico
                </button>
                {!a.valido ? (
                  <button
                    type="button"
                    onClick={() => abrirEditar(a)}
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold"
                  >
                    Editar
                  </button>
                ) : (
                  <button
                    type="button"
                    disabled={Boolean(busy)}
                    onClick={() => novaVersao(a)}
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
                  >
                    Nova versão
                  </button>
                )}
                <button
                  type="button"
                  disabled={Boolean(busy) || a.assinado_coordenador}
                  onClick={() => assinar(a.id, 'coordenador')}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
                >
                  Coord.
                </button>
                <button
                  type="button"
                  disabled={Boolean(busy) || a.assinado_psicopedagogo}
                  onClick={() => assinar(a.id, 'psicopedagogo')}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
                >
                  Psicoped.
                </button>
              </div>
            </li>
          ))}
          {!lista.length ? (
            <li className="px-4 py-8 text-center text-sm text-muted">
              Nenhum PEI individual ainda.
            </li>
          ) : null}
        </ul>
      )}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/* Aba 3 — Adaptações Metodológicas (mesma UX da aba Metodologias)            */
/* -------------------------------------------------------------------------- */

const FAMILIAS_PEI = ['Indutivas', 'Agilidade', 'Contextuais', 'Dedutivas']

function descricaoCurtaPei(row) {
  const d = String(row.descricao || '').trim()
  if (d) return d
  const canon = String(row.texto_canonico || '').trim()
  if (!canon) return 'Sem descrição.'
  const line = canon.split('\n').find((l) => l.trim()) || ''
  return line.length > 140 ? `${line.slice(0, 137)}…` : line
}

function SugestaoCard({ item, busy, onAdaptar }) {
  const texto = item.teacher_adaptation_text || item.texto || '— (sem texto)'
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
          {busy ? 'Adaptando…' : '🤖 Adaptar PEI com IA'}
        </button>
      </footer>
    </article>
  )
}

/**
 * Painel expandido — espelha AccordionBody da aba Metodologias.
 */
function MetBody({ row, draft, onDraft, onSaved, onToast, peiAlunoId, condicao }) {
  const id = row.metodologia_id
  const canon = row.texto_canonico || ''
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
        const res = await fetch(`/api/pei/curadoria?metodologia_nome=${q}`, {
          credentials: 'include',
        })
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
      const textoSug = item.teacher_adaptation_text || item.texto || ''
      const res = await fetch(`/api/pei/metodologia/${id}/adaptar-ia`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          texto_canonico: canon,
          sugestao: textoSug,
          pei_aluno_id: peiAlunoId || undefined,
          condicao_categoria: condicao || undefined,
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha na adaptação com IA')
      onDraft({ versao_pei: body.versao_pei || '', gerado_por_ia: true })
      onToast?.('Rascunho gerado pela IA — revise e salve a adaptação PEI.')
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
      const res = await fetch(`/api/pei/metodologia/${id}/versao`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          versao_pei: (draft.versao_pei || '').trim() || null,
          gerado_por_ia: Boolean(draft.gerado_por_ia),
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível salvar')
      onSaved?.(body)
      onToast?.(`Adaptação PEI salva para “${row.nome}”.`)
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
              Adaptação PEI da Escola
            </span>
            <textarea
              value={draft.versao_pei || ''}
              onChange={(e) =>
                onDraft({
                  versao_pei: e.target.value,
                  gerado_por_ia: draft.gerado_por_ia,
                })
              }
              rows={10}
              placeholder="Passo a passo adaptado — gere com IA a partir de uma sugestão ou escreva manualmente."
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
              {saving ? 'Salvando…' : 'Salvar Adaptação PEI'}
            </button>
          </div>
        </div>

        <aside className="space-y-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">
              Sugestões dos Professores
            </p>
            <p className="mt-0.5 text-xs text-slate-500">
              Cada card traz o contexto da aula e o relato do professor (curadoria PEI).
            </p>
          </div>

          {loadingSug ? <p className="text-xs text-muted">Carregando…</p> : null}

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

function AdaptacoesPraticaPanel({ onToast }) {
  const [lista, setLista] = useState([])
  const [peis, setPeis] = useState([])
  const [drafts, setDrafts] = useState({})
  const [expandedId, setExpandedId] = useState(null)
  const [filtro, setFiltro] = useState('')
  const [familiaFiltro, setFamiliaFiltro] = useState('Todas')
  const [peiAlunoId, setPeiAlunoId] = useState('')
  const [condicao, setCondicao] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [togglingId, setTogglingId] = useState(null)

  useEffect(() => {
    ;(async () => {
      setLoading(true)
      setError('')
      try {
        const [resM, resP] = await Promise.all([
          fetch('/api/pei/metodologias', { credentials: 'include' }),
          fetch('/api/pei/alunos', { credentials: 'include' }),
        ])
        const bodyM = await resM.json().catch(() => [])
        const bodyP = await resP.json().catch(() => [])
        if (!resM.ok) throw new Error(bodyM.error || 'Falha ao carregar metodologias')
        const rows = Array.isArray(bodyM) ? bodyM : []
        setLista(rows)
        const d = {}
        rows.forEach((r) => {
          d[r.metodologia_id] = {
            versao_pei: r.versao_pei || '',
            gerado_por_ia: Boolean(r.gerado_por_ia),
            disponivel_dia_a_dia: r.disponivel_dia_a_dia !== false,
            disponivel_desafio: r.disponivel_desafio !== false,
            uso_estrelas: r.uso_estrelas || 0,
          }
        })
        setDrafts(d)
        setPeis(Array.isArray(bodyP) ? bodyP : [])
      } catch (e) {
        setError(e.message || 'Erro ao carregar metodologias')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const filtered = useMemo(() => {
    const q = filtro.trim().toLowerCase()
    return lista.filter((row) => {
      const familia = row.familia || row.categoria
      if (familiaFiltro !== 'Todas' && familia !== familiaFiltro) return false
      if (!q) return true
      return (
        (row.nome || '').toLowerCase().includes(q) ||
        (row.descricao || '').toLowerCase().includes(q)
      )
    })
  }, [lista, filtro, familiaFiltro])

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
      const res = await fetch(`/api/instituicoes/${INSTITUICAO_ID}/metodologias/${id}`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          disponivel_dia_a_dia: draft.disponivel_dia_a_dia,
          disponivel_desafio: draft.disponivel_desafio,
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível atualizar')
      setLista((prev) =>
        prev.map((row) => {
          if (row.metodologia_id !== id) return row
          return {
            ...row,
            disponivel_dia_a_dia: body.disponivel_dia_a_dia !== false,
            disponivel_desafio: body.disponivel_desafio !== false,
          }
        }),
      )
      patchDraft(id, {
        disponivel_dia_a_dia: body.disponivel_dia_a_dia !== false,
        disponivel_desafio: body.disponivel_desafio !== false,
      })
    } catch (err) {
      patchDraft(id, { [field]: !value })
      setError(err.message || 'Erro ao salvar disponibilidade')
    } finally {
      setTogglingId(null)
    }
  }

  const peiSel = peis.find((p) => p.id === peiAlunoId)

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-xl text-sm text-muted">
          Defina se a adaptação PEI vale no Dia a Dia e/ou no Desafio — os mesmos
          interruptores da aba Metodologias.
        </p>
        {!loading ? (
          <p className="text-xs text-muted">
            {filtered.length} de {lista.length} metodologia(s)
          </p>
        ) : null}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">
          Contexto para a IA (opcional)
        </p>
        <div className="flex flex-col gap-3 sm:flex-row">
          <label className="block min-w-0 flex-1">
            <span className="mb-1.5 block text-xs text-slate-500">PEI do aluno</span>
            <select
              className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100"
              value={peiAlunoId}
              onChange={(e) => {
                setPeiAlunoId(e.target.value)
                const p = peis.find((x) => x.id === e.target.value)
                if (p) setCondicao(p.condicao_categoria || '')
              }}
            >
              <option value="">— Sem PEI específico (usa AEE ativa) —</option>
              {peis.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nome_completo} ({p.condicao_categoria})
                </option>
              ))}
            </select>
          </label>
          <label className="block min-w-0 flex-1">
            <span className="mb-1.5 block text-xs text-slate-500">Ou condição AEE</span>
            <input
              className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100 disabled:bg-slate-50"
              placeholder="Ex: TEA"
              value={condicao}
              disabled={Boolean(peiAlunoId)}
              onChange={(e) => setCondicao(e.target.value)}
            />
          </label>
        </div>
        {peiSel ? (
          <p className="mt-2 text-xs text-school-700">
            IA usará as experiências individuais de {peiSel.nome_completo}.
          </p>
        ) : null}
      </div>

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
          {FAMILIAS_PEI.map((c) => (
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

      <div className="space-y-2">
        {filtered.map((row) => {
          const id = row.metodologia_id
          const draft = drafts[id] || {
            versao_pei: '',
            gerado_por_ia: false,
            disponivel_dia_a_dia: true,
            disponivel_desafio: true,
            uso_estrelas: 0,
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
                    <span className="text-slate-400" aria-hidden>
                      {open ? '▾' : '▸'}
                    </span>
                    <h3 className="text-base font-semibold text-ink">{row.nome}</h3>
                    <EstrelasUso value={row.uso_estrelas} />
                  </div>
                  <p className="mt-1 line-clamp-2 pl-5 text-sm text-muted">
                    {descricaoCurtaPei(row)}
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
                <MetBody
                  row={row}
                  draft={draft}
                  onDraft={(patch) => patchDraft(id, patch)}
                  onToast={onToast}
                  peiAlunoId={peiAlunoId}
                  condicao={condicao}
                  onSaved={(body) => {
                    setLista((prev) =>
                      prev.map((r) =>
                        r.metodologia_id === id
                          ? {
                              ...r,
                              versao_pei: body.versao_pei || '',
                              gerado_por_ia: Boolean(body.gerado_por_ia),
                            }
                          : r,
                      ),
                    )
                    patchDraft(id, {
                      versao_pei: body.versao_pei || '',
                      gerado_por_ia: Boolean(body.gerado_por_ia),
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
  )
}

/**
 * Aba Inclusão do Editor Pedagógico — AEE + PEI + adaptações práticas.
 */
export default function PeiEditorTab() {
  const [sub, setSub] = useState('aee')
  const [toast, setToast] = useState('')

  useEffect(() => {
    if (!toast) return undefined
    const t = setTimeout(() => setToast(''), 4000)
    return () => clearTimeout(t)
  }, [toast])

  return (
    <div className="space-y-4">
      {toast ? (
        <p className="text-sm text-school-700" role="status">
          {toast}
        </p>
      ) : null}

      <div className="flex gap-2 border-b border-slate-200">
        {SUBS.map((s) => {
          const active = sub === s.id
          return (
            <button
              key={s.id}
              type="button"
              onClick={() => setSub(s.id)}
              className={[
                '-mb-px border-b-2 px-4 py-2.5 text-sm font-semibold transition',
                active
                  ? 'border-school-500 text-school-800'
                  : 'border-transparent text-muted hover:text-ink',
              ].join(' ')}
            >
              {s.label}
            </button>
          )
        })}
      </div>

      {sub === 'aee' ? <DiretrizesAeePanel onToast={setToast} /> : null}
      {sub === 'pei' ? <PeisIndividuaisPanel onToast={setToast} /> : null}
      {sub === 'metodologicas' ? <AdaptacoesPraticaPanel onToast={setToast} /> : null}
    </div>
  )
}
