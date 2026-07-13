import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import RequireAuth from './components/RequireAuth';
import { ROUTE_PERMISSIONS } from './config/rbac';
import Acesso from './pages/Acesso';
import Assessment from './pages/Assessment';
import AvaliacaoDetail from './pages/AvaliacaoDetail';
import Avaliacoes from './pages/Avaliacoes';
import Cadastro from './pages/Cadastro';
import Dashboard from './pages/Dashboard';
import DiagnosticReport from './pages/DiagnosticReport';
import MeusDados from './pages/MeusDados';
import PlanoGeral from './pages/PlanoGeral';
import KanbanBoard from './pages/KanbanBoard';
import KaizenBoard from './components/KaizenBoard';
import FrameworkBuilder from './pages/FrameworkBuilder';
import PortalLauncher from './pages/PortalLauncher';
import Questoes from './pages/Questoes';
import Usuarios from './pages/Usuarios';
import OrganizationSettings from './pages/OrganizationSettings';
import OperationalSitesManager from './pages/OperationalSitesManager';
import OperationalPlanning from './pages/OperationalPlanning';
import OperationalReports from './pages/OperationalReports';
import TdPlanManager from './pages/TdPlanManager';
import TdKanban from './pages/TdKanban';
import ProfessionalsManager from './pages/ProfessionalsManager';
import OkrDashboard from './pages/OkrDashboard';

export default function App() {
  return (
    <Routes>
      <Route path="/acesso" element={<Acesso />} />
      <Route path="/acesso/:accessCode" element={<Acesso />} />
      <Route path="/cadastro" element={<Cadastro />} />

      <Route
        path="/portal"
        element={
          <RequireAuth>
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/portal']}>
              <PortalLauncher />
            </ProtectedRoute>
          </RequireAuth>
        }
      />

      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route
          index
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/']}>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="my-assessment"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/my-assessment']}>
              <Assessment />
            </ProtectedRoute>
          }
        />
        <Route path="diagnostico" element={<Navigate to="/my-assessment" replace />} />
        <Route
          path="meus-dados"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/meus-dados']}>
              <MeusDados />
            </ProtectedRoute>
          }
        />
        <Route
          path="plano-geral"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/plano-geral']}>
              <PlanoGeral />
            </ProtectedRoute>
          }
        />
        <Route
          path="kanban"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/kanban']}>
              <KanbanBoard />
            </ProtectedRoute>
          }
        />
        <Route
          path="kaizen"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/kaizen']}>
              <KaizenBoard />
            </ProtectedRoute>
          }
        />
        <Route
          path="relatorio/:submissionId"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/']}>
              <DiagnosticReport />
            </ProtectedRoute>
          }
        />
        <Route
          path="avaliacoes"
          element={<Navigate to="/my-assessment" replace />}
        />
        <Route
          path="avaliacoes/:id"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/avaliacoes']}>
              <AvaliacaoDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="settings/organization"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/settings/organization']}>
              <OrganizationSettings />
            </ProtectedRoute>
          }
        />
        <Route
          path="operational/sites"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/operational/sites']}>
              <OperationalSitesManager />
            </ProtectedRoute>
          }
        />
        <Route
          path="operational/planning"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/operational/planning']}>
              <OperationalPlanning />
            </ProtectedRoute>
          }
        />
        <Route
          path="operational/reports"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/operational/reports']}>
              <OperationalReports />
            </ProtectedRoute>
          }
        />
        <Route
          path="professionals-manager"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/professionals-manager']}>
              <ProfessionalsManager />
            </ProtectedRoute>
          }
        />
        <Route
          path="strategic-planning"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/strategic-planning']}>
              <OkrDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="td/plan"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/td/plan']}>
              <TdPlanManager />
            </ProtectedRoute>
          }
        />
        <Route
          path="td/kanban"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/td/kanban']}>
              <TdKanban />
            </ProtectedRoute>
          }
        />
        {/* Compatibilidade: rotas antigas redirecionam para a Área Operacional */}
        <Route path="operational-planning" element={<Navigate to="/operational/planning" replace />} />
        <Route path="operational-reports" element={<Navigate to="/operational/reports" replace />} />
        <Route
          path="usuarios"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/usuarios']}>
              <Usuarios />
            </ProtectedRoute>
          }
        />
        <Route
          path="questoes"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/questoes']}>
              <Questoes />
            </ProtectedRoute>
          }
        />
        <Route
          path="builder"
          element={
            <ProtectedRoute roles={ROUTE_PERMISSIONS['/builder']}>
              <FrameworkBuilder />
            </ProtectedRoute>
          }
        />
        <Route path="assessment" element={<Navigate to="/my-assessment" replace />} />
        <Route path="frameworks" element={<Navigate to="/builder" replace />} />
      </Route>

      <Route path="*" element={<Navigate to="/acesso" replace />} />
    </Routes>
  );
}
