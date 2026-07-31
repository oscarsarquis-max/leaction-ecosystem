import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import BrandLogo from '../components/BrandLogo'

/**
 * Aceite de convite multidisciplinar — 1 clique adiciona o desafio ao grafo do convidado.
 * Depois ele planeja as próprias aulas (isolado do outro professor).
 */
export default function ConvitePage() {
  const { token } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')
  const [convite, setConvite] = useState(null)
  const [busy, setBusy] = useState(false)
  const [aceitoMsg, setAceitoMsg] = useState('')
  const autoAceitar = searchParams.get('aceitar') === '1'

  const nextLogin = useMemo(
    () => `/acesso?next=${encodeURIComponent(`/convite/${token}?aceitar=1`)}`,
    [token],
  )

  async function load() {
    setLoading(true)
    setErro('')
    try {
      const data = await api.getConvite(token)
      setConvite(data.convite || null)
    } catch (err) {
      setErro(err.message || 'Convite inválido.')
      setConvite(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!token) return
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, user?.id_clie])

  useEffect(() => {
    if (!autoAceitar || !user || !convite?.pode_aceitar || busy) return
    void handleAceitar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoAceitar, user, convite?.pode_aceitar])

  async function handleAceitar() {
    setBusy(true)
    setErro('')
    setAceitoMsg('')
    try {
      const data = await api.aceitarConvite(token)
      await load()
      const idEvento = data.id_evento || data.evento?.id_evento
      setAceitoMsg(
        'Desafio adicionado ao seu mapa. Agora planeje as suas aulas — o outro professor não vê este planejamento.',
      )
      if (idEvento) {
        navigate(`/execucao/${idEvento}`, {
          replace: true,
          state: { fromConvite: true },
        })
        return
      }
      navigate('/mesa-do-inovador', { replace: true })
    } catch (err) {
      setErro(err.message || 'Não foi possível aceitar.')
    } finally {
      setBusy(false)
    }
  }

  async function handleRecusar() {
    setBusy(true)
    setErro('')
    try {
      await api.recusarConvite(token)
      await load()
    } catch (err) {
      setErro(err.message || 'Não foi possível recusar.')
    } finally {
      setBusy(false)
    }
  }

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-bordo-soft">Carregando convite…</p>
      </div>
    )
  }

  const d = convite?.desafio

  return (
    <div className="min-h-screen px-4 py-10">
      <div className="mx-auto max-w-lg">
        <div className="mb-6 flex justify-center">
          <BrandLogo variant="internal" className="h-20 w-auto object-contain" />
        </div>
        <div className="rounded-2xl border border-brand-200 bg-white p-6 shadow-soft">
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
            Convite multidisciplinar · sem nova IA
          </p>
          <h1 className="mt-1 font-display text-2xl font-bold text-bordo-deep">
            Entrar neste desafio
          </h1>

          {erro ? (
            <p className="mt-4 rounded-lg bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-800">
              {erro}
            </p>
          ) : null}
          {aceitoMsg ? (
            <p className="mt-4 rounded-lg bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-900">
              {aceitoMsg}
            </p>
          ) : null}

          {!convite ? (
            <p className="mt-4 text-sm text-bordo-soft">Convite não encontrado ou expirado.</p>
          ) : (
            <>
              <p className="mt-3 text-sm text-bordo-soft">
                <span className="font-semibold text-bordo">{d?.dono_nome || 'Um professor'}</span>{' '}
                convidou{' '}
                <span className="font-semibold text-bordo">{convite.email_convidado}</span> para
                uma parte deste desafio.
              </p>

              <div className="mt-5 space-y-3 rounded-xl border border-brand-100 bg-brand-50/40 p-4">
                <p className="text-[10px] font-bold uppercase tracking-wide text-bordo-soft">
                  Desafio
                </p>
                <p className="whitespace-pre-wrap text-sm text-bordo">
                  {convite.desafio_descricao || d?.descricao || d?.titulo || 'Desafio'}
                </p>
              </div>

              <div className="mt-3 space-y-2 rounded-xl border border-emerald-100 bg-emerald-50/50 p-4">
                <p className="text-[10px] font-bold uppercase tracking-wide text-emerald-900">
                  Card associado
                </p>
                <p className="font-display text-base font-bold text-bordo-deep">
                  {convite.card_titulo || convite.papel_ou_parte || 'Card colaborativo'}
                </p>
                {convite.card_descricao ? (
                  <p className="whitespace-pre-wrap text-sm text-bordo">
                    {convite.card_descricao}
                  </p>
                ) : null}
              </div>

              <p className="mt-3 text-[11px] leading-snug text-bordo-soft">
                Com um clique o desafio entra no seu mapa. Em seguida você registra as suas aulas.
                O planejamento de cada professor fica isolado.
              </p>

              <p className="mt-2 text-[11px] text-bordo-soft">
                Status: <strong>{convite.status}</strong>
                {convite.email_convidado ? ` · ${convite.email_convidado}` : ''}
              </p>

              {!user ? (
                <div className="mt-5 flex flex-wrap gap-2">
                  <Link to={nextLogin} className="btn-primary !px-4 !py-2 text-sm">
                    Entrar e aceitar
                  </Link>
                  <Link to="/acesso" className="btn-ghost !px-4 !py-2 text-sm">
                    Ir ao login
                  </Link>
                </div>
              ) : convite.status === 'pendente' && convite.pode_aceitar ? (
                <div className="mt-5 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="btn-primary !px-4 !py-2 text-sm"
                    disabled={busy}
                    onClick={handleAceitar}
                  >
                    {busy ? 'Adicionando…' : 'Aceitar e adicionar ao meu mapa'}
                  </button>
                  <button
                    type="button"
                    className="btn-ghost !px-4 !py-2 text-sm"
                    disabled={busy}
                    onClick={handleRecusar}
                  >
                    Recusar
                  </button>
                </div>
              ) : convite.status === 'pendente' && convite.email_bate === false ? (
                <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900">
                  Você está logado com outro e-mail. Entre com{' '}
                  <strong>{convite.email_convidado}</strong> para aceitar.
                </p>
              ) : convite.status === 'aceito' ? (
                <div className="mt-5 space-y-3">
                  <p className="text-sm font-semibold text-emerald-800">
                    Convite aceito — desafio no seu mapa.
                  </p>
                  <button
                    type="button"
                    className="btn-primary !px-4 !py-2 text-sm"
                    onClick={() => handleAceitar()}
                  >
                    Abrir minha execução
                  </button>
                </div>
              ) : convite.status === 'recusado' ? (
                <p className="mt-4 text-sm text-bordo-soft">Você recusou este convite.</p>
              ) : null}
            </>
          )}

          <div className="mt-6 border-t border-brand-100 pt-4">
            <Link to="/mesa-do-inovador" className="text-xs font-bold text-bordo hover:underline">
              ← Mesa do Inovador
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
