import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'

const ERROR_TOAST =
  'Não foi possível gerar o pagamento no momento. Tente novamente.'

/**
 * Freemium → checkout Brick white-label no Action Hub (mesmo padrão PanelDX).
 * @param {object} props
 * @param {boolean} props.open
 * @param {() => void} props.onClose
 * @param {boolean} [props.exhausted] — true quando o uso foi bloqueado por falta de créditos
 */
export default function UpgradeCreditsModal({ open, onClose, exhausted = false }) {
  const { user } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [toast, setToast] = useState('')

  const saldo = Number(user?.creditos_ia)
  const semCreditos =
    exhausted || (Number.isFinite(saldo) && saldo <= 0)

  useEffect(() => {
    if (!open) {
      setIsLoading(false)
      setToast('')
    }
  }, [open])

  useEffect(() => {
    if (!toast) return undefined
    const t = window.setTimeout(() => setToast(''), 4500)
    return () => window.clearTimeout(t)
  }, [toast])

  async function handleUpgrade() {
    if (isLoading) return
    setIsLoading(true)
    setToast('')
    try {
      // Vitrine Hub (escolhe plano) → depois Brick — padrão PanelDX
      const data = await api.getBillingPlansUrl()
      const plansUrl = data?.url
      if (!plansUrl) {
        throw new Error('plans url ausente')
      }
      try {
        sessionStorage.setItem(
          'i4_credits_before_checkout',
          String(Number(user?.creditos_ia ?? 0)),
        )
      } catch {
        /* ignore */
      }
      window.location.href = plansUrl
    } catch {
      setIsLoading(false)
      setToast(ERROR_TOAST)
    }
  }

  if (!open) return null

  return (
    <>
      <div
        className="fixed inset-0 z-[100] flex items-end justify-center bg-bordo-deep/50 p-4 sm:items-center"
        role="dialog"
        aria-modal="true"
        aria-labelledby="upgrade-credits-title"
        onClick={(e) => {
          if (isLoading) return
          if (e.target === e.currentTarget) onClose?.()
        }}
      >
        <div className="w-full max-w-md rounded-2xl border border-brand-200 bg-white p-6 shadow-soft sm:p-7">
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
            Seus créditos
          </p>
          <h2
            id="upgrade-credits-title"
            className="mt-2 font-display text-2xl font-bold leading-snug text-bordo-deep"
          >
            {semCreditos
              ? 'Seus créditos acabaram'
              : 'Quer mais créditos?'}
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-bordo-soft">
            {semCreditos ? (
              <>
                Você usou todos os planejamentos disponíveis. Faça o upgrade para continuarmos
                resolvendo desafios e criando planos de aula juntos.
              </>
            ) : (
              <>
                Você tem{' '}
                <span className="font-semibold text-bordo">
                  {Number.isFinite(saldo) ? saldo : '—'} créditos
                </span>{' '}
                disponíveis. Escolha um pacote para ampliar o uso do inove4us na resolução de
                mais desafios e na criação de mais planos de aulas.
              </>
            )}
          </p>

          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              className="btn-ghost !px-4 !py-2.5 text-sm"
              onClick={onClose}
              disabled={isLoading}
            >
              Cancelar
            </button>
            <button
              type="button"
              className="btn-primary !px-4 !py-2.5 text-sm disabled:cursor-wait disabled:opacity-70"
              onClick={handleUpgrade}
              disabled={isLoading}
            >
              {isLoading ? 'Abrindo planos...' : 'Ver planos'}
            </button>
          </div>
        </div>
      </div>

      {toast ? (
        <div
          role="status"
          className="fixed bottom-8 left-1/2 z-[110] w-[min(92vw,28rem)] -translate-x-1/2 animate-fade-in rounded-2xl border border-rose-200 bg-white px-4 py-3 text-center text-sm font-medium text-rose-900 shadow-soft"
        >
          {toast}
        </div>
      ) : null}
    </>
  )
}
