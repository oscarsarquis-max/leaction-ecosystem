import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './lib/auth'
import BrandLogo from './components/BrandLogo'
import Acesso from './pages/Acesso'
import DesafioPage from './pages/DesafioPage'
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

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingScreen label="Carregando sessão…" />
  if (!user) return <Navigate to="/acesso" replace />
  return children
}

function AppRoutes() {
  const { user, loading } = useAuth()

  if (loading) return <LoadingScreen />

  return (
    <Routes>
      <Route
        path="/acesso"
        element={user ? <Navigate to="/mesa-do-inovador" replace /> : <Acesso />}
      />
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
        path="*"
        element={<Navigate to={user ? '/mesa-do-inovador' : '/acesso'} replace />}
      />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
