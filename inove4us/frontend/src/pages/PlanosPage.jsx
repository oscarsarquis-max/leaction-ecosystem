import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { api } from '../lib/api'
import BrandLogo from '../components/BrandLogo'

/**
 * Vitrine de planos (equivalente /plans).
 * Solo → redireciona à vitrine Action Hub.
 * Institucional → volta ao Dashboard (sem oferta Hub).
 */
export default function PlanosPage() {
  const { user, loading } = useAuth()
  const [error, setError] = useState('')

  useEffect(() => {
    if (loading || !user || user.is_institutional) return undefined
    let cancelled = false
    ;(async () => {
      try {
        const data = await api.getBillingPlansUrl()
        const url = data?.url
        if (!url) throw new Error('URL de planos indisponível')
        if (!cancelled) window.location.href = url
      } catch (err) {
        if (!cancelled) {
          setError(err?.message || 'Não foi possível abrir a vitrine de planos.')
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [loading, user])

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-6">
        <BrandLogo variant="internal" className="h-24 w-auto object-contain" />
        <p className="text-sm text-bordo-soft">Carregando…</p>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/acesso?next=%2Fplanos" replace />
  }

  if (user.is_institutional) {
    return <Navigate to="/mesa-do-inovador" replace />
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-6">
      <BrandLogo variant="internal" className="h-24 w-auto object-contain" />
      <p className="text-sm text-bordo-soft">
        {error || 'Abrindo vitrine de planos no Action Hub…'}
      </p>
      {error ? (
        <a href="/mesa-do-inovador" className="btn-primary text-sm">
          Voltar ao início
        </a>
      ) : null}
    </div>
  )
}
