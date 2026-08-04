import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import AdminLayout from './layouts/AdminLayout'
import Dashboard from './pages/Dashboard'
import TeamManagement from './pages/TeamManagement'
import PedagogicalEditor from './pages/PedagogicalEditor'

export default function App() {
  function handleSair() {
    // Auth real virá do Flask; MVP só sinaliza a ação.
    window.alert('Sair (mock) — sessão de gestor será encerrada quando a auth estiver ligada.')
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          element={
            <AdminLayout
              escolaNome="Colégio Horizonte Inovador"
              gestorNome="Ana Coordenadora · Coordenador"
              onSair={handleSair}
            />
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="equipe" element={<TeamManagement />} />
          <Route path="editor-pedagogico" element={<PedagogicalEditor />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
