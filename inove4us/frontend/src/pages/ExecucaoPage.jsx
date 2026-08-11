import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import ProgressStepper from '../components/wizard/ProgressStepper'
import StepEduScrum from '../components/wizard/StepEduScrum'
import ReplicarDesafioModal from '../components/ReplicarDesafioModal'

function hasPlanData(planData) {
  if (!planData || typeof planData !== 'object') return false
  return Object.keys(planData).length > 0
}

function labelExecucao(ex) {
  const turma = ex.turma || (ex.turmas || []).join(', ') || 'Turma'
  const pct = ex.progresso_pct != null ? `${ex.progresso_pct}%` : ''
  const quem =
    ex.responsavel?.nome_clie ||
    ex.responsavel?.mail_clie ||
    (ex.eh_dono_desafio ? 'dono' : 'colaborador')
  const base = pct ? `${turma} · ${pct}` : turma
  return `${base} · ${quem}`
}

/**
 * Retomada da execução EduScrum a partir de um evento da agenda (plan_data / kanban_state).
 * Fase 2: seletor de execução (turma) acima das abas por aula da Fase 1.
 */
export default function ExecucaoPage() {
  const { idEvento } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [infoAula, setInfoAula] = useState('')
  const [evento, setEvento] = useState(null)
  const [desafio, setDesafio] = useState(null)
  const [execucoes, setExecucoes] = useState([])
  const [showReplicar, setShowReplicar] = useState(false)
  const [showConvidar, setShowConvidar] = useState(false)
  const [conviteEmail, setConviteEmail] = useState('')
  const [conviteCardId, setConviteCardId] = useState('')
  const [conviteBusy, setConviteBusy] = useState(false)
  const [conviteMsg, setConviteMsg] = useState('')
  const [conviteErro, setConviteErro] = useState('')
  const [conviteUrl, setConviteUrl] = useState('')
  const [conviteDevMail, setConviteDevMail] = useState(false)
  const [colaboradores, setColaboradores] = useState([])

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const fromState = location.state?.evento
        const statePlan = location.state?.plan_data
        if (
          fromState?.id_evento &&
          String(fromState.id_evento) === String(idEvento) &&
          hasPlanData(statePlan || fromState.plan_data)
        ) {
          if (!cancelled) {
            setEvento({
              ...fromState,
              plan_data: statePlan || fromState.plan_data,
              kanban_state: location.state?.kanban_state ?? fromState.kanban_state,
            })
          }
        }
        const data = await api.getAgendaEvento(idEvento)
        if (cancelled) return
        const ev = data.evento
        if (!ev) {
          setError('Evento não encontrado.')
          setEvento(null)
          return
        }
        if (ev.status === 'concluido') {
          // Pós-relato: Kanban continua editável para movimentar cards.
          setError('')
          setInfoAula(
            'Aula concluída neste quadro. Você já pode movimentar os cards da sua mesa (visão isolada de cada professor).',
          )
          setEvento(ev)
        } else if (!hasPlanData(ev.plan_data)) {
          setError('Este evento ainda não tem plano do método inove4us. Inicie um novo Desafio.')
          setInfoAula('')
          setEvento(null)
          return
        } else {
          setError('')
          setInfoAula(
            'Para mover um card nesta mesa, conclua a(s) aula(s) deste quadro com «Registrar e concluir aula» (relato). Em andamento você edita o plano; arrastar entre colunas só após a realização. Cada professor move só no próprio quadro.',
          )
          setEvento(ev)
        }

        try {
          const dRes = await api.getDesafioDoEvento(ev.id_evento)
          if (cancelled) return
          const d = dRes.desafio
          setDesafio(d || null)
          if (d?.id) {
            const exRes = await api.listDesafioExecucoes(d.id)
            if (!cancelled) setExecucoes(exRes.execucoes || [])
            if (d.sou_dono) {
              try {
                const col = await api.listDesafioColaboradores(d.id)
                if (!cancelled) setColaboradores(col.colaboradores || [])
              } catch {
                if (!cancelled) setColaboradores([])
              }
            }
          } else {
            setExecucoes([])
          }
        } catch {
          if (!cancelled) {
            setDesafio(null)
            setExecucoes([])
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Não foi possível carregar a aula.')
          setEvento(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [idEvento, location.state])

  const hydrated = useMemo(() => {
    if (!evento?.plan_data) return null
    const pd = evento.plan_data
    const plano = pd.plano || pd.plano_eduscrum || null
    if (!plano) return null
    const ks = evento.kanban_state
    const tarefas =
      (Array.isArray(ks?.tarefas) && ks.tarefas.length ? ks.tarefas : null) ||
      (Array.isArray(ks) && ks.length ? ks : null) ||
      plano.tarefas_kanban ||
      []
    return {
      plano: { ...plano, tarefas_kanban: tarefas },
      hipotese: pd.hipotese || pd.hipotese_teste || evento.meta_json?.hipotese || '',
      problema: pd.problema || evento.meta_json?.problema || '',
      causas: pd.causas || evento.meta_json?.causas || desafio?.causas || [],
      planoSession: pd.plano_session || evento.plano_session || null,
      initialKanbanState: ks || { tarefas },
      initialEventoId: evento.id_evento,
      desafioId: evento.desafio_id || desafio?.id || null,
      isReplica: Boolean(evento.meta_json?.execucao_replicada),
      somenteLeitura: Boolean(evento.somente_leitura) || evento.pode_editar === false,
      souDono: Boolean(desafio?.sou_dono),
    }
  }, [evento, desafio])

  const multiExecucao = execucoes.length > 1
  const execucaoAtual = useMemo(() => {
    if (!execucoes.length || !evento) return null
    const session = (evento.plano_session || '').trim()
    return (
      execucoes.find((ex) => {
        if (session && ex.plano_session === session) return true
        return (ex.aulas || []).some((a) => a.id_evento === evento.id_evento)
      }) || null
    )
  }, [execucoes, evento])

  const irmas = useMemo(() => {
    if (!execucaoAtual || execucoes.length < 2) return []
    return execucoes.filter((ex) => ex.execucao_key !== execucaoAtual.execucao_key)
  }, [execucoes, execucaoAtual])

  function handleTrocarExecucao(execucaoKey) {
    const ex = execucoes.find((e) => e.execucao_key === execucaoKey)
    if (!ex?.pode_abrir_kanban || !ex?.id_evento_ancora) return
    if (String(ex.id_evento_ancora) === String(idEvento)) return
    navigate(`/execucao/${ex.id_evento_ancora}`)
  }

  function handleReplicarDone(data) {
    const first = data?.eventos?.[0]
    if (first?.id_evento) {
      navigate(`/execucao/${first.id_evento}`)
    }
  }

  const cardsParaConvite = useMemo(() => {
    const fontes = hydrated?.plano?.tarefas_kanban || []
    const seen = new Set()
    const out = []
    for (const t of fontes) {
      const id = String(t?.id || '').trim()
      if (!id || seen.has(id)) continue
      seen.add(id)
      out.push({
        id,
        titulo: (t.titulo || 'Card').trim() || 'Card',
        objetivo: (t.objetivo || t.descricao || '').trim(),
      })
    }
    return out
  }, [hydrated?.plano?.tarefas_kanban])

  async function handleConvidar(e) {
    e?.preventDefault?.()
    if (!desafio?.id) return
    setConviteErro('')
    setConviteMsg('')
    if (!conviteCardId) {
      setConviteErro('Escolha o card que o professor convidado vai realizar.')
      return
    }
    setConviteBusy(true)
    try {
      const data = await api.convidarColaborador(desafio.id, {
        email: conviteEmail.trim(),
        card_id: conviteCardId,
      })
      const url = data.convite_url || ''
      const isDev = data.email?.channel === 'dev_log'
      setConviteUrl(url)
      setConviteDevMail(isDev)
      setConviteMsg(
        isDev
          ? `Convite criado para ${conviteEmail.trim()}. Em ambiente local o e-mail NÃO é enviado — copie o link abaixo e envie ao convidado.`
          : `Convite enviado para ${conviteEmail.trim()}.`,
      )
      setConviteEmail('')
      setConviteCardId('')
      const col = await api.listDesafioColaboradores(desafio.id)
      setColaboradores(col.colaboradores || [])
    } catch (err) {
      setConviteErro(err.message || 'Falha ao convidar.')
    } finally {
      setConviteBusy(false)
    }
  }

  return (
    <div className="min-h-screen">
      <ProgressStepper currentStep={4} />

      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6 print:hidden">
        <div className="flex min-w-0 items-center gap-3">
          <Link
            to={desafio?.id ? `/desafios/${desafio.id}` : '/mesa-do-inovador'}
            className="btn-ghost !px-3 !py-1.5 text-xs"
          >
            {desafio?.id ? '← Mesa do desafio' : '← Início'}
          </Link>
          <p className="truncate text-sm text-bordo-soft">
            Mesa da aula ·{' '}
            <span className="font-semibold text-bordo">{user?.nome_clie || 'professor'}</span>
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {desafio?.sou_dono ? (
            <button
              type="button"
              className="btn-ghost !px-3 !py-1.5 text-xs"
              onClick={() => {
                setShowConvidar(true)
                setConviteErro('')
                setConviteMsg('')
              }}
            >
              Convidar colaborador
            </button>
          ) : null}
          {desafio?.id ? (
            <button
              type="button"
              className="btn-ghost !px-3 !py-1.5 text-xs"
              onClick={() => setShowReplicar(true)}
            >
              Replicar para outra turma
            </button>
          ) : null}
          <button type="button" onClick={logout} className="btn-ghost !px-3 !py-1.5 text-xs">
            Sair
          </button>
        </div>
      </div>

      <main className="px-4 pb-16 pt-2 sm:px-6">
        {loading ? (
          <p className="py-16 text-center text-sm text-bordo-soft">Carregando aula…</p>
        ) : error && !hydrated ? (
          <div className="mx-auto max-w-lg rounded-2xl border border-brand-200 bg-white p-6 text-center shadow-soft">
            <p className="font-display text-xl font-bold text-bordo-deep">Não foi possível retomar</p>
            <p className="mt-2 text-sm text-bordo-soft">{error}</p>
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              <Link to="/mesa-do-inovador" className="btn-ghost !px-4 !py-2 text-sm">
                Voltar ao início
              </Link>
              <button
                type="button"
                className="btn-primary !px-4 !py-2 text-sm"
                onClick={() => navigate('/desafio')}
              >
                + Desafio
              </button>
            </div>
          </div>
        ) : hydrated ? (
          <>
            {infoAula ? (
              <div className="mx-auto mb-4 max-w-6xl rounded-xl border border-brand-200 bg-brand-50/90 px-4 py-3 text-xs text-bordo print:hidden">
                {infoAula}
              </div>
            ) : null}

            {multiExecucao ? (
              <div className="mx-auto mb-4 max-w-6xl rounded-2xl border border-brand-200 bg-white/95 p-4 shadow-soft print:hidden">
                <label className="block text-[10px] font-bold uppercase tracking-wide text-bordo">
                  Turma / execução
                </label>
                <select
                  className="field-input mt-1"
                  value={execucaoAtual?.execucao_key || ''}
                  onChange={(e) => handleTrocarExecucao(e.target.value)}
                >
                  {execucoes.map((ex) => (
                    <option
                      key={ex.execucao_key}
                      value={ex.execucao_key}
                      disabled={!ex.pode_abrir_kanban}
                    >
                      {labelExecucao(ex)}
                      {!ex.pode_abrir_kanban ? ' (só resumo)' : ''}
                      {ex.eh_colaborador ? ' · colaborador' : ''}
                      {' · '}
                      {ex.n_aulas} aula(s)
                    </option>
                  ))}
                </select>
                <ul className="mt-2 space-y-1 text-[11px] text-bordo-soft">
                  {execucoes
                    .filter((ex) => !ex.eh_minha)
                    .map((ex) => (
                      <li key={`sum-${ex.execucao_key}`}>
                        {ex.eh_colaborador ? 'Colaborador' : 'Dono'}:{' '}
                        <strong>{ex.responsavel?.nome_clie || ex.responsavel?.mail_clie || '—'}</strong>
                        {' · '}
                        {ex.turma || 'turma'} · progresso {ex.progresso_pct ?? 0}%
                        {ex.pode_abrir_kanban ? (
                          <>
                            {' '}
                            ·{' '}
                            <button
                              type="button"
                              className="font-bold text-brand-700 hover:underline"
                              onClick={() => navigate(`/execucao/${ex.id_evento_ancora}`)}
                            >
                              ver mesa
                            </button>
                          </>
                        ) : null}
                      </li>
                    ))}
                </ul>
              </div>
            ) : null}

            {hydrated.somenteLeitura ? (
              <div className="mx-auto mb-4 max-w-6xl rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-800 print:hidden">
                <strong>Modo leitura</strong> — esta execução é de outro professor. Você vê o
                progresso, mas não edita a mesa.
              </div>
            ) : null}

            {hydrated.isReplica || irmas.length > 0 ? (
              <div className="mx-auto mb-4 max-w-6xl rounded-xl border border-amber-200 bg-amber-50/80 px-4 py-3 text-xs text-amber-950 print:hidden">
                {hydrated.isReplica ? (
                  <p className="font-semibold">
                    Esta é uma execução replicada do mesmo desafio (sem nova IA).
                  </p>
                ) : (
                  <p className="font-semibold">Este desafio tem outras turmas em execução.</p>
                )}
                {irmas.length > 0 ? (
                  <ul className="mt-2 flex flex-wrap gap-2">
                    {irmas.map((ex) => (
                      <li key={ex.execucao_key}>
                        <button
                          type="button"
                          className="rounded-lg bg-white px-2.5 py-1 font-bold text-bordo shadow-sm hover:bg-brand-50"
                          onClick={() => navigate(`/execucao/${ex.id_evento_ancora}`)}
                        >
                          {labelExecucao(ex)} →
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}

            <StepEduScrum
              plano={hydrated.plano}
              hipotese={hydrated.hipotese}
              problema={hydrated.problema}
              causas={hydrated.causas}
              user={user}
              planoSession={hydrated.planoSession}
              desafioId={hydrated.desafioId || desafio?.id || null}
              initialEventoId={hydrated.initialEventoId}
              initialKanbanState={hydrated.initialKanbanState}
              resumeMode
              readOnly={hydrated.somenteLeitura}
              colaboradores={colaboradores}
              onVoltar={() =>
                navigate(
                  desafio?.id || hydrated.desafioId
                    ? `/desafios/${desafio?.id || hydrated.desafioId}`
                    : '/mesa-do-inovador',
                )
              }
              onAgendaChanged={() =>
                navigate(
                  desafio?.id || hydrated.desafioId
                    ? `/desafios/${desafio?.id || hydrated.desafioId}`
                    : '/mesa-do-inovador',
                )
              }
              onReplicar={desafio?.id && !hydrated.somenteLeitura ? () => setShowReplicar(true) : undefined}
            />
          </>
        ) : null}
      </main>

      {showConvidar && desafio?.sou_dono ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-3 sm:items-center">
          <div className="w-full max-w-md rounded-2xl border border-brand-200 bg-white p-5 shadow-xl">
            <h2 className="font-display text-xl font-bold text-bordo-deep">
              Convidar professor
            </h2>
            <p className="mt-1 text-xs text-bordo-soft">
              Multidisciplinar: o e-mail leva a descrição do desafio e do card. Ao aceitar, o
              desafio entra no mapa dele; cada um planeja as próprias aulas sem ver o do outro.
            </p>
            <form onSubmit={handleConvidar} className="mt-4 space-y-3">
              <label className="block">
                <span className="text-[10px] font-bold uppercase text-bordo">
                  E-mail do professor
                </span>
                <input
                  type="email"
                  className="field-input mt-1"
                  required
                  value={conviteEmail}
                  onChange={(e) => setConviteEmail(e.target.value)}
                  placeholder="professor@escola.edu.br"
                />
              </label>
              <label className="block">
                <span className="text-[10px] font-bold uppercase text-bordo">
                  Card que ele vai realizar
                </span>
                <select
                  className="field-input mt-1"
                  required
                  value={conviteCardId}
                  onChange={(e) => setConviteCardId(e.target.value)}
                >
                  <option value="">Selecione…</option>
                  {cardsParaConvite.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.titulo}
                    </option>
                  ))}
                </select>
              </label>
              {conviteErro ? (
                <p className="text-xs font-semibold text-rose-700">{conviteErro}</p>
              ) : null}
              {conviteMsg ? (
                <p className="text-xs font-semibold text-emerald-800">{conviteMsg}</p>
              ) : null}
              {conviteUrl ? (
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2">
                  {conviteDevMail ? (
                    <p className="text-[10px] font-bold uppercase tracking-wide text-amber-900">
                      Link do convite (local — sem SES)
                    </p>
                  ) : (
                    <p className="text-[10px] font-bold uppercase tracking-wide text-amber-900">
                      Link do convite
                    </p>
                  )}
                  <p className="mt-1 break-all text-[11px] text-bordo-deep">{conviteUrl}</p>
                  <button
                    type="button"
                    className="btn-ghost mt-2 !px-2 !py-1 text-[11px]"
                    onClick={() => {
                      void navigator.clipboard?.writeText(conviteUrl)
                    }}
                  >
                    Copiar link
                  </button>
                </div>
              ) : null}
              {colaboradores.length ? (
                <ul className="max-h-28 space-y-1 overflow-y-auto text-[11px] text-bordo-soft">
                  {colaboradores.map((c) => (
                    <li key={c.id}>
                      {c.email_convidado} · {c.status}
                      {c.card_titulo ? ` · ${c.card_titulo}` : c.papel_ou_parte ? ` · ${c.papel_ou_parte}` : ''}
                    </li>
                  ))}
                </ul>
              ) : null}
              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  className="btn-ghost !px-3 !py-2 text-xs"
                  onClick={() => setShowConvidar(false)}
                >
                  Fechar
                </button>
                <button type="submit" className="btn-primary !px-3 !py-2 text-xs" disabled={conviteBusy}>
                  {conviteBusy ? 'Enviando…' : 'Enviar convite'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      <ReplicarDesafioModal
        open={showReplicar}
        onClose={() => setShowReplicar(false)}
        desafioId={desafio?.id || hydrated?.desafioId}
        sourceEventoId={Number(idEvento)}
        onDone={handleReplicarDone}
      />
    </div>
  )
}
