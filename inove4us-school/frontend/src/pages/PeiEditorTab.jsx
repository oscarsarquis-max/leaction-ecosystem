import { useCallback, useEffect, useMemo, useState } from 'react'
import ModalHistoricoVersoes from '../components/ModalHistoricoVersoes'
import { tabClassName } from '../lib/tabs'
import {
  BTN_PRIMARY,
  BTN_PRIMARY_BOLD,
  BTN_PRIMARY_FULL,
  CHECKBOX_CLASS,
} from '../lib/buttons'

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
  aluno_id: '',
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
        className="inline-flex items-center gap-0.5 text-base leading-none text-slate-300 sm:text-lg"
        title="Histórico do período: ainda sem sugestões aceitas"
        aria-label="Sem estrelas de uso"
      >
        <span aria-hidden>☆☆☆</span>
      </span>
    )
  }
  return (
    <span
      className="inline-flex items-center gap-0.5 text-base leading-none text-amber-500 sm:text-lg"
      title={`${n} de 3 — sugestões aceitas no período (histórico)`}
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
  if (/^prof.?s/i.test(raw)) return raw
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
                    className={BTN_PRIMARY_BOLD}
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
                  className="rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-violet-700 disabled:opacity-50"
                >
                  {aguardando.assinado_coordenador
                    ? 'Coordenador já assinou'
                    : 'Assinar como Coordenador'}
                </button>
                <button
                  type="button"
                  disabled={Boolean(busy) || aguardando.assinado_psicopedagogo}
                  onClick={() => assinar('psicopedagogo')}
                  className={BTN_PRIMARY_BOLD}
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
  const [alunosSec, setAlunosSec] = useState([])
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
      const [resP, resC, resA] = await Promise.all([
        fetch('/api/pei/alunos', { credentials: 'include' }),
        fetch('/api/aee/condicoes', { credentials: 'include' }),
        fetch('/api/secretaria/alunos', { credentials: 'include' }),
      ])
      const bodyP = await resP.json().catch(() => [])
      const bodyC = await resC.json().catch(() => [])
      const bodyA = await resA.json().catch(() => ({}))
      if (!resP.ok) throw new Error(bodyP.error || 'Falha ao listar PEIs')
      setLista(Array.isArray(bodyP) ? bodyP : [])
      if (Array.isArray(bodyC) && bodyC.length) {
        setCondicoes(bodyC.map((c) => c.condicao_categoria))
      }
      const itemsA = Array.isArray(bodyA?.items) ? bodyA.items : []
      setAlunosSec(itemsA.filter((a) => a.ativo !== false))
      if (!resA.ok) {
        setError(bodyA.error || 'Não foi possível carregar alunos da Secretaria')
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
      aluno_id: row.aluno_id || '',
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

  function onSelectAluno(alunoId) {
    const a = alunosSec.find((x) => x.id === alunoId)
    setForm((s) => ({
      ...s,
      aluno_id: alunoId,
      nome_completo: a?.nome || '',
      matricula: a?.matricula || '',
    }))
  }

  function setField(key, value) {
    setForm((s) => ({ ...s, [key]: value }))
  }

  async function salvar(e) {
    e.preventDefault()
    if (!form.aluno_id) {
      setError('Selecione um aluno cadastrado na Secretaria.')
      return
    }
    setBusy('salvar')
    setError('')
    try {
      const url = editId ? `/api/pei/alunos/${editId}` : '/api/pei/alunos'
      const method = editId ? 'PUT' : 'POST'
      const payload = {
        aluno_id: form.aluno_id,
        nome_responsavel: form.nome_responsavel,
        perfil_atual_habilidades: form.perfil_atual_habilidades,
        barreiras_identificadas: form.barreiras_identificadas,
        metas_desenvolvimento: form.metas_desenvolvimento,
        recursos_assistivos: form.recursos_assistivos,
        criterios_avaliacao_flexibilizados: form.criterios_avaliacao_flexibilizados,
        experiencias_adaptadas_individuais: form.experiencias_adaptadas_individuais,
      }
      if (!editId) payload.condicao_categoria = form.condicao_categoria
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
          className={BTN_PRIMARY_BOLD}
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
            <Field
              label="Aluno (Secretaria)"
              hint="Cadastre o aluno em Secretaria Acadêmica antes de criar o PEI."
            >
              <select
                className={inputClass}
                required
                value={form.aluno_id}
                onChange={(e) => onSelectAluno(e.target.value)}
                disabled={Boolean(editId)}
              >
                <option value="">Selecione o aluno…</option>
                {alunosSec.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.nome}
                    {a.matricula ? ` · ${a.matricula}` : ''}
                    {a.turma_nome ? ` · ${a.turma_nome}` : ''}
                  </option>
                ))}
              </select>
              {!alunosSec.length ? (
                <p className="mt-1 text-xs text-amber-800">
                  Nenhum aluno ativo na Secretaria desta instituição.
                </p>
              ) : null}
            </Field>
            <Field label="Matrícula (somente leitura)">
              <input
                className={inputClass}
                value={form.matricula}
                readOnly
                disabled
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
              className={BTN_PRIMARY_BOLD}
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
/* Aba 3 — Adaptações Metodológicas na Prática (por condição AEE)             */
/* -------------------------------------------------------------------------- */

const FAMILIAS_PEI = ['Indutivas', 'Agilidade', 'Contextuais', 'Dedutivas']

function formatDataModificacaoPei(iso) {
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

function limparRoteiroPei(raw) {
  const text = String(raw || '').trim()
  if (!text) return ''
  const ban =
    /adaptação pei|observações da coordenação|sugestões dos professores|texto integrado|campos de experiência|metodologia original|dados de entrada:|canônico|sugestões/i
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

function IconeCadeadoPei({ className = 'h-4 w-4' }) {
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

/** Modal: metodologia canônica + campos de experiência AEE (somente leitura). */
function ModalBaseAdaptacao({ open, onClose, textoCanonico, camposExperiencia, condicao }) {
  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Base de adaptação"
      onClick={onClose}
    >
      <div
        className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-ink">Base de Adaptação</h2>
            <p className="mt-1 text-sm italic text-slate-500">
              Fonte de referência para a condição {condicao || '—'}. Estes textos não são
              editados aqui.
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
        <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
          <section className="rounded-lg border border-slate-200 bg-slate-50/80 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">
              1. Texto Canônico Original da Metodologia
            </p>
            <pre className="mt-2 whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink">
              {textoCanonico || '—'}
            </pre>
          </section>
          <section className="rounded-lg border border-violet-200 bg-violet-50/50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-violet-800">
              2. Campos de Experiência (AEE — {condicao || 'condição'})
            </p>
            <pre className="mt-2 whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink">
              {camposExperiencia || '—'}
            </pre>
          </section>
        </div>
      </div>
    </div>
  )
}

function descricaoCurtaPei(row) {
  const d = String(row.descricao || '').trim()
  if (d) return d
  const canon = String(row.texto_canonico || '').trim()
  if (!canon) return 'Sem descrição.'
  const line = canon.split('\n').find((l) => l.trim()) || ''
  return line.length > 140 ? `${line.slice(0, 137)}…` : line
}

function SugestaoCard({ item, busy, incorporada, onIncorporar }) {
  const texto = item.teacher_adaptation_text || item.texto || '— (sem texto)'
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

/**
 * Painel expandido — UX limpa da aba Metodologias, persistência por condição AEE.
 */
function MetBody({
  row,
  draft,
  onDraft,
  onSaved,
  onToast,
  aeeId,
  condicao,
  camposExperiencia,
}) {
  const id = row.metodologia_id
  const nomeMet = row.nome || ''
  const canonCatalogo = row.texto_canonico || ''
  const campos = camposExperiencia || row.campos_experiencia_aee || ''
  const isCustomizado = Boolean(row.is_customizado ?? draft.is_customizado)
  const dataMod = formatDataModificacaoPei(row.updated_at || draft.updated_at)

  const [sugestoes, setSugestoes] = useState([])
  const [loadingSug, setLoadingSug] = useState(true)
  const [busyId, setBusyId] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')
  const [incorporadas, setIncorporadas] = useState([])
  const [modalBase, setModalBase] = useState(false)

  useEffect(() => {
    setIncorporadas([])
    setErr('')
    if (!(draft.versao_escola || '').trim() && canonCatalogo) {
      onDraft({ versao_escola: canonCatalogo })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- só ao trocar metodologia/AEE
  }, [id, aeeId])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoadingSug(true)
      setSugestoes([])
      setIncorporadas([])
      try {
        if (!nomeMet) {
          if (!cancelled) {
            setSugestoes([])
            setLoadingSug(false)
          }
          return
        }
        const q = encodeURIComponent(nomeMet)
        const res = await fetch(`/api/pei/curadoria?metodologia_nome=${q}`, {
          credentials: 'include',
        })
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(body.error || 'Falha ao carregar sugestões')
        const items = Array.isArray(body.items) ? body.items : []
        const daMetodologia = items.filter((it) => {
          const nome = it.metodologia_nome || ''
          if (!String(nome).trim()) return true
          return String(nome).trim().toLowerCase() === nomeMet.toLowerCase()
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
  }, [nomeMet])

  async function incorporarSugestao(item) {
    if (incorporadas.some((s) => s.id === item.id)) return
    setBusyId(item.id)
    setErr('')
    try {
      if (!item.smoke && !String(item.id).startsWith('smoke-')) {
        const res = await fetch(`/api/pei/curadoria/${item.id}/incorporar`, {
          method: 'POST',
          credentials: 'include',
        })
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(body.error || 'Falha ao incorporar sugestão')
      }
      setIncorporadas((prev) => [...prev, item])
      onToast?.(
        'Sugestão marcada. Use “Gerar adaptação integrada” para a IA compor o texto.',
      )
    } catch (e) {
      setErr(e.message || 'Erro ao incorporar')
    } finally {
      setBusyId(null)
    }
  }

  async function gerarAdaptacaoIntegrada() {
    if (!aeeId) {
      setErr('Selecione uma condição AEE antes de gerar.')
      return
    }
    setGenerating(true)
    setErr('')
    try {
      const sugestoesTxt = incorporadas
        .map((s) => s.teacher_adaptation_text || s.texto || '')
        .map((t) => String(t).trim())
        .filter(Boolean)
      const res = await fetch(
        `/api/aee/${aeeId}/metodologia/${encodeURIComponent(nomeMet)}/adaptar-ia`,
        {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            texto_canonico: canonCatalogo,
            campos_experiencia_aee: campos,
            sugestoes: sugestoesTxt,
          }),
        },
      )
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha na síntese com IA')
      const texto = limparRoteiroPei(body.versao_escola || '')
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
    if (!aeeId) {
      setErr('Selecione uma condição AEE antes de salvar.')
      return
    }
    setSaving(true)
    setErr('')
    try {
      const res = await fetch(
        `/api/aee/${aeeId}/metodologias/${encodeURIComponent(nomeMet)}`,
        {
          method: 'PUT',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ versao_escola: texto }),
        },
      )
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível salvar')
      onDraft({
        versao_escola: body.versao_escola || texto,
        is_customizado: body.is_customizado !== false,
        updated_at: body.updated_at || new Date().toISOString(),
      })
      onSaved?.(body)
      onToast?.(`Versão da instituição salva para “${nomeMet}” (${condicao}).`)
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
        <section className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
          <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                  Versão da Escola para {condicao || '—'}
                </p>
                <button
                  type="button"
                  onClick={() => setModalBase(true)}
                  className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] font-medium text-slate-600 transition hover:border-school-300 hover:bg-school-50 hover:text-school-700"
                >
                  <IconeCadeadoPei className="h-3.5 w-3.5" />
                  Ver Base de Adaptação
                </button>
              </div>
              <p className="mt-0.5 text-[11px] text-slate-500">
                Texto oficial em uso pelo professor nesta condição. Começa com o canônico e
                muda quando a escola adapta. A base (canônico + campos AEE) fica no cadeado.
              </p>
            </div>
            <p className="shrink-0 text-xs font-medium text-slate-600">
              {isCustomizado && dataMod
                ? `Adaptada · ${dataMod}`
                : 'Padrão canônico (ainda sem adaptação)'}
            </p>
          </div>
          <textarea
            value={draft.versao_escola || ''}
            onChange={(e) => onDraft({ versao_escola: e.target.value })}
            rows={12}
            placeholder="Versão da escola para esta condição — inicia com o padrão canônico."
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-ink outline-none transition placeholder:text-slate-400 focus:border-school-500 focus:ring-2 focus:ring-school-100"
          />
        </section>

        <aside className="flex min-h-[14rem] flex-col">
            <div className="mb-2 shrink-0">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                Sugestões dos Professores
              </p>
              <p className="mt-0.5 text-xs text-slate-500">
                Marque com Incorporar e gere a composição no campo Versão da Escola acima.
                {incorporadas.length
                  ? ` (${incorporadas.length} selecionada${incorporadas.length > 1 ? 's' : ''})`
                  : ''}
              </p>
            </div>

            {loadingSug ? <p className="text-xs text-muted">Carregando…</p> : null}

            {!loadingSug && !sugestoes.length ? (
              <p className="rounded-lg border border-dashed border-slate-200 px-3 py-6 text-center text-xs text-muted">
                Nenhuma sugestão pendente para esta metodologia.
              </p>
            ) : null}

            <ul className="grid min-h-0 flex-1 gap-3 overflow-y-auto pr-0.5 sm:grid-cols-2 xl:grid-cols-3">
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

        <div>
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            <button
              type="button"
              disabled={generating || !aeeId}
              onClick={() => void gerarAdaptacaoIntegrada()}
              className={BTN_PRIMARY}
            >
              {generating ? 'Gerando…' : 'Gerar adaptação integrada'}
            </button>
            <button
              type="button"
              disabled={saving || !(draft.versao_escola || '').trim() || !aeeId}
              onClick={() => void salvarVersaoInstituicao()}
              className={BTN_PRIMARY}
            >
              {saving ? 'Salvando…' : 'Salvar Versão da Instituição'}
            </button>
          </div>
          <p className="mt-2 text-[11px] italic leading-relaxed text-slate-500">
            Ao salvar, você ratifica a adaptação oficial desta metodologia para a condição{' '}
            {condicao || 'selecionada'}.
          </p>
        </div>
      </div>

      {err ? (
        <p className="mt-3 text-sm font-medium text-red-700" role="alert">
          {err}
        </p>
      ) : null}

      <ModalBaseAdaptacao
        open={modalBase}
        onClose={() => setModalBase(false)}
        textoCanonico={canonCatalogo}
        camposExperiencia={campos}
        condicao={condicao}
      />
    </div>
  )
}

function AdaptacoesPraticaPanel({ onToast, focusMet = '' }) {
  const [condicoes, setCondicoes] = useState([])
  const [condicao, setCondicao] = useState('TEA')
  const [aeeId, setAeeId] = useState('')
  const [camposAee, setCamposAee] = useState('')
  const [lista, setLista] = useState([])
  const [drafts, setDrafts] = useState({})
  const [expandedId, setExpandedId] = useState(null)
  const [filtro, setFiltro] = useState(focusMet || '')
  const [familiaFiltro, setFamiliaFiltro] = useState('Todas')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [togglingId, setTogglingId] = useState(null)

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
        setCondicoes(['TEA', 'TDAH', 'DI', 'Dislexia'])
      }
    })()
  }, [])

  const carregar = useCallback(async (cond) => {
    setLoading(true)
    setError('')
    setExpandedId(null)
    try {
      const q = encodeURIComponent(cond)
      const resM = await fetch(`/api/aee/matriz?condicao=${q}`, {
        credentials: 'include',
      })
      const bodyM = await resM.json().catch(() => ({}))
      if (!resM.ok) throw new Error(bodyM.error || 'Falha ao carregar matriz AEE')
      const matriz = bodyM.editavel || bodyM.ativa || bodyM.atual
      if (!matriz?.id) throw new Error('Nenhuma matriz AEE disponível para esta condição')
      setAeeId(matriz.id)
      setCamposAee(matriz.campos_experiencia_metodologica || '')

      const res = await fetch(`/api/aee/${matriz.id}/metodologias`, {
        credentials: 'include',
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha ao carregar metodologias')
      const rows = Array.isArray(body.items) ? body.items : []
      setLista(rows)
      setCamposAee(body.campos_experiencia_aee || matriz.campos_experiencia_metodologica || '')
      const d = {}
      rows.forEach((r) => {
        const salvo = (r.versao_escola || '').trim()
        const canon = (r.texto_canonico || '').trim()
        d[r.metodologia_id] = {
          // Sempre inicia com a versão em uso (canônica até a 1ª adaptação).
          versao_escola: salvo || canon,
          is_customizado: Boolean(r.is_customizado),
          updated_at: r.updated_at || null,
          disponivel_dia_a_dia: r.disponivel_dia_a_dia !== false,
          disponivel_desafio: r.disponivel_desafio !== false,
        }
      })
      setDrafts(d)
      if (focusMet) {
        const hit = rows.find(
          (r) => String(r.nome || '').trim().toLowerCase() === focusMet.toLowerCase(),
        )
        if (hit) {
          setExpandedId(hit.metodologia_id)
          setFiltro(hit.nome || focusMet)
        }
      }
    } catch (e) {
      setError(e.message || 'Erro ao carregar')
      setLista([])
      setAeeId('')
    } finally {
      setLoading(false)
    }
  }, [focusMet])

  useEffect(() => {
    if (condicao) void carregar(condicao)
  }, [condicao, carregar])

  useEffect(() => {
    if (focusMet) setFiltro(focusMet)
  }, [focusMet])

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
      const res = await fetch(`/api/pedagogico/metodologias/${id}`, {
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

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-[12rem]">
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
              Condição AEE
            </span>
            <select
              value={condicao}
              onChange={(e) => setCondicao(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100"
            >
              {(condicoes.length ? condicoes : ['TEA']).map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="max-w-xl flex-1 text-sm text-muted">
          Adaptação por condição — a versão salva vale para esta matriz AEE (
          {condicao}).
        </p>
        {!loading ? (
          <p className="text-xs text-muted">
            {filtered.length} de {lista.length} metodologia(s)
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
            versao_escola: '',
            is_customizado: false,
            disponivel_dia_a_dia: true,
            disponivel_desafio: true,
          }
          const open = expandedId === id
          const busyToggle = togglingId === id
          const pendentes = Number(row.pendentes_count) || 0
          const temPendente = pendentes > 0
          const versaoStatus =
            draft.is_customizado || row.is_customizado
              ? `Versão da escola · adaptada${
                  formatDataModificacaoPei(draft.updated_at || row.updated_at)
                    ? ` em ${formatDataModificacaoPei(draft.updated_at || row.updated_at)}`
                    : ''
                }`
              : 'Versão da escola · padrão canônico'

          return (
            <article
              key={id}
              className={[
                'overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm',
                temPendente ? 'border-l-[5px] border-l-amber-500 bg-amber-50/35' : '',
              ].join(' ')}
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
                    {temPendente ? (
                      <span className="rounded-md bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-900">
                        {pendentes === 1
                          ? '1 sugestão p/ análise'
                          : `${pendentes} sugestões p/ análise`}
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1 pl-5 text-xs font-medium text-slate-600">
                    {versaoStatus}
                  </p>
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
                <MetBody
                  row={row}
                  draft={draft}
                  onDraft={(patch) => patchDraft(id, patch)}
                  onToast={onToast}
                  aeeId={aeeId}
                  condicao={condicao}
                  camposExperiencia={camposAee}
                  onSaved={(body) => {
                    setLista((prev) =>
                      prev.map((r) =>
                        r.metodologia_id === id
                          ? {
                              ...r,
                              versao_escola: body.versao_escola || '',
                              is_customizado: body.is_customizado !== false,
                              updated_at: body.updated_at || r.updated_at,
                            }
                          : r,
                      ),
                    )
                    patchDraft(id, {
                      versao_escola: body.versao_escola || '',
                      is_customizado: body.is_customizado !== false,
                      updated_at: body.updated_at || null,
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
export default function PeiEditorTab({ focusMet = '' }) {
  const [sub, setSub] = useState(focusMet ? 'metodologicas' : 'aee')
  const [toast, setToast] = useState('')

  useEffect(() => {
    if (focusMet) setSub('metodologicas')
  }, [focusMet])

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
              className={tabClassName(active)}
            >
              {s.label}
            </button>
          )
        })}
      </div>

      {sub === 'aee' ? <DiretrizesAeePanel onToast={setToast} /> : null}
      {sub === 'pei' ? <PeisIndividuaisPanel onToast={setToast} /> : null}
      {sub === 'metodologicas' ? (
        <AdaptacoesPraticaPanel onToast={setToast} focusMet={focusMet} />
      ) : null}
    </div>
  )
}
