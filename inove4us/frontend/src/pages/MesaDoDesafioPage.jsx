import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import BrandLogo from '../components/BrandLogo'
import RegistrarAulasModal from '../components/RegistrarAulasModal'
import { useAuth } from '../lib/auth'
import { api } from '../lib/api'

const COLUNAS = [
  { id: 'para_fazer', label: 'Para Fazer', tone: 'border-brand-200 bg-brand-50/60' },
  { id: 'fazendo', label: 'Fazendo', tone: 'border-amber-200 bg-amber-50/50' },
  { id: 'pronto', label: 'Pronto', tone: 'border-emerald-200 bg-emerald-50/50' },
]

const STATUS_LABEL = {
  planejado: 'Planejada',
  em_execucao: 'Em execução',
  concluido: 'Concluída',
}

const TURNO_LABEL = {
  manha: 'Manhã',
  tarde: 'Tarde',
  noite: 'Noite',
}

function formatDate(iso) {
  if (!iso) return '—'
  const d = String(iso).slice(0, 10)
  const [y, m, day] = d.split('-')
  if (!y || !m || !day) return d
  return `${day}/${m}/${y}`
}

function formatMin(n) {
  const m = Math.max(0, Math.round(Number(n) || 0))
  if (m < 60) return `${m} min`
  const h = Math.floor(m / 60)
  const rest = m % 60
  return rest ? `${h} h ${rest} min` : `${h} h`
}

function cardColor(card) {
  return card?.cor || '#FDE68A'
}

function aulaIdsDoCard(card) {
  const fromEstados = (card?.estados || [])
    .map((st) => Number(st?.id_evento))
    .filter((n) => Number.isFinite(n) && n > 0)
  return [...new Set(fromEstados)]
}

/**
 * Mesa do desafio — painel gerencial no espírito do método inove4us:
 * missão completa, Kanban com todos os cards, aulas com realce ao selecionar card.
 */
