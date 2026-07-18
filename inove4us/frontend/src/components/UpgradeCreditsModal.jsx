import { useEffect, useState } from 'react'
import { api } from '../lib/api'

const ERROR_TOAST =
  'Não foi possível gerar o pagamento no momento. Tente novamente.'

/**
 * Freemium → checkout seguro via backend (proxy Action Hub).
 */
export default function UpgradeCreditsModal({ open, onClose }) {
  const [isLoading, setIsLoading] = useState(false)
  const [toast, setToast] = useState('')

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
      const data = await api.createBillingCheckout('golive-50')
      const checkoutUrl = data?.checkout_url
      if (!checkoutUrl) {
        throw new Error('checkout_url ausente')
      }
      window.location.href = checkoutUrl
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
            Plano gratuito
          </p>
          <h2
            id="upgrade-credits-title"
            className="mt-2 font-display text-2xl font-bold leading-snug text-bordo-deep"
          >
            Você atingiu o seu limite gratuito!
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-bordo-soft">
            Seus 10 planejamentos gratuitos foram utilizados. Para continuar criando aulas com a
            IA, faça o upgrade para a versão Premium.
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
              {isLoading ? 'Gerando link seguro...' : 'Fazer Upgrade Agora'}
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
