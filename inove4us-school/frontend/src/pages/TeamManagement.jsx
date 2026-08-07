import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '../lib/auth'

const FALLBACK_INSTITUICAO_ID =
  import.meta.env.VITE_INSTITUICAO_ID || 'a1111111-1111-4111-8111-111111111111'

function formatDate(iso) {
  if (!iso) return '—'
  const [y, m, d] = String(iso).slice(0, 10).split('-')
  return `${d}/${m}/${y}`
}

function StatusBadge({ status }) {
  const active = status === 'Ativo'
  const pending = status === 'Pendente'
  return (
    <span
      className={[
        'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold',
        active
          ? 'bg-school-50 text-school-700'
          : pending
            ? 'bg-amber-50 text-amber-800'
            : 'bg-slate-100 text-slate-600',
      ].join(' ')}
    >
      {status}
    </span>
  )
}

function PedagogicoBadge({ ped }) {
  if (!ped) return <span className="text-xs text-muted">—</span>
  const codigo = ped.codigo || 'sem_planos'
  const tone =
    codigo === 'em_dia'
      ? 'bg-school-50 text-school-700'
      : codigo === 'pendencias'
        ? 'bg-amber-50 text-amber-800'
        : codigo === 'reprovacoes'
          ? 'bg-red-50 text-red-700'
          : 'bg-slate-100 text-slate-600'
  return (
    <span className="inline-flex flex-col gap-0.5">
      <span
        className={[
          'inline-flex w-fit items-center rounded-md px-2 py-0.5 text-xs font-semibold',
          tone,
        ].join(' ')}
      >
        {ped.label}
      </span>
      {ped.detalhe ? <span className="text-[11px] text-muted">{ped.detalhe}</span> : null}
    </span>
  )
}

function LicenseCard({ label, value, hint }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-panel">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-ink">
        {value == null ? '—' : value}
      </p>
      {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
    </div>
  )
}

function MiniStat({ label, value }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-0.5 text-lg font-semibold tabular-nums text-ink">{value ?? '—'}</p>
    </div>
  )
}

function tipoAulaLabel(t) {
  if (t === 'desafio') return 'Desafio'
  if (t === 'dia_a_dia') return 'Dia a Dia'
  return t || '—'
}

function statusPlanoLabel(s) {
  const map = { pendente: 'Pendente', aprovado: 'Aprovado', reprovado: 'Reprovado' }
  return map[s] || s
}

function formatMoney(value, currency = 'BRL') {
  const n = Number(value)
  if (!Number.isFinite(n)) return '—'
  try {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency }).format(n)
  } catch {
    return `R$ ${n.toFixed(2)}`
  }
}

/** Nomes comerciais exibidos ao gestor (nunca códigos internos). */
const PACOTES_LICENCA = {
  'school-starter-50': 'Escola Inicial (50 licenças)',
  'school-growth-100': 'Escola Crescimento (100 licenças)',
}

function nomePacoteLicenca(codigo) {
  if (!codigo) return null
  return PACOTES_LICENCA[codigo] || null
}

