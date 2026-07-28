import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import BrandLogo from '../components/BrandLogo'
import ReplicarDesafioModal from '../components/ReplicarDesafioModal'

/**
 * Aceite de convite pontual — reusa login /acesso?next=…
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
  const [showCriar, setShowCriar] = useState(false)
  const autoAceitar = searchParams.get('aceitar') === '1'

  const nextLogin = useMemo(
    () => `/acesso?next=${encodeURIComponent(`/convite/${token}`)}`,
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
    try {
      const data = await api.aceitarConvite(token)
      setShowCriar(true)
      await load()
      if (data.desafio_id) {
        /* modal abre com desafio */
      }
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
            Convite pontual · sem nova IA
          </p>
          <h1 className="mt-1 font-display text-2xl font-bold text-bordo-deep">
            Colaborar neste desafio
          </h1>

          {erro ? (
            <p className="mt-4 rounded-lg bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-800">
              {erro}
            </p>
          ) : null}

          {!convite ? (
            <p className="mt-4 text-sm text-bordo-soft">Convite não encontrado ou expirado.</p>
          ) : (
            <>
              <p className="mt-3 text-sm text-bordo-soft">
                <span className="font-semibold text-bordo">{d?.dono_nome || 'Um professor'}</span>{' '}
                convidou você para uma parte deste desafio.
              </p>
              {convite.papel_ou_parte ? (
                <p className="mt-2 rounded-lg bg-brand-50 px-3 py-2 text-sm font-semibold text-bordo">
                  Parte sugerida: {convite.papel_ou_parte}
                </p>
              ) : null}

              <div className="mt-5 space-y-3 rounded-xl border border-brand-100 bg-brand-50/40 p-4">
                <p className="text-[10px] font-bold uppercase tracking-wide text-bordo-soft">
                  Conteúdo do desafio (somente leitura)
                </p>
                <h2 className="font-display text-lg font-bold text-bordo-deep">
                  {d?.titulo || 'Desafio'}
                </h2>
                {d?.tema ? (
                  <p className="text-xs text-bordo-soft">
                    Tema: <span className="font-semibold text-bordo">{d.tema}</span>
                  </p>
                ) : null}
                {d?.hipotese ? (
                  <p className="text-sm text-bordo">
                    <span className="font-bold">Hipótese:</span> {d.hipotese}
                  </p>
                ) : null}
                {Array.isArray(d?.causas) && d.causas.length ? (
                  <ul className="list-disc space-y-1 pl-5 text-xs text-bordo-soft">
                    {d.causas.map((c, i) => (
                      <li key={i}>
                        {typeof c === 'string' ? c : c?.titulo || c?.descricao || JSON.stringify(c)}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>

              <p className="mt-3 text-[11px] text-bordo-soft">
                Status: <strong>{convite.status}</strong>
                {convite.email_convidado ? ` · ${convite.email_convidado}` : ''}
              </p>

              {!user ? (
                <div className="mt-5 flex flex-wrap gap-2">
                  <Link to={nextLogin} className="btn-primary !px-4 !py-2 text-sm">
                    Entrar para aceitar
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
                    {busy ? 'Aceitando…' : 'Aceitar e criar minha parte'}
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
                  <p className="text-sm font-semibold text-emerald-800">Convite aceito.</p>
                  <button
                    type="button"
                    className="btn-primary !px-4 !py-2 text-sm"
                    onClick={() => setShowCriar(true)}
                  >
                    Criar minha execução
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

      <ReplicarDesafioModal
        open={showCriar}
        onClose={() => setShowCriar(false)}
        desafioId={convite?.desafio_id}
        sourceEventoId={null}
        suggestFromDesafio
        onDone={(data) => {
          const first = data?.eventos?.[0]
          if (first?.id_evento) navigate(`/execucao/${first.id_evento}`)
          else navigate('/mesa-do-inovador')
        }}
      />
    </div>
  )
}
