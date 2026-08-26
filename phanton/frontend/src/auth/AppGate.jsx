import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { useAuth } from './AuthContext'
import LoginPage from './LoginPage'
import RegisterPage from './RegisterPage'
import RestrictedShell from './RestrictedShell'

/**
 * Gate de role — negar UI por padrão:
 * - sem sessão → LoginPage (ou cadastro com código)
 * - restricted_tester / usuario_executor → só Simulação
 * - admin (token ou “admin local”) → App completo
 */
export default function AppGate({ apiBase, children }) {
  const { user, booting, isRestricted, isAuthenticated } = useAuth()
  const [authView, setAuthView] = useState(
    typeof window !== 'undefined' && window.location.hash === '#cadastro'
      ? 'register'
      : 'login',
  )

  if (booting) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <Loader2 className="h-8 w-8 animate-spin text-teal-700" />
      </div>
    )
  }

  if (!isAuthenticated) {
    if (authView === 'register') {
      return (
        <RegisterPage
          onGoLogin={() => {
            if (typeof window !== 'undefined') {
              window.history.replaceState({}, '', window.location.pathname)
            }
            setAuthView('login')
          }}
        />
      )
    }
    return (
      <LoginPage
        onGoRegister={() => {
          if (typeof window !== 'undefined') {
            window.history.replaceState({}, '', `${window.location.pathname}#cadastro`)
          }
          setAuthView('register')
        }}
      />
    )
  }

  if (isRestricted) {
    return <RestrictedShell apiBase={apiBase} />
  }

  return children
}
