import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Dashboard from "./components/Dashboard";
import DetalhesConsulta from "./components/DetalhesConsulta";
import ImportacoesConsulta from "./components/ImportacoesConsulta";
import GuestRoute from "./components/GuestRoute";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider, useAuth } from "./context/AuthContext";
import ConfiguracaoParametros from "./pages/ConfiguracaoParametros";
import Login from "./pages/Login";

function RootRedirect() {
  const { autenticado } = useAuth();
  return <Navigate to={autenticado ? "/dashboard" : "/login"} replace />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <GuestRoute>
            <Login />
          </GuestRoute>
        }
      />

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/analise"
        element={
          <ProtectedRoute>
            <Navigate to="/dashboard" replace />
          </ProtectedRoute>
        }
      />

      <Route
        path="/parametros"
        element={
          <ProtectedRoute>
            <ConfiguracaoParametros />
          </ProtectedRoute>
        }
      />

      <Route
        path="/importacoes"
        element={
          <ProtectedRoute>
            <ImportacoesConsulta />
          </ProtectedRoute>
        }
      />

      <Route
        path="/detalhes"
        element={
          <ProtectedRoute>
            <DetalhesConsulta />
          </ProtectedRoute>
        }
      />

      <Route
        path="/configuracao"
        element={
          <ProtectedRoute>
            <Navigate to="/parametros" replace />
          </ProtectedRoute>
        }
      />

      <Route path="/" element={<RootRedirect />} />
      <Route path="*" element={<RootRedirect />} />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
