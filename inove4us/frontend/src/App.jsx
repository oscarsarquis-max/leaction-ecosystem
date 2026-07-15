import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './lib/auth'
import Acesso from './pages/Acesso'
import MesaDoInovador from './pages/MesaDoInovador'

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-bordo-soft">
        Carregando sessão…
      </div>
    )
  }
  if (!user) return <Navigate to="/acesso" replace />
  return children
}

function AppRoutes() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-bordo-soft">
        Carregando…
      </div>
    )
  }

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
