import { useEffect, useMemo, useState } from 'react'
import AlunoPEI from './AlunoPEI'

const INSTITUICAO_ID =
  import.meta.env.VITE_INSTITUICAO_ID || 'a1111111-1111-4111-8111-111111111111'

export const CAMPOS_EXPERIENCIA = [
  { id: 'o_eu_o_outro_e_o_nos', label: 'O eu, o outro e o nós' },
  { id: 'corpo_gestos_e_movimentos', label: 'Corpo, gestos e movimentos' },
  {
    id: 'escuta_fala_pensamento_e_imaginacao',
    label: 'Escuta, fala, pensamento e imaginação',
  },
  { id: 'tracos_sons_cores_e_formas', label: 'Traços, sons, cores e formas' },
  {
    id: 'espacos_tempos_quantidades_relacoes_e_transformacoes',
    label: 'Espaços, tempos, quantidades, relações e transformações',
  },
]

const SUGESTOES_TIPO = ['TDAH', 'TEA', 'Dislexia']

const emptyArea = {
  tipo_neurodivergencia: '',
  diretriz: '',
  capacidades_interesses: '',
  necessidades: '',
  metas_prazos: '',
  recursos_estrategias: '',
  profissionais_envolvidos: '',
  ativo: true,
}

const emptyNovoObj = {
  objetivo: '',
  curriculo_habilidades: '',
  estrategias_ensino: '',
  prazo: '',
}

const inputClass =
  'w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100'
const areaClass = `${inputClass} min-h-[5rem] resize-y`

function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
        {label}
      </span>
      {hint ? <p className="mb-1.5 text-xs text-muted">{hint}</p> : null}
      {children}
    </label>
  )
}

/**
 * Pilar 2 do Editor Pedagógico — planos gerais de PEI (neuropedagoga).
 */
