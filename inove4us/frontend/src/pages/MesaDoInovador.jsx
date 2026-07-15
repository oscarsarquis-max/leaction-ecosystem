import { useEffect } from 'react'
import { useAuth } from '../lib/auth'

/**
 * Após o login freemium, abre a Oficina do Inovador fiel ao PanelDX
 * (inovador_dashboard.ejs servida em /inovador/?id_clie=…).
 */
export default function MesaDoInovador() {
  const { user, loading, logout } = useAuth()

  useEffect(() => {
    if (loading) return
    if (!user?.id_clie) return
    window.location.replace(`/inovador/?id_clie=${user.id_clie}`)
  }, [user, loading])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-bordo-soft">
        Carregando sessão…
      </div>
    )
  }

  if (!user) {
    return null
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col items-center justify-center px-6 text-center">
      <p className="text-sm text-bordo-soft">Abrindo a Mesa do Inovador…</p>
      <a
        href={`/inovador/?id_clie=${user.id_clie}`}
        className="btn-primary mt-4"
      >
        Entrar na mesa
      </a>
      <button type="button" onClick={logout} className="btn-ghost mt-3">
        Sair
      </button>
    </main>
  )
}