export default function MesaDoDesafioPage() {
  const { desafioId } = useParams()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedCardId, setSelectedCardId] = useState(null)
  const [showRegistro, setShowRegistro] = useState(false)
  const [registroOk, setRegistroOk] = useState('')

  const load = useCallback(async () => {
    if (!desafioId) return
    setLoading(true)
    setError('')
    try {
      const res = await api.getDesafioMesa(desafioId)
      setData(res)
    } catch (err) {
      setError(err?.message || 'Não foi possível abrir a mesa do desafio.')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [desafioId])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    setSelectedCardId(null)
  }, [desafioId])

  const desafio = data?.desafio
  const plan = useMemo(() => {
    const pd = desafio?.plan_data
    if (!pd || typeof pd !== 'object') return {}
    return pd.plano || pd.plano_eduscrum || pd
  }, [desafio])

  const hipotese = desafio?.hipotese || plan?.hipotese || desafio?.meta_json?.hipotese || ''
  const problema = desafio?.problema || plan?.problema || ''
  const papeis = plan?.papeis || {}

  const missao = useMemo(() => {
    const raw = (
      plan?.missao ||
      desafio?.meta_json?.missao ||
      ''
    ).trim()
    const problemaFull = (problema || '').trim()
    const nomeMatch = raw.match(/conduzir\s*«([^»]+)»/i)
    const nome =
      nomeMatch?.[1]?.trim() ||
      plan?.nome ||
      plan?.etiqueta ||
      'a metodologia escolhida'

    // Missão antiga vinha com trecho[:120] — reconstrói com o problema completo.
    const truncada =
      !raw ||
      /…\s*$/.test(raw) ||
      (problemaFull.length > 80 &&
        raw.includes('para enfrentar') &&
        !raw.toLowerCase().includes(problemaFull.slice(0, 48).toLowerCase()))

    if (problemaFull && truncada) {
      return `Missão: conduzir «${nome}» para enfrentar «${problemaFull}».`
    }
    if (raw) return raw
    if (problemaFull) return problemaFull
    return desafio?.titulo || 'Missão a definir'
  }, [plan, desafio, problema])

  const progresso = data?.progresso || {}
  const tempo = data?.tempo || {}
  const cards = Array.isArray(data?.cards) ? data.cards : []
  const execucoes = Array.isArray(data?.execucoes) ? data.execucoes : []
  const aulas = useMemo(() => {
    const all = [
      ...(Array.isArray(data?.aulas_por_executar) ? data.aulas_por_executar : []),
      ...(Array.isArray(data?.aulas_executadas) ? data.aulas_executadas : []),
    ]
    return all.sort((a, b) => String(a.data_evento || '').localeCompare(String(b.data_evento || '')))
  }, [data])

  const selectedCard = useMemo(
    () => cards.find((c) => String(c.id) === String(selectedCardId)) || null,
    [cards, selectedCardId],
  )

  const highlightedAulaIds = useMemo(() => {
    if (!selectedCard) return new Set()
    return new Set(aulaIdsDoCard(selectedCard).map(String))
  }, [selectedCard])

  const execucaoStats = useMemo(() => {
    let prontoMin = 0
    let fazendoMin = 0
    let total = 0
    let prontoCount = 0
    let fazendoCount = 0
    for (const c of cards) {
      const m = Math.max(1, Number(c.duracao_minutos) || 10)
      total += m
      if (c.coluna === 'pronto') {
        prontoMin += m
        prontoCount += 1
      } else if (c.coluna === 'fazendo') {
        fazendoMin += m * 0.5
        fazendoCount += 1
      }
    }
    const feitos = prontoMin + fazendoMin
    const pct = total ? Math.round((100 * feitos) / total) : progresso.progresso_pct || 0
    return {
      total,
      feitos,
      restantes: Math.max(0, total - feitos),
      pct,
      prontoCount,
      fazendoCount,
      pendentes: cards.length - prontoCount - fazendoCount,
    }
  }, [cards, progresso.progresso_pct])

  function toggleCard(cardId) {
    setSelectedCardId((prev) => (String(prev) === String(cardId) ? null : cardId))
  }

  function openKanban() {
    if (data?.id_evento_ancora) {
      navigate(`/execucao/${data.id_evento_ancora}`)
      return
    }
    setShowRegistro(true)
  }

  const suggestTurma = useMemo(() => {
    const mine = aulas.find((a) => a.eh_minha && a.turma)
    return mine?.turma || aulas.find((a) => a.turma)?.turma || ''
  }, [aulas])

  return (
    <div className="min-h-screen bg-[#FBF7F2]">
      <header className="sticky top-0 z-40 border-b border-brand-200/80 bg-white/95 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Link to="/mesa-do-inovador" className="flex items-center gap-3" aria-label="Voltar ao início">
            <BrandLogo
              variant="internal"
              className="h-20 w-auto max-w-[260px] object-contain sm:h-24"
            />
          </Link>
          <div className="flex flex-wrap items-center gap-2">
            <p className="hidden text-sm text-bordo-soft lg:block">
              Olá, <span className="font-semibold text-bordo">{user?.nome_clie || 'professor'}</span>
            </p>
            <Link to="/mesa-do-inovador" className="btn-ghost !px-3 !py-1.5 text-xs font-semibold">
              ← Início / desafios
            </Link>
            <button
              type="button"
              onClick={() => {
                setRegistroOk('')
                setShowRegistro(true)
              }}
              className="btn-primary !px-4 !py-2 text-sm"
            >
              Acrescentar / ratificar aulas
            </button>
            {data?.id_evento_ancora ? (
              <button type="button" onClick={openKanban} className="btn-ghost !px-3 !py-2 text-sm font-semibold">
                Minha mesa
              </button>
            ) : null}
            <button type="button" onClick={logout} className="btn-ghost !px-3 !py-1.5 text-xs">
              Sair
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 pb-20 pt-6 sm:px-6">
        {loading ? <p className="text-sm text-bordo-soft">Carregando mesa do desafio…</p> : null}
        {error ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
            {error}{' '}
            <button type="button" className="font-semibold underline" onClick={() => void load()}>
              Tentar de novo
            </button>
          </div>
        ) : null}

        {registroOk ? (
          <p className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-900">
            {registroOk}
          </p>
        ) : null}

        {!loading && !error && desafio ? (
          <>
            <div className="mb-6 text-center sm:text-left">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-brand-600">
                Mesa do desafio · painel gerencial
              </p>
              <h1 className="mt-2 font-display text-3xl font-bold text-bordo-deep sm:text-4xl">
                Aula · método inove4us
              </h1>
              <div className="mt-2 flex flex-wrap items-center justify-center gap-2 sm:justify-start">
                <span
                  className={[
                    'rounded-full px-3 py-1 text-[11px] font-bold uppercase tracking-wide',
                    desafio.sou_dono
                      ? 'bg-emerald-100 text-emerald-900'
                      : 'bg-amber-100 text-amber-950',
                  ].join(' ')}
                >
                  {desafio.sou_dono ? 'Meu desafio' : 'Desafio atribuído a mim'}
                </span>
                {desafio.tema ? (
                  <span className="rounded-full bg-brand-100 px-3 py-1 text-[11px] font-bold text-bordo">
                    Tema: {desafio.tema}
                  </span>
                ) : null}
              </div>
            </div>

            {/* Missão — texto completo, sem corte */}
            <section className="mb-6 rounded-2xl border border-brand-200 bg-white p-5 shadow-soft sm:p-7">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-600">
                Missão da aula
              </p>
              <h2 className="mt-3 whitespace-pre-wrap font-display text-base font-semibold leading-relaxed text-bordo-deep sm:text-lg">
                {missao}
              </h2>

              {hipotese ? (
                <div className="mt-5 rounded-xl bg-brand-50 px-4 py-3">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-bordo">Hipótese</p>
                  <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-bordo-deep">
                    {hipotese}
                  </p>
                </div>
              ) : null}

              {problema ? (
                <div className="mt-4">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-bordo">Problema</p>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-bordo">
                    {problema}
                  </p>
                </div>
              ) : null}

              <div className="mt-6">
                <p className="mb-3 text-xs font-bold uppercase tracking-[0.18em] text-bordo">
                  Regra dos times
                </p>
                <div className="grid gap-3 sm:grid-cols-3">
                  {[
                    { key: 'lider', icon: 'fa-flag', label: 'Líder' },
                    { key: 'guardiao', icon: 'fa-hourglass-half', label: 'Guardião' },
                    { key: 'apresentador', icon: 'fa-bullhorn', label: 'Apresentador' },
                  ].map((role) => (
                    <div
                      key={role.key}
                      className="rounded-xl border border-brand-100 bg-brand-50/70 p-4"
                    >
                      <p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-bordo">
                        <i className={`fa-solid ${role.icon} text-brand-600`} />
                        {role.label}
                      </p>
                      <p className="whitespace-pre-wrap text-sm leading-relaxed text-bordo-soft">
                        {papeis[role.key] || '—'}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
              {/* Kanban gerencial */}
              <section className="rounded-2xl border border-brand-200 bg-white/95 p-4 shadow-soft sm:p-6">
                <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-bordo">
                      Mesa
                    </p>
                    <p className="mt-1 text-sm text-bordo-soft">
                      Clique em um card para realçar as aulas associadas no painel ao lado.
                      Para mudar o plano em execução, use{' '}
                      <strong className="text-bordo">Acrescentar / ratificar aulas</strong>.
                    </p>
                  </div>
                  {selectedCard ? (
                    <button
                      type="button"
                      className="btn-ghost !px-3 !py-1.5 text-xs"
                      onClick={() => setSelectedCardId(null)}
                    >
                      Limpar seleção
                    </button>
                  ) : null}
                </div>

                {!cards.length ? (
                  <div className="rounded-xl border border-dashed border-brand-200 bg-brand-50/50 px-4 py-8 text-center">
                    <p className="text-sm font-semibold text-bordo">Ainda sem cards neste desafio.</p>
                    <p className="mt-2 text-sm text-bordo-soft">
                      Abra a mesa da sua execução para montar o quadro ou registre as aulas.
                    </p>
                    <button
                      type="button"
                      className="btn-primary mt-4 !px-4 !py-2 text-sm"
                      onClick={() => {
                        setRegistroOk('')
                        setShowRegistro(true)
                      }}
                    >
                      Ir para acrescentar aulas
                    </button>
                  </div>
                ) : (
                  <div className="grid gap-4 md:grid-cols-3">
                    {COLUNAS.map((col) => {
                      const colCards = cards.filter((c) => (c.coluna || 'para_fazer') === col.id)
                      return (
                        <div
                          key={col.id}
                          className={`min-h-[280px] rounded-xl border p-3 sm:p-4 ${col.tone}`}
                        >
                          <div className="mb-3 flex items-center justify-between">
                            <h3 className="text-sm font-bold text-bordo-deep">{col.label}</h3>
                            <span className="rounded-full bg-white/80 px-2 py-0.5 text-[11px] font-bold text-bordo-soft">
                              {colCards.length}
                            </span>
                          </div>
                          <ul className="space-y-3">
                            {colCards.map((card) => {
                              const selected = String(selectedCardId) === String(card.id)
                              const aids = aulaIdsDoCard(card)
                              const dimOthers =
                                selectedCardId && !selected
                                  ? 'opacity-45'
                                  : ''
                              return (
                                <li key={card.id}>
                                  <button
                                    type="button"
                                    onClick={() => toggleCard(card.id)}
                                    aria-pressed={selected}
                                    className={[
                                      'w-full rounded-xl border p-4 text-left text-sm text-bordo-deep shadow-sm transition',
                                      selected
                                        ? 'ring-2 ring-bordo ring-offset-2'
                                        : 'border-black/5 hover:ring-2 hover:ring-brand-400/60',
                                      dimOthers,
                                    ].join(' ')}
                                    style={{
                                      backgroundColor: cardColor(card),
                                      transform: `rotate(${(String(card.id).charCodeAt(1) % 3) - 1}deg)`,
                                    }}
                                  >
                                    <div className="flex items-start justify-between gap-2">
                                      <p className="font-semibold leading-snug">{card.titulo}</p>
                                      <span className="shrink-0 rounded-md bg-white/75 px-1.5 py-0.5 text-[11px] font-bold tabular-nums">
                                        {card.duracao_minutos || 10}′
                                      </span>
                                    </div>

                                    {card.objetivo ? (
                                      <p className="mt-2 whitespace-pre-wrap text-[12px] font-normal leading-relaxed text-bordo/90">
                                        <span className="font-bold">Objetivo: </span>
                                        {card.objetivo}
                                      </p>
                                    ) : null}

                                    {card.como_executar ? (
                                      <p className="mt-2 whitespace-pre-wrap text-[12px] font-normal leading-relaxed text-bordo/85">
                                        <span className="font-bold">Como fazer: </span>
                                        {card.como_executar}
                                      </p>
                                    ) : null}

                                    {aids.length ? (
                                      <p className="mt-2 inline-block rounded bg-white/80 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-bordo/80">
                                        {aids.length} aula{aids.length === 1 ? '' : 's'} vinculada
                                        {aids.length === 1 ? '' : 's'}
                                      </p>
                                    ) : (
                                      <p className="mt-2 text-[11px] font-semibold text-amber-900/90">
                                        Sem aula vinculada ainda — registre e associe este card.
                                      </p>
                                    )}

                                    {Array.isArray(card.estados) && card.estados.length > 0 ? (
                                      <ul className="mt-2 space-y-1.5">
                                        {card.estados.map((st, i) => {
                                          const escopos = Array.isArray(st.escopos_turma)
                                            ? st.escopos_turma.filter((e) =>
                                                String(e?.nota || '').trim(),
                                              )
                                            : []
                                          return (
                                            <li
                                              key={`${card.id}-st-${st.id_evento}-${i}`}
                                              className="rounded-lg bg-white/70 px-2 py-1.5 text-[11px] leading-snug text-bordo/95"
                                            >
                                              <span className="font-bold">
                                                {st.turma || 'Turma'}
                                                {st.turno ? ` · ${TURNO_LABEL[st.turno] || st.turno}` : ''}
                                                {': '}
                                              </span>
                                              {STATUS_LABEL[st.status_aula] || st.status_aula}
                                              {escopos.map((esc, j) => (
                                                <span key={j} className="mt-1 block font-normal">
                                                  Escopo: {esc.nota}
                                                </span>
                                              ))}
                                            </li>
                                          )
                                        })}
                                      </ul>
                                    ) : null}
                                  </button>
                                </li>
                              )
                            })}
                          </ul>
                        </div>
                      )
                    })}
                  </div>
                )}

                {/* Aulas em lista ampla sob o kanban — realce pela seleção */}
                <div className="mt-8 border-t border-brand-100 pt-6">
                  <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-[0.18em] text-bordo">
                        Aulas do desafio
                      </p>
                      <p className="mt-1 text-sm text-bordo-soft">
                        {selectedCard
                          ? `Realce: aulas ligadas ao card «${selectedCard.titulo}».`
                          : 'Selecione um card acima para destacar as aulas associadas.'}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="btn-primary !px-4 !py-2 text-sm"
                      onClick={() => {
                        setRegistroOk('')
                        setShowRegistro(true)
                      }}
                    >
                      Acrescentar / ratificar aulas
                    </button>
                  </div>

                  {!aulas.length ? (
                    <p className="rounded-xl bg-brand-50 px-4 py-4 text-sm text-bordo">
                      Nenhuma aula registrada ainda. Use «Acrescentar / ratificar aulas» para criar
                      datas, turmas e vincular cards — o plano pode mudar a qualquer momento.
                    </p>
                  ) : (
                    <ul className="grid gap-3 sm:grid-cols-2">
                      {aulas.map((a) => {
                        const linked = highlightedAulaIds.has(String(a.id_evento))
                        const faded = selectedCard && !linked
                        return (
                          <li key={a.id_evento}>
                            <div
                              className={[
                                'rounded-xl border px-4 py-4 transition',
                                linked
                                  ? 'border-bordo bg-bordo/5 ring-2 ring-bordo ring-offset-2'
                                  : a.status === 'concluido'
                                    ? 'border-emerald-200 bg-emerald-50/60'
                                    : 'border-brand-200 bg-white',
                                faded ? 'opacity-35' : '',
                              ].join(' ')}
                            >
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="text-base font-bold text-bordo-deep">
                                  {formatDate(a.data_evento)}
                                </span>
                                {a.turma ? (
                                  <span className="text-sm font-semibold text-bordo">{a.turma}</span>
                                ) : null}
                                {a.turno ? (
                                  <span className="text-sm text-bordo-soft">
                                    {TURNO_LABEL[a.turno] || a.turno}
                                  </span>
                                ) : null}
                                <span
                                  className={[
                                    'rounded-full px-2 py-0.5 text-[10px] font-bold uppercase',
                                    a.origem === 'interna'
                                      ? 'bg-emerald-100 text-emerald-900'
                                      : 'bg-amber-100 text-amber-950',
                                  ].join(' ')}
                                >
                                  {a.origem === 'interna' ? 'Interna' : 'Externa'}
                                </span>
                                <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-bold uppercase text-bordo-soft">
                                  {STATUS_LABEL[a.status] || a.status}
                                </span>
                                {linked ? (
                                  <span className="rounded-full bg-bordo px-2 py-0.5 text-[10px] font-bold uppercase text-white">
                                    Vinculada ao card
                                  </span>
                                ) : null}
                              </div>
                              <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-bordo">
                                {a.titulo || 'Aula · método inove4us'}
                              </p>
                              {a.eh_minha ? (
                                <button
                                  type="button"
                                  className="mt-3 text-sm font-bold text-brand-700 underline-offset-2 hover:underline"
                                  onClick={() => navigate(`/execucao/${a.id_evento}`)}
                                >
                                  Abrir minha mesa desta aula →
                                </button>
                              ) : (
                                <p className="mt-2 text-xs font-semibold text-bordo-soft">
                                  Quadro de outro responsável — só visão gerencial aqui.
                                </p>
                              )}
                            </div>
                          </li>
                        )
                      })}
                    </ul>
                  )}
                </div>

                {/* Execuções internas / externas */}
                {execucoes.length > 0 ? (
                  <div className="mt-8 border-t border-brand-100 pt-6">
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-bordo">
                      Execuções (interna e externa)
                    </p>
                    <ul className="mt-4 grid gap-3 sm:grid-cols-2">
                      {execucoes.map((ex) => (
                        <li
                          key={ex.execucao_key}
                          className="rounded-xl border border-brand-100 bg-brand-50/40 p-4"
                        >
                          <div className="flex flex-wrap gap-2">
                            <span
                              className={[
                                'rounded-full px-2 py-0.5 text-[10px] font-bold uppercase',
                                ex.origem === 'interna'
                                  ? 'bg-emerald-100 text-emerald-900'
                                  : 'bg-amber-100 text-amber-950',
                              ].join(' ')}
                            >
                              {ex.origem}
                            </span>
                            {ex.eh_minha ? (
                              <span className="text-[10px] font-bold uppercase text-brand-700">
                                minha
                              </span>
                            ) : null}
                          </div>
                          <p className="mt-2 text-base font-bold text-bordo-deep">
                            {ex.turma || 'Sem turma'}
                            {ex.turno ? ` · ${TURNO_LABEL[ex.turno] || ex.turno}` : ''}
                          </p>
                          <p className="mt-1 text-sm text-bordo-soft">
                            {ex.responsavel?.nome_clie ||
                              ex.responsavel?.mail_clie ||
                              'Responsável'}
                          </p>
                          <p className="mt-2 text-sm text-bordo">
                            Progresso {ex.progresso_pct ?? 0}% · {ex.n_concluido}/{ex.n_aulas}{' '}
                            aulas · {ex.cards_pronto}/{ex.cards_total} cards
                          </p>
                          {ex.pode_abrir_kanban && ex.id_evento_ancora ? (
                            <button
                              type="button"
                              className="mt-3 text-sm font-bold text-brand-700 underline-offset-2 hover:underline"
                              onClick={() => navigate(`/execucao/${ex.id_evento_ancora}`)}
                            >
                              Abrir mesa →
                            </button>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </section>

              {/* Lateral — estatísticas (espaço generoso; detalhe refinado depois) */}
              <aside className="space-y-4 xl:sticky xl:top-28 xl:self-start">
                <div className="rounded-2xl border border-brand-200 bg-white p-5 shadow-soft">
                  <p className="mb-4 text-xs font-bold uppercase tracking-[0.18em] text-bordo">
                    Execução do plano
                  </p>
                  <div className="rounded-xl bg-gradient-to-b from-brand-600 to-bordo p-5 text-white">
                    <div className="flex items-center justify-between gap-2 text-[11px] font-semibold uppercase tracking-widest opacity-90">
                      <span>Progresso dos cards</span>
                      <span>{execucaoStats.pct}%</span>
                    </div>
                    <p className="mt-3 font-display text-4xl font-bold tabular-nums tracking-tight">
                      {formatMin(execucaoStats.feitos)}
                      <span className="ml-1 text-lg font-semibold opacity-80">
                        / {formatMin(execucaoStats.total)}
                      </span>
                    </p>
                    <p className="mt-2 text-sm leading-relaxed opacity-90">
                      Pronto = 100% do card · Fazendo = 50%. Restam ~
                      {formatMin(execucaoStats.restantes)}.
                    </p>
                    <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/25">
                      <div
                        className="h-full rounded-full bg-white transition-all duration-500"
                        style={{ width: `${execucaoStats.pct}%` }}
                      />
                    </div>
                    <p className="mt-3 text-sm opacity-90">
                      {execucaoStats.prontoCount} prontos · {execucaoStats.fazendoCount} em
                      andamento · {execucaoStats.pendentes} a fazer
                    </p>
                  </div>

                  <dl className="mt-5 space-y-4 text-sm">
                    <div>
                      <dt className="text-[11px] font-bold uppercase tracking-wide text-bordo-soft">
                        Aulas no desafio
                      </dt>
                      <dd className="mt-1 text-lg font-bold text-bordo-deep">
                        {progresso.n_concluido || 0} concluídas / {progresso.n_aulas || 0} total
                      </dd>
                      <dd className="text-bordo-soft">
                        {progresso.n_em_execucao || 0} em execução · {progresso.n_planejado || 0}{' '}
                        planejada(s)
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[11px] font-bold uppercase tracking-wide text-bordo-soft">
                        Calendário do desafio
                      </dt>
                      <dd className="mt-1 font-semibold text-bordo-deep">
                        {tempo.data_inicio ? formatDate(tempo.data_inicio) : '—'} →{' '}
                        {tempo.data_fim ? formatDate(tempo.data_fim) : '—'}
                      </dd>
                      <dd
                        className={[
                          'mt-1 font-bold',
                          tempo.atrasado ? 'text-rose-700' : 'text-bordo',
                        ].join(' ')}
                      >
                        {tempo.dias_restantes == null
                          ? 'Sem datas suficientes para prazo'
                          : tempo.atrasado
                            ? `${Math.abs(tempo.dias_restantes)} dia(s) em atraso`
                            : tempo.dias_restantes === 0
                              ? 'Encerra hoje'
                              : `${tempo.dias_restantes} dia(s) restantes`}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[11px] font-bold uppercase tracking-wide text-bordo-soft">
                        Tempo restante nos cards
                      </dt>
                      <dd className="mt-1 text-lg font-bold text-bordo-deep">
                        {formatMin(tempo.minutos_restantes)}
                      </dd>
                      <dd className="text-bordo-soft">
                        de {formatMin(tempo.minutos_estimados || tempo.minutos_cards)} estimados
                      </dd>
                    </div>
                  </dl>

                  <button
                    type="button"
                    className="btn-primary mt-5 w-full !py-3 text-sm"
                    onClick={() => {
                        setRegistroOk('')
                        setShowRegistro(true)
                      }}
                  >
                    Acrescentar / ratificar aulas
                  </button>
                  {data?.id_evento_ancora ? (
                    <button
                      type="button"
                      className="btn-ghost mt-2 w-full !py-2.5 text-sm"
                      onClick={openKanban}
                    >
                      Abrir minha mesa
                    </button>
                  ) : null}
                  <p className="mt-3 text-xs leading-relaxed text-bordo-soft">
                    Em execução você pode mudar o plano a qualquer momento: novas aulas entram
                    neste mesmo desafio. As estatísticas da lateral serão refinadas em seguida.
                  </p>
                </div>

                {selectedCard ? (
                  <div className="rounded-2xl border border-bordo/20 bg-white p-5 shadow-soft">
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-bordo">
                      Card selecionado
                    </p>
                    <p className="mt-2 text-lg font-bold text-bordo-deep">{selectedCard.titulo}</p>
                    {selectedCard.objetivo ? (
                      <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-bordo">
                        {selectedCard.objetivo}
                      </p>
                    ) : null}
                    <p className="mt-3 text-sm text-bordo-soft">
                      {highlightedAulaIds.size
                        ? `${highlightedAulaIds.size} aula(s) em realce na lista.`
                        : 'Nenhuma aula vinculada a este card ainda.'}
                    </p>
                  </div>
                ) : null}
              </aside>
            </div>
          </>
        ) : null}
      </main>

      <RegistrarAulasModal
        open={showRegistro}
        onClose={() => setShowRegistro(false)}
        desafio={desafio}
        cardsMesa={cards}
        missao={missao}
        planoSession={data?.plano_session || null}
        suggestTurma={suggestTurma}
        onDone={async (res) => {
          const n = (res?.eventos || []).length
          setRegistroOk(
            n
              ? `${n} aula(s) acrescentada(s) ao desafio. O painel foi atualizado.`
              : 'Aulas salvas. O painel foi atualizado.',
          )
          await load()
        }}
      />
    </div>
  )
}
