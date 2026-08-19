import { Loader2 } from 'lucide-react'
import { useAuth } from './AuthContext'
import LoginPage from './LoginPage'
import RestrictedShell from './RestrictedShell'

/**
 * Gate de role — negar UI por padrão:
 * - sem sessão → LoginPage
 * - restricted_tester → só Simulação
 * - admin (token ou “admin local”) → App completo
 */
export default function AppGate({ apiBase, children }) {
  const { user, booting, isRestricted, isAuthenticated } = useAuth()

  if (booting) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <Loader2 className="h-8 w-8 animate-spin text-teal-700" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <LoginPage />
  }

  if (isRestricted) {
    return <RestrictedShell apiBase={apiBase} />
  }

  return children
}
