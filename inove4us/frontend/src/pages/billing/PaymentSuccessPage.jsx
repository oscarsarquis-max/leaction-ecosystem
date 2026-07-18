import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import BrandLogo from '../../components/BrandLogo'
import { useAuth } from '../../lib/auth'

/**
 * Retorno pós-checkout Mercado Pago (back_urls.success).
 * Força refresh do usuário para trazer creditos_ia fresco do banco.
 */
export default function PaymentSuccessPage() {
  const { user, refresh } = useAuth()
  const [syncing, setSyncing] = useState(true)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        await refresh()
      } finally {
        if (!cancelled) setSyncing(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [refresh])

  const credits =
    user?.creditos_ia != null && Number.isFinite(Number(user.creditos_ia))
      ? Number(user.creditos_ia)
      : null

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-12">
      <BrandLogo
        variant="internal"
        className="mb-8 h-20 w-auto max-w-[280px] object-contain"
      />

      <div className="w-full max-w-md rounded-2xl border border-brand-200 bg-white p-8 text-center shadow-soft">
        <div
          className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 text-emerald-600"
          aria-hidden
        >
          <svg
            className="h-9 w-9"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.5}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>

        <h1 className="mt-5 font-display text-2xl font-bold text-bordo-deep sm:text-3xl">
          Pagamento Aprovado!
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-bordo-soft">
          Seus créditos foram adicionados à sua conta com sucesso.
        </p>

        <p className="mt-4 text-sm font-medium text-bordo">
          {syncing ? (
            <span className="text-bordo-soft">Atualizando saldo…</span>
          ) : credits != null ? (
            <>
              Saldo atual:{' '}
              <span className="font-display text-lg font-bold text-emerald-700">
                {credits} créditos
              </span>
            </>
          ) : null}
        </p>

        <Link
          to="/desafio"
          className="btn-primary mt-8 inline-flex !px-5 !py-3 text-sm"
        >
          Voltar para Meus Planejamentos
        </Link>
      </div>
    </div>
  )
}
