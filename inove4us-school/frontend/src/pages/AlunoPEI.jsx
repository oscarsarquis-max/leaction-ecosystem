import { useCallback, useEffect, useMemo, useState } from 'react'

const INSTITUICAO_ID =
  import.meta.env.VITE_INSTITUICAO_ID || 'a1111111-1111-4111-8111-111111111111'

const inputClass =
  'w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100'

/**
 * Ciclo Vivo do PEI — adaptações por metodologia + sugestões da trincheira.
 */
export default function AlunoPEI() {
  const [lista, setLista] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [metodologias, setMetodologias] = useState([])
  const [metNome, setMetNome] = useState('')
  const [passos, setPassos] = useState('')
  const [curadoria, setCuradoria] = useState([])
  const [aba, setAba] = useState('adaptacoes') // adaptacoes | trincheira
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')

  const adaptMap = useMemo(() => {
    const m = new Map()
    for (const a of detail?.adaptacoes || []) {
      m.set(String(a.metodologia_nome || '').toLowerCase(), a)
    }
    return m
  }, [detail])

  const carregarLista = useCallback(async () => {
    const res = await fetch('/api/pedagogico/pei/alunos', { credentials: 'include' })
    const body = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(body.error || 'Falha ao listar PEIs')
    setLista(body.items || [])
    return body.items || []
  }, [])

  const carregarMetodologias = useCallback(async () => {
    const res = await fetch(`/api/instituicoes/${INSTITUICAO_ID}/metodologias`, {
      credentials: 'include',
    })
    const body = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(body.error || 'Falha ao carregar metodologias')
    const items = Array.isArray(body) ? body : body.items || body.metodologias || []
    setMetodologias(items)
    if (!metNome && items[0]?.nome) setMetNome(items[0].nome)
  }, [metNome])

  const carregarDetalhe = useCallback(async (id) => {
    const [dRes, cRes] = await Promise.all([
      fetch(`/api/pedagogico/pei/${id}`, { credentials: 'include' }),
      fetch(`/api/pedagogico/pei/${id}/curadoria`, { credentials: 'include' }),
    ])
    const dBody = await dRes.json().catch(() => ({}))
    const cBody = await cRes.json().catch(() => ({}))
    if (!dRes.ok) throw new Error(dBody.error || 'Falha ao abrir PEI')
    setDetail(dBody)
    setCuradoria(cRes.ok ? cBody.items || [] : [])
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError('')
      try {
        const [items] = await Promise.all([carregarLista(), carregarMetodologias()])
        if (cancelled) return
        if (items[0]?.id) {
          setSelectedId(items[0].id)
          await carregarDetalhe(items[0].id)
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
  }, [carregarLista, carregarMetodologias, carregarDetalhe])

  useEffect(() => {
    if (!metNome || !detail) return
    const hit = adaptMap.get(metNome.toLowerCase())
    setPassos(hit?.passos_customizados || '')
  }, [metNome, detail, adaptMap])

  async function selecionar(id) {
    setSelectedId(id)
    setFeedback('')
    setError('')
    setBusy(true)
    try {
      await carregarDetalhe(id)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function gerarIa() {
    if (!selectedId || !metNome) return
    setBusy(true)
    setError('')
    setFeedback('')
    try {
      const res = await fetch(
        `/api/pedagogico/pei/${selectedId}/metodologia/${encodeURIComponent(metNome)}/gerar`,
        { method: 'POST', credentials: 'include' },
      )
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha na geração por IA')
      setPassos(body.item?.passos_customizados || '')
      setFeedback(body.message || 'Adaptação gerada por IA.')
      await carregarDetalhe(selectedId)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function salvarOficial() {
    if (!selectedId || !metNome) return
    setBusy(true)
    setError('')
    setFeedback('')
    try {
      const res = await fetch(
        `/api/pedagogico/pei/${selectedId}/metodologia/${encodeURIComponent(metNome)}`,
        {
          method: 'PUT',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ passos_customizados: passos }),
        },
      )
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha ao salvar')
      setFeedback(body.message || 'Adaptação salva e enviada ao B2C.')
      await carregarDetalhe(selectedId)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function incorporar(id) {
    setBusy(true)
    setError('')
    try {
      const res = await fetch(`/api/pedagogico/curadoria_pei/${id}/incorporar`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha ao incorporar')
      setFeedback(body.message || 'Sugestão incorporada.')
      setCuradoria((prev) => prev.filter((c) => c.id !== id))
      if (selectedId) await carregarDetalhe(selectedId)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return <p className="text-sm text-muted">Carregando PEIs dos alunos…</p>
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-ink">Ciclo Vivo do PEI</h2>
        <p className="mt-1 text-sm text-muted">
          Adapte cada metodologia ao perfil do aluno (IA + curadoria da trincheira).
        </p>
      </div>

      {error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
      {feedback ? <p className="text-sm text-school-700">{feedback}</p> : null}

      {lista.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-muted">
          Nenhum PEI individualizado cadastrado. Cadastre alunos e vincule a um plano
          geral (school_pei_individualizado) para usar o ciclo vivo.
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[16rem_1fr]">
          <aside className="space-y-1 rounded-xl border border-slate-200 bg-white p-2 shadow-panel">
            {lista.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => selecionar(item.id)}
                className={[
                  'w-full rounded-lg px-3 py-2 text-left text-sm transition',
                  selectedId === item.id
                    ? 'bg-school-500 text-white'
                    : 'hover:bg-slate-50 text-ink',
                ].join(' ')}
              >
                <span className="font-semibold">{item.aluno_nome}</span>
                <span
                  className={[
                    'mt-0.5 block text-xs',
                    selectedId === item.id ? 'text-white/80' : 'text-muted',
                  ].join(' ')}
                >
                  {item.tipo_neurodivergencia}
                </span>
              </button>
            ))}
          </aside>

          <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-panel sm:p-5">
            {detail?.pei ? (
              <>
                <div>
                  <h3 className="text-base font-semibold text-ink">
                    {detail.pei.aluno_nome}
                  </h3>
                  <p className="text-sm text-muted">
                    {detail.pei.tipo_neurodivergencia}
                    {detail.pei.matricula ? ` · matrícula ${detail.pei.matricula}` : ''}
                  </p>
                </div>

                <div className="flex flex-wrap gap-2 border-b border-slate-100 pb-2">
                  {[
                    { id: 'adaptacoes', label: 'Adaptações por metodologia' },
                    {
                      id: 'trincheira',
                      label: `Sugestões da Trincheira (${curadoria.length})`,
                    },
                  ].map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setAba(t.id)}
                      className={[
                        'rounded-lg px-3 py-1.5 text-xs font-semibold',
                        aba === t.id
                          ? 'bg-amber-500 text-white'
                          : 'bg-slate-100 text-slate-700',
                      ].join(' ')}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>

                {aba === 'adaptacoes' ? (
                  <div className="space-y-3">
                    <label className="block text-sm">
                      <span className="mb-1 block text-xs font-semibold uppercase text-muted">
                        Metodologia
                      </span>
                      <select
                        className={inputClass}
                        value={metNome}
                        onChange={(e) => setMetNome(e.target.value)}
                      >
                        {metodologias.length === 0 ? (
                          <option value="">Nenhuma metodologia no catálogo</option>
                        ) : (
                          metodologias.map((m) => (
                            <option key={m.metodologia_id || m.nome} value={m.nome}>
                              {m.nome}
                            </option>
                          ))
                        )}
                      </select>
                    </label>
                    <label className="block text-sm">
                      <span className="mb-1 block text-xs font-semibold uppercase text-muted">
                        Passos customizados (PEI × metodologia)
                      </span>
                      <textarea
                        className={`${inputClass} min-h-[10rem] resize-y`}
                        value={passos}
                        onChange={(e) => setPassos(e.target.value)}
                        placeholder="Gere com IA ou escreva os passos oficiais da escola…"
                      />
                    </label>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={busy || !metNome}
                        onClick={gerarIa}
                        className="rounded-lg border border-violet-300 bg-violet-50 px-4 py-2 text-sm font-semibold text-violet-900 hover:bg-violet-100 disabled:opacity-60"
                      >
                        {busy ? '…' : 'Gerar com IA'}
                      </button>
                      <button
                        type="button"
                        disabled={busy || !metNome || !passos.trim()}
                        onClick={salvarOficial}
                        className="rounded-lg bg-school-500 px-4 py-2 text-sm font-semibold text-white hover:bg-school-600 disabled:opacity-60"
                      >
                        Salvar versão oficial
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {curadoria.length === 0 ? (
                      <p className="text-sm text-muted">
                        Nenhuma sugestão pendente deste aluno.
                      </p>
                    ) : (
                      curadoria.map((item) => (
                        <article
                          key={item.id}
                          className="rounded-lg border border-amber-100 bg-amber-50/50 p-3"
                        >
                          <p className="text-xs font-semibold uppercase text-amber-900">
                            {item.metodologia_nome || 'Metodologia'}
                          </p>
                          <p className="mt-2 text-sm text-ink">
                            {item.pei_adaptation_text || '—'}
                          </p>
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => incorporar(item.id)}
                            className="mt-3 rounded-lg bg-school-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-school-600 disabled:opacity-60"
                          >
                            Incorporar à Adaptação Base
                          </button>
                        </article>
                      ))
                    )}
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm text-muted">Selecione um aluno.</p>
            )}
          </section>
        </div>
      )}
    </div>
  )
}