function BillingModal({ open, onClose, onPaidHint }) {
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [buyingSku, setBuyingSku] = useState('')

  useEffect(() => {
    if (!open) return undefined
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError('')
      try {
        const res = await fetch('/api/billing/plans', { credentials: 'include' })
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(body.error || 'Não foi possível carregar os planos')
        if (!cancelled) setPlans(Array.isArray(body.plans) ? body.plans : [])
      } catch (err) {
        if (!cancelled) setError(err.message || 'Erro ao carregar planos')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [open])

  async function handleBuy(sku) {
    setBuyingSku(sku)
    setError('')
    try {
      const res = await fetch('/api/billing/checkout', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sku_id: sku, sku }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha ao iniciar o pagamento')
      const url = body.checkout_url || body.url
      if (!url) throw new Error('O Action Hub não retornou o link de pagamento')
      onPaidHint?.()
      window.location.href = url
    } catch (err) {
      setError(err.message || 'Erro ao iniciar o pagamento')
      setBuyingSku('')
    }
  }

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Faturamento — comprar licenças"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-slate-200 bg-white p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-ink">Faturamento · Licenças</h2>
            <p className="mt-1 text-sm text-muted">
              Pacotes comerciais do Action Hub para a instituição. Após o pagamento, as licenças
              são creditadas automaticamente.
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

        {loading ? <p className="text-sm text-muted">Carregando planos…</p> : null}
        {error ? (
          <p className="mb-3 text-sm text-red-700" role="alert">
            {error}
          </p>
        ) : null}

        {!loading && plans.length === 0 && !error ? (
          <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm text-muted">
            Nenhum plano ativo no Action Hub para esta instituição.
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {plans.map((plan) => {
              const sku = plan.sku || plan.sku_id
              const seats = plan.licenses_granted
              return (
                <article
                  key={sku || plan.id}
                  className={[
                    'flex flex-col rounded-xl border p-4',
                    plan.recommended
                      ? 'border-school-400 bg-school-50/40'
                      : 'border-slate-200 bg-white',
                  ].join(' ')}
                >
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <h3 className="font-semibold text-ink">{plan.name}</h3>
                    {plan.recommended ? (
                      <span className="rounded bg-violet-600 px-2 py-0.5 text-[10px] font-semibold uppercase text-white">
                        Recomendado
                      </span>
                    ) : null}
                  </div>
                  <p className="text-2xl font-semibold tabular-nums text-ink">
                    {formatMoney(plan.price, plan.currency)}
                  </p>
                  <p className="mt-1 text-sm text-school-700">
                    {seats != null ? `${seats} licenças de professor` : 'Licenças conforme o plano'}
                  </p>
                  <ul className="mt-3 flex-1 space-y-1 text-xs text-muted">
                    {(plan.features || []).map((f) => (
                      <li key={f}>· {f}</li>
                    ))}
                  </ul>
                  <button
                    type="button"
                    disabled={Boolean(buyingSku) || !sku}
                    onClick={() => handleBuy(sku)}
                    className="mt-4 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-60"
                  >
                    {buyingSku === sku ? 'Redirecionando…' : 'Comprar licenças'}
                  </button>
                </article>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default function TeamManagement() {
  const { user } = useAuth()
  const instituicaoId = user?.instituicao_id || FALLBACK_INSTITUICAO_ID

  const [email, setEmail] = useState('')
  const [licencas, setLicencas] = useState(null)
  const [team, setTeam] = useState([])
  const [feedback, setFeedback] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [billingOpen, setBillingOpen] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [radio, setRadio] = useState(null)
  const [radioLoading, setRadioLoading] = useState(false)
  const [radioError, setRadioError] = useState('')
  const [notaForm, setNotaForm] = useState({ nota: '', referencia: '', observacao: '' })

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`/api/instituicoes/${instituicaoId}/equipe`, {
        credentials: 'include',
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha ao carregar equipe')
      setLicencas(body.licencas || null)
      setTeam(Array.isArray(body.membros) ? body.membros : [])
    } catch (err) {
      setError(err.message || 'Erro ao carregar')
    } finally {
      setLoading(false)
    }
  }, [instituicaoId])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('paid') === '1') {
      setFeedback('Pagamento concluído no Hub. Atualizando licenças…')
      load().finally(() => {
        params.delete('paid')
        const next = `${window.location.pathname}${params.toString() ? `?${params}` : ''}`
        window.history.replaceState({}, '', next)
      })
    }
  }, [load])

  const loadRadiografia = useCallback(
    async (vinculoId) => {
      setRadioLoading(true)
      setRadioError('')
      setRadio(null)
      try {
        const res = await fetch(
          `/api/instituicoes/${instituicaoId}/equipe/${vinculoId}/radiografia`,
          { credentials: 'include' },
        )
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(body.error || 'Falha ao carregar o status pedagógico')
        setRadio(body)
      } catch (err) {
        setRadioError(err.message || 'Erro')
      } finally {
        setRadioLoading(false)
      }
    },
    [instituicaoId],
  )

  useEffect(() => {
    if (selectedId) loadRadiografia(selectedId)
  }, [selectedId, loadRadiografia])

  const ordered = useMemo(
    () =>
      [...team].sort((a, b) => {
        if (a.status !== b.status) return a.status === 'Pendente' ? -1 : 1
        return String(b.convidadoEm || '').localeCompare(String(a.convidadoEm || ''))
      }),
    [team],
  )

  const atLimit = Boolean(licencas?.no_limite)
  const selected = team.find((t) => t.id === selectedId)

  async function handleInvite(e) {
    e.preventDefault()
    setFeedback('')
    setError('')
    setBusy(true)
    try {
      const res = await fetch(`/api/instituicoes/${instituicaoId}/equipe/convites`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json; charset=utf-8' },
        body: JSON.stringify({ email: email.trim() }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) {
        if (body.licencas) setLicencas(body.licencas)
        throw new Error(body.error || 'Não foi possível convidar')
      }
      if (body.licencas) setLicencas(body.licencas)
      if (body.membro) {
        setTeam((prev) => [body.membro, ...prev.filter((m) => m.id !== body.membro.id)])
      }
      setEmail('')
      setFeedback(`Convite registrado para ${body.membro?.email || email}.`)
    } catch (err) {
      setError(err.message || 'Erro ao convidar')
    } finally {
      setBusy(false)
    }
  }

  async function handleRevoke(id) {
    const row = team.find((t) => t.id === id)
    if (!row) return
    if (!window.confirm(`Revogar vínculo de ${row.email || 'este professor'}?`)) return
    setBusy(true)
    setError('')
    try {
      const res = await fetch(`/api/instituicoes/${instituicaoId}/equipe/${id}/revogar`, {
        method: 'POST',
        credentials: 'include',
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha ao revogar')
      if (body.licencas) setLicencas(body.licencas)
      setTeam((prev) => prev.filter((t) => t.id !== id))
      if (selectedId === id) {
        setSelectedId(null)
        setRadio(null)
      }
      setFeedback(`Vínculo de ${body.email || row.email} revogado.`)
    } catch (err) {
      setError(err.message || 'Erro ao revogar')
    } finally {
      setBusy(false)
    }
  }

  async function handleDeclararNota(e) {
    e.preventDefault()
    if (!selectedId) return
    setBusy(true)
    setRadioError('')
    try {
      const res = await fetch(
        `/api/instituicoes/${instituicaoId}/equipe/${selectedId}/avaliacoes`,
        {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json; charset=utf-8' },
          body: JSON.stringify({
            nota: Number(notaForm.nota),
            referencia: notaForm.referencia.trim(),
            observacao: notaForm.observacao.trim() || null,
            gestor_id: user?.id || null,
          }),
        },
      )
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Falha ao declarar nota')
      setNotaForm({ nota: '', referencia: '', observacao: '' })
      await loadRadiografia(selectedId)
      setFeedback('Avaliação declarada.')
    } catch (err) {
      setRadioError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Minha Equipe</h1>
        <p className="mt-1 text-sm text-muted">
          Licenças, convites e status pedagógico do professor: recursos, entrega,
          metodologias, disciplinas e desempenho declarado.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <LicenseCard label="Licenças contratadas" value={licencas?.licencas_contratadas} hint="Definidas no plano da escola" />
        <LicenseCard label="Licenças em uso" value={licencas?.licencas_em_uso} hint="Professores com vínculo ativo" />
        <LicenseCard
          label="Licenças disponíveis"
          value={licencas?.licencas_disponiveis}
          hint={atLimit ? 'Limite atingido' : 'Livres para novos convites'}
        />
      </div>

      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-panel sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-ink">Faturamento · Licenças</p>
          <p className="mt-0.5 text-xs text-muted">
            Compre os pacotes Escola Inicial (50) ou Escola Crescimento (100) pelo Action Hub.
            As licenças entram automaticamente após o pagamento.
            {licencas?.sku_ultimo
              ? ` Último pacote: ${nomePacoteLicenca(licencas.sku_ultimo) || 'contratado'}.`
              : ''}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setBillingOpen(true)}
          className="inline-flex shrink-0 items-center justify-center rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-700"
        >
          Comprar licenças
        </button>
      </div>

      <BillingModal
        open={billingOpen}
        onClose={() => setBillingOpen(false)}
        onPaidHint={() =>
          setFeedback('Abrindo pagamento no Action Hub… Ao retornar, as licenças serão atualizadas.')
        }
      />

      <form
        onSubmit={handleInvite}
        className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-panel sm:flex-row sm:items-end"
      >
        <label className="min-w-0 flex-1">
          <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
            E-mail do Professor
          </span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="professor@escola.edu.br"
            disabled={busy || atLimit}
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100 disabled:opacity-60"
          />
        </label>
        <button
          type="submit"
          disabled={busy || atLimit}
          className="shrink-0 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-60"
        >
          Convidar Professor
        </button>
      </form>

      {feedback ? <p className="text-sm text-school-700">{feedback}</p> : null}
      {error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}

      {/* Empilha até xl: sidebar admin (320px) + tabela larga + painel conflitam em lg */}
      <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(300px,380px)]">
        <div className="min-w-0 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[32rem] text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-4 py-3">E-mail</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Convite</th>
                  <th className="px-4 py-3">Ações</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-muted">
                      Carregando…
                    </td>
                  </tr>
                ) : ordered.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-muted">
                      Nenhum professor vinculado ainda.
                    </td>
                  </tr>
                ) : (
                  ordered.map((row) => (
                    <tr
                      key={row.id}
                      className={[
                        'border-b border-slate-100 last:border-0',
                        selectedId === row.id ? 'bg-school-50/60' : '',
                      ].join(' ')}
                    >
                      <td className="px-4 py-3 font-medium text-ink">{row.email || '—'}</td>
                      <td className="px-4 py-3">
                        <StatusBadge status={row.status} />
                      </td>
                      <td className="px-4 py-3 tabular-nums text-muted">
                        {formatDate(row.convidadoEm)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => setSelectedId(row.id)}
                            className="rounded-md border border-violet-200 bg-violet-50 px-2.5 py-1.5 text-xs font-semibold text-violet-700 hover:bg-violet-100"
                          >
                            Status pedagógico
                          </button>
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => handleRevoke(row.id)}
                            className="rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-muted hover:border-red-200 hover:bg-red-50 hover:text-red-700 disabled:opacity-60"
                          >
                            Revogar
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <aside className="min-w-0 rounded-xl border border-slate-200 bg-white p-4 shadow-panel xl:sticky xl:top-4 xl:self-start">
          {!selectedId ? (
            <p className="text-sm text-muted">
              Selecione <span className="font-medium text-ink">Status pedagógico</span> em um
              professor para ver o detalhe.
            </p>
          ) : radioLoading ? (
            <div className="space-y-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                  Status pedagógico
                </p>
                <h2 className="mt-1 text-lg font-semibold text-ink">
                  {selected?.email || 'Professor'}
                </h2>
                <div className="mt-2">
                  <PedagogicoBadge ped={selected?.status_pedagogico} />
                </div>
              </div>
              <p className="text-sm text-muted">Carregando detalhes…</p>
            </div>
          ) : radioError ? (
            <div className="space-y-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                  Status pedagógico
                </p>
                <h2 className="mt-1 text-lg font-semibold text-ink">
                  {selected?.email || 'Professor'}
                </h2>
                <div className="mt-2">
                  <PedagogicoBadge ped={selected?.status_pedagogico} />
                </div>
              </div>
              <p className="text-sm text-red-700">{radioError}</p>
            </div>
          ) : radio ? (
            <div className="space-y-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                  Status pedagógico
                </p>
                <h2 className="mt-1 text-lg font-semibold text-ink">
                  {selected?.email || radio.professor?.email || 'Professor'}
                </h2>
                <div className="mt-2">
                  <PedagogicoBadge
                    ped={selected?.status_pedagogico || radio.status_pedagogico}
                  />
                </div>
              </div>

              <section>
                <h3 className="text-sm font-semibold text-ink">Recursos recebidos</h3>
                <ul className="mt-2 space-y-1.5">
                  {(radio.recursos_recebidos || []).length === 0 ? (
                    <li className="text-xs text-muted">Nenhum recurso registrado.</li>
                  ) : (
                    radio.recursos_recebidos.map((r, i) => (
                      <li key={r.id || i} className="rounded-md border border-slate-100 px-2.5 py-1.5 text-xs">
                        <span className="font-medium text-ink">{r.titulo}</span>
                        <span className="ml-1 text-muted">· {r.tipo}</span>
                        {r.detalhe ? <p className="mt-0.5 text-muted">{r.detalhe}</p> : null}
                      </li>
                    ))
                  )}
                </ul>
                {(radio.metodologias_liberadas_escola || []).length > 0 ? (
                  <p className="mt-2 text-[11px] text-muted">
                    Repertório da escola liberado: {radio.metodologias_liberadas_escola.length}{' '}
                    metodologia(s).
                  </p>
                ) : null}
              </section>

              <section>
                <h3 className="text-sm font-semibold text-ink">O que entrega</h3>
                <div className="mt-2 grid grid-cols-2 gap-2">
                  <MiniStat label="Planos" value={radio.entrega?.planos_total} />
                  <MiniStat label="Aprovados" value={radio.entrega?.aprovados} />
                  <MiniStat label="Pendentes" value={radio.entrega?.pendentes} />
                  <MiniStat label="Metodologias" value={radio.entrega?.metodologias_distintas} />
                  <MiniStat label="Dia a Dia" value={radio.entrega?.dia_a_dia} />
                  <MiniStat label="Desafio" value={radio.entrega?.desafio} />
                </div>
              </section>

              <section>
                <h3 className="text-sm font-semibold text-ink">Metodologias usadas</h3>
                <p className="mt-1 text-xs text-muted">
                  {(radio.metodologias_usadas || []).length === 0
                    ? 'Ainda sem uso registrado nos planos espelhados.'
                    : radio.metodologias_usadas.join(' · ')}
                </p>
              </section>

              <section>
                <h3 className="text-sm font-semibold text-ink">Disciplinas sob comando</h3>
                <ul className="mt-2 space-y-1">
                  {(radio.disciplinas || []).length === 0 ? (
                    <li className="text-xs text-muted">Nenhuma disciplina vinculada.</li>
                  ) : (
                    radio.disciplinas.map((d, i) => (
                      <li key={i} className="text-xs text-ink">
                        <span className="font-medium">{d.disciplina}</span>
                        <span className="text-muted"> · {d.turma}</span>
                        {!d.ativo ? <span className="text-muted"> (inativo)</span> : null}
                      </li>
                    ))
                  )}
                </ul>
              </section>

              <section>
                <h3 className="text-sm font-semibold text-ink">Desempenho declarado</h3>
                {radio.avaliacao?.atual ? (
                  <p className="mt-1 text-sm text-ink">
                    Nota atual:{' '}
                    <span className="text-xl font-semibold tabular-nums">
                      {radio.avaliacao.atual.nota.toFixed(1)}
                    </span>
                    <span className="ml-1 text-xs text-muted">
                      ({radio.avaliacao.atual.referencia} ·{' '}
                      {formatDate(radio.avaliacao.atual.declarado_em)})
                    </span>
                  </p>
                ) : (
                  <p className="mt-1 text-xs text-muted">Nenhuma nota declarada ainda.</p>
                )}
                {(radio.avaliacao?.historico || []).length > 1 ? (
                  <ul className="mt-2 space-y-1 border-t border-slate-100 pt-2">
                    {radio.avaliacao.historico.slice(1).map((a) => (
                      <li key={a.id} className="flex justify-between text-xs text-muted">
                        <span>
                          {a.referencia} · {formatDate(a.declarado_em)}
                        </span>
                        <span className="font-semibold tabular-nums text-ink">
                          {a.nota.toFixed(1)}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : null}
                <form onSubmit={handleDeclararNota} className="mt-3 space-y-2 border-t border-slate-100 pt-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">
                    Declarar nota
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      required
                      type="number"
                      min="0"
                      max="10"
                      step="0.1"
                      placeholder="Nota 0–10"
                      value={notaForm.nota}
                      onChange={(e) => setNotaForm({ ...notaForm, nota: e.target.value })}
                      className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm outline-none focus:border-school-500"
                    />
                    <input
                      required
                      placeholder="Ref. (ex. 2026-1)"
                      value={notaForm.referencia}
                      onChange={(e) => setNotaForm({ ...notaForm, referencia: e.target.value })}
                      className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm outline-none focus:border-school-500"
                    />
                  </div>
                  <input
                    placeholder="Observação (opcional)"
                    value={notaForm.observacao}
                    onChange={(e) => setNotaForm({ ...notaForm, observacao: e.target.value })}
                    className="w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm outline-none focus:border-school-500"
                  />
                  <button
                    type="submit"
                    disabled={busy}
                    className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-700 disabled:opacity-60"
                  >
                    Salvar avaliação
                  </button>
                </form>
              </section>

              <section>
                <h3 className="text-sm font-semibold text-ink">
                  Execuções na metodologia da escola
                </h3>
                <p className="mt-0.5 text-[11px] text-muted">
                  Planos espelhados da plataforma do professor usando o repertório institucional.
                </p>
                <ul className="mt-2 max-h-56 space-y-2 overflow-y-auto">
                  {(radio.execucoes || []).length === 0 ? (
                    <li className="text-xs text-muted">Sem registros de execução ainda.</li>
                  ) : (
                    radio.execucoes.map((ex) => (
                      <li key={ex.id} className="rounded-md border border-slate-100 px-2.5 py-2 text-xs">
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                          <span className="font-medium text-ink">{ex.metodologia}</span>
                          <span className="text-muted">{tipoAulaLabel(ex.tipo_aula)}</span>
                          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-700">
                            {statusPlanoLabel(ex.status)}
                          </span>
                        </div>
                        <p className="mt-0.5 text-muted">
                          {formatDate(ex.semana_referencia)} · {ex.turma}
                          {ex.desafio_titulo ? ` · ${ex.desafio_titulo}` : ''}
                        </p>
                        {ex.resumo ? (
                          <p className="mt-1 line-clamp-2 text-ink/80">{ex.resumo}</p>
                        ) : null}
                      </li>
                    ))
                  )}
                </ul>
              </section>
            </div>
          ) : null}
        </aside>
      </div>
    </div>
  )
}
