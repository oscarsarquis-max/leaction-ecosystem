import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AuthBalanceSync, AuthProvider, useAuth } from './lib/auth'
import BrandLogo from './components/BrandLogo'
import AssistenteChat from './components/AssistenteChat'
import CrmPageTracker from './components/CrmPageTracker'
import NinaOnboarding from './components/NinaOnboarding'
import Acesso from './pages/Acesso'
import PaymentFailurePage from './pages/billing/PaymentFailurePage'
import PaymentPendingPage from './pages/billing/PaymentPendingPage'
import PaymentSuccessPage from './pages/billing/PaymentSuccessPage'
import DailyDashboard from './pages/DailyDashboard'
import DailyPlanner from './pages/DailyPlanner'
import DesafioPage from './pages/DesafioPage'
import ExecucaoPage from './pages/ExecucaoPage'
import ConvitePage from './pages/ConvitePage'
import ImportacoesPage from './pages/ImportacoesPage'
import InstituicoesPage from './pages/InstituicoesPage'
import MesaDoInovador from './pages/MesaDoInovador'

function LoadingScreen({ label = 'Carregando…' }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-6">
      <BrandLogo
        variant="internal"
        className="h-28 w-auto max-w-[400px] object-contain"
      />
      <p className="text-sm text-bordo-soft">{label}</p>
    </div>
  )
}

function safeNextPath(raw) {
  if (!raw || typeof raw !== 'string') return null
  const t = raw.trim()
  if (!t.startsWith('/') || t.startsWith('//')) return null
  if (t.startsWith('/acesso')) return null
  return t
}

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <LoadingScreen label="Carregando sessão…" />
  if (!user) {
    const next = encodeURIComponent(`${location.pathname}${location.search || ''}`)
    return <Navigate to={`/acesso?next=${next}`} replace />
  }
  return (
    <>
      {children}
      <NinaOnboarding />
      <AssistenteChat />
    </>
  )
}

function AppRoutes() {
  const { user, loading } = useAuth()
  const location = useLocation()
  const nextParam = safeNextPath(new URLSearchParams(location.search).get('next'))

  if (loading) return <LoadingScreen />

  return (
    <Routes>
      <Route
        path="/acesso"
        element={
          user ? (
            <Navigate to={nextParam || '/mesa-do-inovador'} replace />
          ) : (
            <Acesso />
          )
        }
      />
      <Route path="/convite/:token" element={<ConvitePage />} />
      <Route
        path="/mesa-do-inovador"
        element={
          <ProtectedRoute>
            <MesaDoInovador />
          </ProtectedRoute>
        }
      />
      <Route
        path="/desafio"
        element={
          <ProtectedRoute>
            <DesafioPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/instituicoes"
        element={
          <ProtectedRoute>
            <InstituicoesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/importacoes"
        element={
          <ProtectedRoute>
            <ImportacoesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dia-a-dia"
        element={
          <ProtectedRoute>
            <DailyDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dia-a-dia/nova"
        element={
          <ProtectedRoute>
            <DailyPlanner />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dia-a-dia/:id"
        element={
          <ProtectedRoute>
            <DailyPlanner />
          </ProtectedRoute>
        }
      />
      <Route
        path="/execucao/:idEvento"
        element={
          <ProtectedRoute>
            <ExecucaoPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pagamento/sucesso"
        element={
          <ProtectedRoute>
            <PaymentSuccessPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pagamento/pendente"
        element={
          <ProtectedRoute>
            <PaymentPendingPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pagamento/erro"
        element={
          <ProtectedRoute>
            <PaymentFailurePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="*"
        element={<Navigate to={user ? '/mesa-do-inovador' : '/acesso'} replace />}
      />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AuthBalanceSync />
      <CrmPageTracker />
      <AppRoutes />
    </AuthProvider>
  )
}
