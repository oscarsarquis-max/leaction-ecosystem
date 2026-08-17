import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '../lib/auth'

const STATUS_LABEL = {
  preparada: 'Preparada',
  em_andamento: 'Em andamento',
  pausada: 'Pausada',
  concluida: 'Concluída',
  cancelada: 'Cancelada',
}

const RESULTADO_LABEL = {
  passou: 'Passou',
  travou: 'Travou',
  nao_concluido: 'Não concluído',
}

function formatDate(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR')
  } catch {
    return iso
  }
}

function formatDuration(seconds) {
  const s = Math.max(0, Number(seconds) || 0)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const r = s % 60
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`
  if (m > 0) return `${m}m ${String(r).padStart(2, '0')}s`
  return `${r}s`
}

function StatusPill({ status }) {
  const tone =
    status === 'em_andamento'
      ? 'bg-school-50 text-school-700'
      : status === 'pausada'
        ? 'bg-amber-50 text-amber-800'
        : status === 'concluida'
          ? 'bg-slate-100 text-slate-700'
          : status === 'cancelada'
            ? 'bg-red-50 text-red-700'
            : 'bg-slate-50 text-slate-600'
  return (
    <span className={`inline-flex rounded-md px-2 py-0.5 text-xs font-semibold ${tone}`}>
      {STATUS_LABEL[status] || status}
    </span>
  )
}

export default function HomologacaoAdmin() {
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('sessao') || ''

  const [me, setMe] = useState(null)
  const [sessoes, setSessoes] = useState([])
  const [detail, setDetail] = useState(null)
  const [eventos, setEventos] = useState([])
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')
  const [busy, setBusy] = useState(false)

  const [profNome, setProfNome] = useState('')
  const [profPapel, setProfPapel] = useState('participante')
  const [eventoTexto, setEventoTexto] = useState('')
  const [eventoTipo, setEventoTipo] = useState('interrupcao')
  const [impressoes, setImpressoes] = useState('')
  const [resultado, setResultado] = useState('')
  const [tick, setTick] = useState(0)

  const loadList = useCallback(async () => {
    setErro('')
    const [meRes, listRes] = await Promise.all([
      fetch('/api/homologacao/me', { credentials: 'include' }),
      fetch('/api/homologacao/sessoes', { credentials: 'include' }),
    ])
    const meBody = await meRes.json().catch(() => ({}))
    const listBody = await listRes.json().catch(() => ({}))
    if (!meRes.ok) throw new Error(meBody.error || 'Falha ao carregar perfil')
    if (!listRes.ok) throw new Error(listBody.error || 'Falha ao listar sessões')
    setMe(meBody)
    setSessoes(listBody.itens || [])
  }, [])

  const loadDetail = useCallback(async (id) => {
    if (!id) {
      setDetail(null)
      setEventos([])
      return
    }
    const res = await fetch(`/api/homologacao/sessoes/${encodeURIComponent(id)}`, {
      credentials: 'include',
    })
    const body = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(body.error || 'Falha ao carregar sessão')
    setDetail(body.sessao)
    setEventos(body.eventos || [])
    setImpressoes(body.sessao?.impressoes || '')
    setResultado(body.sessao?.resultado_geral || '')
  }, [])

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      await loadList()
      await loadDetail(selectedId)
    } catch (e) {
      setErro(e.message || 'Erro')
    } finally {
      setLoading(false)
    }
  }, [loadList, loadDetail, selectedId])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    if (detail?.status !== 'em_andamento') return undefined
    const t = setInterval(() => setTick((n) => n + 1), 1000)
    return () => clearInterval(t)
  }, [detail?.status])

  const tempoVivo = useMemo(() => {
    if (!detail) return 0
    void tick
    return detail.tempo_ativo_segundos || 0
  }, [detail, tick])

  const selectSessao = (id) => {
    const next = new URLSearchParams(searchParams)
    if (id) next.set('sessao', id)
    else next.delete('sessao')
    setSearchParams(next)
  }

  const api = async (url, options = {}) => {
    setBusy(true)
    setErro('')
    try {
      const res = await fetch(url, {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
        ...options,
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Operação falhou')
      await loadList()
      const sid = body.sessao?.id || selectedId
      if (sid) {
        if (sid !== selectedId) selectSessao(sid)
        await loadDetail(sid)
      }
      return body
    } catch (e) {
      setErro(e.message || 'Erro')
      throw e
    } finally {
      setBusy(false)
    }
  }

  const criarSessao = async () => {
    await api('/api/homologacao/sessoes', {
      method: 'POST',
      body: JSON.stringify({
        profissionais: [
          {
            nome: user?.nome || me?.homologador?.nome || 'Homologador',
            papel: 'homologador',
            email: user?.email || me?.homologador?.email,
          },
        ],
      }),
    })
  }

  const action = async (path, payload = {}) => {
    if (!selectedId) return
    await api(`/api/homologacao/sessoes/${encodeURIComponent(selectedId)}/${path}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  const salvarMeta = async () => {
    if (!selectedId) return
    await api(`/api/homologacao/sessoes/${encodeURIComponent(selectedId)}`, {
      method: 'PATCH',
      body: JSON.stringify({
        impressoes,
        resultado_geral: resultado || null,
        profissionais: detail?.profissionais || [],
      }),
    })
  }

  const addProfissional = async () => {
    if (!selectedId || !profNome.trim()) return
    const profissionais = [
      ...(detail?.profissionais || []),
      { nome: profNome.trim(), papel: profPapel.trim() || 'participante' },
    ]
    await api(`/api/homologacao/sessoes/${encodeURIComponent(selectedId)}`, {
      method: 'PATCH',
      body: JSON.stringify({ profissionais }),
    })
    setProfNome('')
  }

  const addEvento = async () => {
    if (!selectedId || !eventoTexto.trim()) return
    await api(`/api/homologacao/sessoes/${encodeURIComponent(selectedId)}/eventos`, {
      method: 'POST',
      body: JSON.stringify({ tipo: eventoTipo, texto: eventoTexto.trim() }),
    })
    setEventoTexto('')
  }

  return (
    <div className="mx-auto max-w-6xl px-1 py-4 sm:px-2">
      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-school-700">
          Homologação · multi-pessoa
        </p>
        <h1 className="mt-1 text-2xl font-semibold text-ink">Sessões de homologação</h1>
        <p className="mt-1 max-w-3xl text-sm text-muted">
          Cada homologador grava o próprio percurso (checks do roteiro, tempo, interrupções e
          impressões). {me?.homologador ? (
            <>
              Você está como <strong>{me.homologador.funcao}</strong>
              {me.pode_ver_todas ? ' com visão de todas as sessões.' : ' — só as suas sessões.'}
            </>
          ) : (
            ' Conta administrativa: visão institucional.'
          )}
        </p>
      </div>

      {erro ? (
        <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {erro}
        </p>
      ) : null}

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={busy || !me?.homologador}
          onClick={() => criarSessao().catch(() => {})}
          className="rounded-lg bg-school-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          Nova sessão
        </button>
        <Link
          to="/roteiro-guiado"
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50"
        >
          Abrir roteiro guiado
        </Link>
        {!me?.homologador ? (
          <span className="text-xs text-muted">
            Para criar sessão, a conta precisa estar provisionada como homologador.
          </span>
        ) : null}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <section className="rounded-xl border border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-4 py-3">
            <h2 className="text-sm font-semibold text-ink">Lista</h2>
          </div>
          {loading ? (
            <p className="p-4 text-sm text-muted">Carregando…</p>
          ) : sessoes.length === 0 ? (
            <p className="p-4 text-sm text-muted">Nenhuma sessão ainda.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {sessoes.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    onClick={() => selectSessao(s.id)}
                    className={[
                      'flex w-full flex-col gap-1 px-4 py-3 text-left transition',
                      selectedId === s.id ? 'bg-school-50' : 'hover:bg-slate-50',
                    ].join(' ')}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs font-semibold text-school-800">
                        {s.codigo}
                      </span>
                      <StatusPill status={s.status} />
                    </div>
                    <span className="text-sm text-ink">{s.titulo || s.homologador_nome}</span>
                    <span className="text-xs text-muted">
                      {s.homologador_email} · {formatDuration(s.tempo_ativo_segundos)} · roteiro{' '}
                      {s.roteiro?.percentual ?? 0}%
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white">
          {!selectedId || !detail ? (
            <p className="p-6 text-sm text-muted">Selecione uma sessão para administrar.</p>
          ) : (
            <div className="space-y-5 p-4 sm:p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-mono text-xs font-semibold text-school-800">{detail.codigo}</p>
                  <h2 className="text-lg font-semibold text-ink">{detail.titulo}</h2>
                  <p className="text-sm text-muted">
                    {detail.homologador_nome} · {detail.homologador_email}
                  </p>
                </div>
                <StatusPill status={detail.status} />
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">
                    Tempo ativo
                  </p>
                  <p className="text-lg font-semibold tabular-nums">{formatDuration(tempoVivo)}</p>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">
                    Roteiro
                  </p>
                  <p className="text-lg font-semibold tabular-nums">
                    {detail.roteiro?.percentual ?? 0}%
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">
                    Início
                  </p>
                  <p className="text-xs font-medium">{formatDate(detail.iniciada_em)}</p>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">
                    Fim
                  </p>
                  <p className="text-xs font-medium">{formatDate(detail.encerrada_em)}</p>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                {detail.status === 'preparada' || detail.status === 'pausada' ? (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() =>
                      action(detail.status === 'pausada' ? 'retomar' : 'iniciar').catch(() => {})
                    }
                    className="rounded-lg bg-school-700 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
                  >
                    {detail.status === 'pausada' ? 'Retomar' : 'Iniciar'}
                  </button>
                ) : null}
                {detail.status === 'em_andamento' ? (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => action('pausar').catch(() => {})}
                    className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-1.5 text-sm font-semibold text-amber-900 disabled:opacity-50"
                  >
                    Pausar / interrupção de tempo
                  </button>
                ) : null}
                {detail.status !== 'concluida' && detail.status !== 'cancelada' ? (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() =>
                      action('encerrar', {
                        resultado_geral: resultado || 'nao_concluido',
                        texto: impressoes,
                      }).catch(() => {})
                    }
                    className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-ink disabled:opacity-50"
                  >
                    Encerrar
                  </button>
                ) : null}
                <Link
                  to={`/roteiro-guiado?tipo=homologacao&sessao=${encodeURIComponent(detail.id)}`}
                  className="rounded-lg border border-school-200 bg-school-50 px-3 py-1.5 text-sm font-semibold text-school-800"
                >
                  Preencher roteiro desta sessão
                </Link>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-ink">Profissionais envolvidos</h3>
                <ul className="mt-2 space-y-1">
                  {(detail.profissionais || []).map((p, idx) => (
                    <li key={`${p.nome}-${idx}`} className="text-sm text-muted">
                      <span className="font-medium text-ink">{p.nome}</span>
                      {p.papel ? ` · ${p.papel}` : ''}
                      {p.email ? ` · ${p.email}` : ''}
                    </li>
                  ))}
                </ul>
                {detail.status !== 'concluida' ? (
                  <div className="mt-2 flex flex-wrap gap-2">
                    <input
                      value={profNome}
                      onChange={(e) => setProfNome(e.target.value)}
                      placeholder="Nome"
                      className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
                    />
                    <input
                      value={profPapel}
                      onChange={(e) => setProfPapel(e.target.value)}
                      placeholder="Papel"
                      className="w-36 rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
                    />
                    <button
                      type="button"
                      disabled={busy || !profNome.trim()}
                      onClick={() => addProfissional().catch(() => {})}
                      className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold disabled:opacity-50"
                    >
                      Incluir
                    </button>
                  </div>
                ) : null}
              </div>

              <div>
                <h3 className="text-sm font-semibold text-ink">Interrupções / notas</h3>
                <div className="mt-2 flex flex-wrap gap-2">
                  <select
                    value={eventoTipo}
                    onChange={(e) => setEventoTipo(e.target.value)}
                    className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
                  >
                    <option value="interrupcao">Interrupção</option>
                    <option value="impressao">Impressão</option>
                    <option value="nota">Nota</option>
                  </select>
                  <input
                    value={eventoTexto}
                    onChange={(e) => setEventoTexto(e.target.value)}
                    placeholder="Descreva o evento"
                    className="min-w-[12rem] flex-1 rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
                  />
                  <button
                    type="button"
                    disabled={busy || !eventoTexto.trim()}
                    onClick={() => addEvento().catch(() => {})}
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold disabled:opacity-50"
                  >
                    Registrar
                  </button>
                </div>
                <ul className="mt-3 max-h-48 space-y-2 overflow-y-auto">
                  {eventos.length === 0 ? (
                    <li className="text-sm text-muted">Nenhum evento ainda.</li>
                  ) : (
                    eventos.map((ev) => (
                      <li key={ev.id} className="border-l-2 border-slate-200 pl-3 text-sm">
                        <span className="text-xs font-semibold uppercase text-muted">
                          {ev.tipo}
                        </span>
                        <span className="ml-2 text-xs text-muted">{formatDate(ev.criado_em)}</span>
                        <p className="text-ink">{ev.texto || '—'}</p>
                      </li>
                    ))
                  )}
                </ul>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-ink">Impressões / resultado</h3>
                <textarea
                  value={impressoes}
                  onChange={(e) => setImpressoes(e.target.value)}
                  rows={4}
                  className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  placeholder="O que ficou claro, o que travou, severidade…"
                />
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <select
                    value={resultado}
                    onChange={(e) => setResultado(e.target.value)}
                    className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
                  >
                    <option value="">Resultado…</option>
                    {Object.entries(RESULTADO_LABEL).map(([k, v]) => (
                      <option key={k} value={k}>
                        {v}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => salvarMeta().catch(() => {})}
                    className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
                  >
                    Salvar impressões
                  </button>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
