import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import AdminLayout from './layouts/AdminLayout'
import { AuthProvider, useAuth } from './lib/auth'
import { firstAccessiblePath, hasAnyZona, pathAllowed } from './lib/rbac'
import Acesso from './pages/Acesso'
import Dashboard from './pages/Dashboard'
import TeamManagement from './pages/TeamManagement'
import PedagogicalEditor from './pages/PedagogicalEditor'
import SecretariaOperacional from './pages/SecretariaOperacional'

function ZoneGate({ zonasRequired, children }) {
  const { user } = useAuth()
  const location = useLocation()
  const zonas = user?.zonas || []

  if (!hasAnyZona(zonas, zonasRequired)) {
    return <Navigate to={firstAccessiblePath(zonas)} replace state={{ from: location }} />
  }
  return children
}

function ProtectedShell() {
  const { authenticated, booting, user, logout } = useAuth()
  const location = useLocation()

  if (booting) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-panel text-sm text-muted">
        Carregando…
      </div>
    )
  }

  if (!authenticated) {
    const next = `${location.pathname}${location.search}`
    const q = next && next !== '/acesso' ? `?next=${encodeURIComponent(next)}` : ''
    return <Navigate to={`/acesso${q}`} replace />
  }

  const zonas = user?.zonas || []
  if (!pathAllowed(location.pathname, zonas) && location.pathname !== '/') {
    return <Navigate to={firstAccessiblePath(zonas)} replace />
  }

  const gestorNome = user?.cargo
    ? `${user.nome} · ${user.cargo}`
    : user?.nome || 'Gestor'

  return (
    <AdminLayout
      escolaNome="Colégio Horizonte Inovador"
      gestorNome={gestorNome}
      zonas={zonas}
      onSair={logout}
    >
      <Outlet />
    </AdminLayout>
  )
}

function HomeEntry() {
  const { user } = useAuth()
  const zonas = user?.zonas || []
  if (!pathAllowed('/', zonas)) {
    return <Navigate to={firstAccessiblePath(zonas)} replace />
  }
  return <Dashboard />
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/acesso" element={<Acesso />} />
          <Route element={<ProtectedShell />}>
            <Route
              index
              element={
                <ZoneGate zonasRequired={['pedagogico']}>
                  <HomeEntry />
                </ZoneGate>
              }
            />
            <Route
              path="equipe"
              element={
                <ZoneGate zonasRequired={['administrativo']}>
                  <TeamManagement />
                </ZoneGate>
              }
            />
            <Route
              path="secretaria"
              element={
                <ZoneGate zonasRequired={['operacional']}>
                  <SecretariaOperacional />
                </ZoneGate>
              }
            />
            <Route
              path="editor-pedagogico"
              element={
                <ZoneGate zonasRequired={['pedagogico']}>
                  <PedagogicalEditor />
                </ZoneGate>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
