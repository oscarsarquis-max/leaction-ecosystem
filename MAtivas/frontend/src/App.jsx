import { Routes, Route, useLocation } from 'react-router-dom'
import Home from './pages/Home.jsx'
import Exemplo from './pages/Exemplo.jsx'
import Resultado from './pages/Resultado.jsx'
import Cadastro from './pages/Cadastro.jsx'
import Roteiro from './pages/Roteiro.jsx'
import Livro from './pages/Livro.jsx'
import Admin from './pages/Admin.jsx'
import ProtectedAdmin from './components/ProtectedAdmin.jsx'

function App() {
  const { pathname } = useLocation()
  const isAdminRoute = pathname.startsWith('/admin')

  return (
    <div className={isAdminRoute ? 'admin-root' : 'app-shell'}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/exemplo" element={<Exemplo />} />
        <Route path="/resultado" element={<Resultado />} />
        <Route path="/cadastro" element={<Cadastro />} />
        <Route path="/roteiro" element={<Roteiro />} />
        <Route path="/livro" element={<Livro />} />
        <Route
          path="/admin"
          element={
            <ProtectedAdmin>
              <Admin />
            </ProtectedAdmin>
          }
        />
      </Routes>
    </div>
  )
}

export default App