export default function PeiEditorTab() {
  const [modo, setModo] = useState('planos') // planos | ciclo
  const [lista, setLista] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [area, setArea] = useState(emptyArea)
  const [novoOpen, setNovoOpen] = useState(false)
  const [novoTipo, setNovoTipo] = useState('')
  const [campoAberto, setCampoAberto] = useState(CAMPOS_EXPERIENCIA[0].id)
  const [addFormPorCampo, setAddFormPorCampo] = useState({})
  const [draftsObj, setDraftsObj] = useState({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')


  async function carregarLista() {
    const res = await fetch(`/api/instituicoes/${INSTITUICAO_ID}/pei/planos-gerais`)
    const body = await res.json().catch(() => [])
    if (!res.ok) throw new Error(body.error || 'Não foi possível carregar os planos')
    setLista(body)
    return body
  }

  async function carregarDetalhe(id) {
    const res = await fetch(`/api/pei/planos-gerais/${id}`)
    const body = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(body.error || 'Não foi possível abrir o plano')
    setDetail(body)
    setArea({
      tipo_neurodivergencia: body.tipo_neurodivergencia || '',
      diretriz: body.diretriz || '',
      capacidades_interesses: body.capacidades_interesses || '',
      necessidades: body.necessidades || '',
      metas_prazos: body.metas_prazos || '',
      recursos_estrategias: body.recursos_estrategias || '',
      profissionais_envolvidos: body.profissionais_envolvidos || '',
      ativo: body.ativo !== false,
    })
    const drafts = {}
    for (const c of body.campos_experiencia || []) {
      drafts[c.id] = {
        objetivo: c.objetivo || '',
        curriculo_habilidades: c.curriculo_habilidades || '',
        estrategias_ensino: c.estrategias_ensino || '',
        prazo: c.prazo || '',
        ativo: c.ativo !== false,
      }
    }
    setDraftsObj(drafts)
    return body
  }

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError('')
      try {
        const body = await carregarLista()
        if (cancelled) return
        if (body.length) {
          const first = body.find((p) => p.ativo) || body[0]
          setSelectedId(first.id)
          await carregarDetalhe(first.id)
        }
      } catch (err) {
        if (!cancelled) setError(err.message || 'Erro ao carregar')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const objetivosPorCampo = useMemo(() => {
    const map = new Map(CAMPOS_EXPERIENCIA.map((c) => [c.id, []]))
    for (const obj of detail?.campos_experiencia || []) {
      if (!map.has(obj.campo_experiencia)) map.set(obj.campo_experiencia, [])
      map.get(obj.campo_experiencia).push(obj)
    }
    return map
  }, [detail])

  async function selecionar(id) {
    setError('')
    setFeedback('')
    setSelectedId(id)
    setNovoOpen(false)
    setSaving(true)
    try {
      await carregarDetalhe(id)
    } catch (err) {
      setError(err.message || 'Erro ao abrir')
    } finally {
      setSaving(false)
    }
  }

  async function criarPlano(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    setFeedback('')
    try {
      const tipo = novoTipo.trim()
      if (!tipo) throw new Error('Informe o tipo de neurodivergência.')
      const res = await fetch(`/api/instituicoes/${INSTITUICAO_ID}/pei/planos-gerais`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tipo_neurodivergencia: tipo }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível criar o plano')
      setNovoTipo('')
      setNovoOpen(false)
      await carregarLista()
      setSelectedId(body.id)
      await carregarDetalhe(body.id)
      setFeedback(`Plano geral “${body.tipo_neurodivergencia}” criado.`)
    } catch (err) {
      setError(err.message || 'Erro ao criar')
    } finally {
      setSaving(false)
    }
  }

  async function salvarArea(e) {
    e.preventDefault()
    if (!selectedId) return
    setSaving(true)
    setError('')
    setFeedback('')
    try {
      const res = await fetch(`/api/pei/planos-gerais/${selectedId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tipo_neurodivergencia: area.tipo_neurodivergencia.trim(),
          diretriz: area.diretriz.trim() || '—',
          capacidades_interesses: area.capacidades_interesses.trim(),
          necessidades: area.necessidades.trim(),
          metas_prazos: area.metas_prazos.trim(),
          recursos_estrategias: area.recursos_estrategias.trim(),
          profissionais_envolvidos: area.profissionais_envolvidos.trim(),
          ativo: area.ativo,
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível salvar')
      await carregarLista()
      setDetail(body)
      setFeedback('Área geral atualizada.')
    } catch (err) {
      setError(err.message || 'Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  async function toggleAtivoPlano() {
    if (!selectedId) return
    setSaving(true)
    setError('')
    try {
      const next = !area.ativo
      const res = await fetch(`/api/pei/planos-gerais/${selectedId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ativo: next }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível atualizar')
      setArea((a) => ({ ...a, ativo: body.ativo }))
      setDetail(body)
      await carregarLista()
      setFeedback(body.ativo ? 'Plano ativado.' : 'Plano desativado.')
    } catch (err) {
      setError(err.message || 'Erro ao atualizar')
    } finally {
      setSaving(false)
    }
  }

  function patchDraft(id, patch) {
    setDraftsObj((prev) => ({ ...prev, [id]: { ...prev[id], ...patch } }))
  }

  async function salvarObjetivo(id) {
    const draft = draftsObj[id]
    if (!draft) return
    setSaving(true)
    setError('')
    setFeedback('')
    try {
      const res = await fetch(`/api/pei/campos-experiencia/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          objetivo: draft.objetivo.trim(),
          curriculo_habilidades: draft.curriculo_habilidades.trim(),
          estrategias_ensino: draft.estrategias_ensino.trim(),
          prazo: draft.prazo.trim(),
          ativo: draft.ativo,
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível salvar o objetivo')
      await carregarDetalhe(selectedId)
      setFeedback('Objetivo atualizado.')
    } catch (err) {
      setError(err.message || 'Erro ao salvar objetivo')
    } finally {
      setSaving(false)
    }
  }

  async function desativarObjetivo(id) {
    setSaving(true)
    setError('')
    try {
      const res = await fetch(`/api/pei/campos-experiencia/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ativo: false }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível desativar')
      await carregarDetalhe(selectedId)
      setFeedback('Objetivo desativado.')
    } catch (err) {
      setError(err.message || 'Erro ao desativar')
    } finally {
      setSaving(false)
    }
  }

  async function adicionarObjetivo(campoId, e) {
    e.preventDefault()
    if (!selectedId) return
    const form = addFormPorCampo[campoId] || emptyNovoObj
    setSaving(true)
    setError('')
    setFeedback('')
    try {
      if (!form.objetivo.trim()) throw new Error('Informe o objetivo.')
      const res = await fetch(`/api/pei/planos-gerais/${selectedId}/campos-experiencia`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          campo_experiencia: campoId,
          objetivo: form.objetivo.trim(),
          curriculo_habilidades: form.curriculo_habilidades.trim(),
          estrategias_ensino: form.estrategias_ensino.trim(),
          prazo: form.prazo.trim(),
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível adicionar')
      setAddFormPorCampo((prev) => ({ ...prev, [campoId]: { ...emptyNovoObj } }))
      await carregarDetalhe(selectedId)
      setFeedback('Objetivo adicionado.')
    } catch (err) {
      setError(err.message || 'Erro ao adicionar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
        {[
          { id: 'planos', label: 'Planos gerais' },
          { id: 'ciclo', label: 'Ciclo Vivo (Alunos)' },
        ].map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => {
              setModo(t.id)
              setFeedback('')
              setError('')
            }}
            className={[
              'rounded-lg px-3 py-2 text-sm font-semibold transition',
              modo === t.id
                ? 'bg-school-500 text-white'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200',
            ].join(' ')}
          >
            {t.label}
          </button>
        ))}
      </div>

      {modo === 'ciclo' ? <AlunoPEI /> : null}

      {modo === 'planos' ? (
      <>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm text-muted">
            Diretrizes institucionais por tipo de neurodivergência — área geral e
            objetivos nos campos de experiência (Educação Infantil · BNCC).
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setNovoOpen((v) => !v)
            setFeedback('')
            setError('')
          }}
          className="shrink-0 rounded-lg bg-school-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-school-600"
        >
          {novoOpen ? 'Fechar formulário' : 'Novo plano geral'}
        </button>
      </div>

      {error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
      {feedback ? (
        <p className="text-sm text-emerald-800" role="status">
          {feedback}
        </p>
      ) : null}

      {novoOpen ? (
        <form
          onSubmit={criarPlano}
          className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-panel"
        >
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
            Novo plano geral
          </h2>
          <Field
            label="Tipo de neurodivergência"
            hint={`Exemplos: ${SUGESTOES_TIPO.join(', ')} — texto livre`}
          >
            <input
              className={inputClass}
              list="pei-tipos-sugeridos"
              value={novoTipo}
              onChange={(e) => setNovoTipo(e.target.value)}
              placeholder="Ex.: TEA"
              required
            />
            <datalist id="pei-tipos-sugeridos">
              {SUGESTOES_TIPO.map((t) => (
                <option key={t} value={t} />
              ))}
            </datalist>
          </Field>
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-school-500 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
            >
              Criar plano
            </button>
          </div>
        </form>
      ) : null}

      {loading ? (
        <p className="text-sm text-muted" role="status">
          Carregando…
        </p>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[16rem_minmax(0,1fr)]">
          <aside className="rounded-xl border border-slate-200 bg-white shadow-panel">
            <div className="border-b border-slate-100 px-4 py-3">
              <h2 className="text-sm font-semibold text-ink">Planos gerais</h2>
            </div>
            {lista.length === 0 ? (
              <p className="px-4 py-6 text-sm text-muted">Nenhum plano cadastrado.</p>
            ) : (
              <ul className="max-h-[32rem] space-y-1 overflow-y-auto p-2">
                {lista.map((p) => (
                  <li key={p.id}>
                    <button
                      type="button"
                      onClick={() => selecionar(p.id)}
                      className={[
                        'flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2.5 text-left text-sm transition',
                        selectedId === p.id
                          ? 'bg-school-50 text-school-800'
                          : 'text-ink hover:bg-slate-50',
                      ].join(' ')}
                    >
                      <span className="font-semibold">{p.tipo_neurodivergencia}</span>
                      <span
                        className={[
                          'shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-semibold uppercase',
                          p.ativo
                            ? 'bg-emerald-50 text-emerald-800'
                            : 'bg-slate-100 text-slate-500',
                        ].join(' ')}
                      >
                        {p.ativo ? 'Ativo' : 'Inativo'}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </aside>

          {!selectedId ? (
            <p className="rounded-xl border border-dashed border-slate-200 bg-white px-6 py-10 text-center text-sm text-muted">
              Selecione um plano ou crie o primeiro.
            </p>
          ) : (
            <div className="space-y-5">
              <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-panel">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h2 className="text-sm font-semibold text-ink">Área geral</h2>
                  <label className="inline-flex items-center gap-2 text-sm font-medium text-ink">
                    <input
                      type="checkbox"
                      checked={area.ativo}
                      onChange={toggleAtivoPlano}
                      disabled={saving}
                      className="h-4 w-4 rounded border-slate-300 text-school-600 focus:ring-school-500"
                    />
                    {area.ativo ? 'Ativo' : 'Inativo'}
                  </label>
                </div>

                <form onSubmit={salvarArea} className="mt-4 space-y-4">
                  <Field label="Tipo de neurodivergência">
                    <input
                      className={inputClass}
                      value={area.tipo_neurodivergencia}
                      onChange={(e) =>
                        setArea((a) => ({
                          ...a,
                          tipo_neurodivergencia: e.target.value,
                        }))
                      }
                      required
                    />
                  </Field>
                  <Field label="Resumo geral" hint="Visão livre do plano">
                    <textarea
                      className={areaClass}
                      value={area.diretriz}
                      onChange={(e) =>
                        setArea((a) => ({ ...a, diretriz: e.target.value }))
                      }
                    />
                  </Field>
                  <div className="grid gap-4 md:grid-cols-2">
                    <Field
                      label="Capacidades e interesses"
                      hint="O que sabe, do que gosta"
                    >
                      <textarea
                        className={areaClass}
                        value={area.capacidades_interesses}
                        onChange={(e) =>
                          setArea((a) => ({
                            ...a,
                            capacidades_interesses: e.target.value,
                          }))
                        }
                      />
                    </Field>
                    <Field label="Necessidades" hint="O que ainda precisa aprender">
                      <textarea
                        className={areaClass}
                        value={area.necessidades}
                        onChange={(e) =>
                          setArea((a) => ({ ...a, necessidades: e.target.value }))
                        }
                      />
                    </Field>
                    <Field label="Metas e prazos" hint="Em quanto tempo">
                      <textarea
                        className={areaClass}
                        value={area.metas_prazos}
                        onChange={(e) =>
                          setArea((a) => ({ ...a, metas_prazos: e.target.value }))
                        }
                      />
                    </Field>
                    <Field
                      label="Recursos e estratégias"
                      hint="O que utilizar para ensinar e como"
                    >
                      <textarea
                        className={areaClass}
                        value={area.recursos_estrategias}
                        onChange={(e) =>
                          setArea((a) => ({
                            ...a,
                            recursos_estrategias: e.target.value,
                          }))
                        }
                      />
                    </Field>
                  </div>
                  <Field
                    label="Profissionais envolvidos"
                    hint="Quem planeja e quem aplica"
                  >
                    <textarea
                      className={areaClass}
                      value={area.profissionais_envolvidos}
                      onChange={(e) =>
                        setArea((a) => ({
                          ...a,
                          profissionais_envolvidos: e.target.value,
                        }))
                      }
                    />
                  </Field>
                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={saving}
                      className="rounded-lg bg-school-500 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
                    >
                      Salvar área geral
                    </button>
                  </div>
                </form>
              </section>

              <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-panel">
                <h2 className="text-sm font-semibold text-ink">
                  Campos de experiência
                </h2>
                <p className="mt-1 text-xs text-muted">
                  BNCC · Educação Infantil. Vários objetivos por campo. “Como ensinar”
                  é a âncora futura das adaptações do app do professor.
                </p>

                <div className="mt-4 space-y-2">
                  {CAMPOS_EXPERIENCIA.map((campo) => {
                    const aberto = campoAberto === campo.id
                    const objs = (objetivosPorCampo.get(campo.id) || []).filter(
                      (o) => o.ativo !== false,
                    )
                    const inativos = (objetivosPorCampo.get(campo.id) || []).filter(
                      (o) => o.ativo === false,
                    )
                    const form = addFormPorCampo[campo.id] || emptyNovoObj
                    return (
                      <div
                        key={campo.id}
                        className="overflow-hidden rounded-lg border border-slate-200"
                      >
                        <button
                          type="button"
                          onClick={() =>
                            setCampoAberto((prev) =>
                              prev === campo.id ? null : campo.id,
                            )
                          }
                          className="flex w-full items-center justify-between gap-2 bg-slate-50 px-4 py-3 text-left"
                        >
                          <span className="text-sm font-semibold text-ink">
                            {campo.label}
                          </span>
                          <span className="text-xs text-muted">
                            {objs.length} ativo{objs.length === 1 ? '' : 's'}
                            {aberto ? ' · ▲' : ' · ▼'}
                          </span>
                        </button>

                        {aberto ? (
                          <div className="space-y-4 border-t border-slate-100 bg-white p-4">
                            {objs.length === 0 ? (
                              <p className="text-xs text-muted">
                                Nenhum objetivo ativo neste campo.
                              </p>
                            ) : (
                              objs.map((obj) => {
                                const d = draftsObj[obj.id] || emptyNovoObj
                                return (
                                  <div
                                    key={obj.id}
                                    className="space-y-3 rounded-lg border border-slate-100 p-3"
                                  >
                                    <Field label="Objetivo">
                                      <textarea
                                        className={areaClass}
                                        value={d.objetivo}
                                        onChange={(e) =>
                                          patchDraft(obj.id, {
                                            objetivo: e.target.value,
                                          })
                                        }
                                      />
                                    </Field>
                                    <Field label="Currículo / habilidades">
                                      <textarea
                                        className={areaClass}
                                        value={d.curriculo_habilidades}
                                        onChange={(e) =>
                                          patchDraft(obj.id, {
                                            curriculo_habilidades: e.target.value,
                                          })
                                        }
                                      />
                                    </Field>
                                    <Field label="Como ensinar">
                                      <textarea
                                        className={areaClass}
                                        value={d.estrategias_ensino}
                                        onChange={(e) =>
                                          patchDraft(obj.id, {
                                            estrategias_ensino: e.target.value,
                                          })
                                        }
                                      />
                                    </Field>
                                    <Field label="Prazo" hint='Ex.: "3 meses"'>
                                      <input
                                        className={inputClass}
                                        value={d.prazo}
                                        onChange={(e) =>
                                          patchDraft(obj.id, {
                                            prazo: e.target.value,
                                          })
                                        }
                                      />
                                    </Field>
                                    <div className="flex flex-wrap gap-2">
                                      <button
                                        type="button"
                                        disabled={saving}
                                        onClick={() => salvarObjetivo(obj.id)}
                                        className="rounded-lg bg-school-500 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
                                      >
                                        Salvar objetivo
                                      </button>
                                      <button
                                        type="button"
                                        disabled={saving}
                                        onClick={() => desativarObjetivo(obj.id)}
                                        className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-muted hover:text-red-700"
                                      >
                                        Desativar
                                      </button>
                                    </div>
                                  </div>
                                )
                              })
                            )}

                            {inativos.length > 0 ? (
                              <p className="text-xs text-muted">
                                {inativos.length} objetivo
                                {inativos.length === 1 ? '' : 's'} inativo
                                {inativos.length === 1 ? '' : 's'} (não exibido
                                {inativos.length === 1 ? '' : 's'} acima).
                              </p>
                            ) : null}

                            <form
                              onSubmit={(e) => adicionarObjetivo(campo.id, e)}
                              className="space-y-3 rounded-lg border border-dashed border-school-200 bg-school-50/40 p-3"
                            >
                              <p className="text-xs font-semibold uppercase tracking-wide text-school-800">
                                + Adicionar objetivo
                              </p>
                              <Field label="Objetivo">
                                <textarea
                                  className={areaClass}
                                  value={form.objetivo}
                                  onChange={(e) =>
                                    setAddFormPorCampo((prev) => ({
                                      ...prev,
                                      [campo.id]: {
                                        ...(prev[campo.id] || emptyNovoObj),
                                        objetivo: e.target.value,
                                      },
                                    }))
                                  }
                                  required
                                />
                              </Field>
                              <Field label="Currículo / habilidades">
                                <textarea
                                  className={areaClass}
                                  value={form.curriculo_habilidades}
                                  onChange={(e) =>
                                    setAddFormPorCampo((prev) => ({
                                      ...prev,
                                      [campo.id]: {
                                        ...(prev[campo.id] || emptyNovoObj),
                                        curriculo_habilidades: e.target.value,
                                      },
                                    }))
                                  }
                                />
                              </Field>
                              <Field label="Como ensinar">
                                <textarea
                                  className={areaClass}
                                  value={form.estrategias_ensino}
                                  onChange={(e) =>
                                    setAddFormPorCampo((prev) => ({
                                      ...prev,
                                      [campo.id]: {
                                        ...(prev[campo.id] || emptyNovoObj),
                                        estrategias_ensino: e.target.value,
                                      },
                                    }))
                                  }
                                />
                              </Field>
                              <Field label="Prazo">
                                <input
                                  className={inputClass}
                                  value={form.prazo}
                                  onChange={(e) =>
                                    setAddFormPorCampo((prev) => ({
                                      ...prev,
                                      [campo.id]: {
                                        ...(prev[campo.id] || emptyNovoObj),
                                        prazo: e.target.value,
                                      },
                                    }))
                                  }
                                />
                              </Field>
                              <button
                                type="submit"
                                disabled={saving}
                                className="rounded-lg border border-school-500 bg-white px-3 py-2 text-sm font-semibold text-school-800 disabled:opacity-60"
                              >
                                Adicionar
                              </button>
                            </form>
                          </div>
                        ) : null}
                      </div>
                    )
                  })}
                </div>
              </section>
            </div>
          )}
        </div>
      )}
      </>
      ) : null}
    </div>
  )
}
