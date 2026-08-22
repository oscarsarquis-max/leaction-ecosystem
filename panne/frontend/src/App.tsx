import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProviderTree } from "./auth/AuthContext";
import { RequireAuth, RequireOrganization, RequirePermission } from "./components/RequireAuth";
import { Shell } from "./components/Shell";
import { BoardPage } from "./pages/BoardPage";
import { CallbackPage } from "./pages/CallbackPage";
import { LoginPage } from "./pages/LoginPage";
import { OrderDetailPage } from "./pages/OrderDetailPage";
import { OrdersPage } from "./pages/OrdersPage";
import { PlanDetailPage } from "./pages/PlanDetailPage";
import { PlansPage } from "./pages/PlansPage";
import { SelectOrgPage } from "./pages/SelectOrgPage";
import { SheetPage } from "./pages/SheetPage";
import { TraceabilityHubPage, TraceabilityPage } from "./pages/TraceabilityPage";
import { OrganizationProvider } from "./session/OrganizationContext";

export function AppRoutes() {
  return (
          <Routes>
            <Route path="/entrar" element={<LoginPage />} />
            <Route path="/callback" element={<CallbackPage />} />
            <Route
              element={
                <RequireAuth>
                  <RequireOrganization>
                    <Shell />
                  </RequireOrganization>
                </RequireAuth>
              }
            >
              <Route path="/organizacao" element={<SelectOrgPage />} />
              <Route
                path="/producao"
                element={
                  <RequirePermission code="production.board.read">
                    <BoardPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/planejamento"
                element={
                  <RequirePermission code="production.plan.read">
                    <PlansPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/planejamento/:planId"
                element={
                  <RequirePermission code="production.plan.read">
                    <PlanDetailPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/ordens"
                element={
                  <RequirePermission code="production.order.read">
                    <OrdersPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/ordens/:orderId"
                element={
                  <RequirePermission code="production.order.read">
                    <OrderDetailPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/ordens/:orderId/fichas/:issueId"
                element={
                  <RequirePermission code="production.order.read">
                    <SheetPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/rastreabilidade"
                element={
                  <RequirePermission code="production.traceability.read">
                    <TraceabilityHubPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/rastreabilidade/:orderId"
                element={<TraceabilityPage />}
              />
              <Route path="/" element={<Navigate to="/producao" replace />} />
            </Route>
          </Routes>
  );
}

export function App() {
  return (
    <AuthProviderTree>
      <OrganizationProvider>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <AppRoutes />
        </BrowserRouter>
      </OrganizationProvider>
    </AuthProviderTree>
  );
}
