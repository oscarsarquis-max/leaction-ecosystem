import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { lazy } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { AuthCallbackPage } from "@/pages/AuthCallbackPage";
import { Hotpage } from "@/public/Hotpage";
import { LoginPage } from "@/pages/LoginPage";

const AssessmentsPage = lazy(() =>
  import("@/pages/AssessmentsPage").then((m) => ({ default: m.AssessmentsPage })),
);
const NewAssessmentPage = lazy(() =>
  import("@/pages/NewAssessmentPage").then((m) => ({
    default: m.NewAssessmentPage,
  })),
);
const AssessmentDetailPage = lazy(() =>
  import("@/pages/AssessmentDetailPage").then((m) => ({
    default: m.AssessmentDetailPage,
  })),
);
const AssessmentEntryPage = lazy(() =>
  import("@/pages/AssessmentEntryPage").then((m) => ({
    default: m.AssessmentEntryPage,
  })),
);
const AssessmentGuidedPage = lazy(() =>
  import("@/pages/AssessmentGuidedPage").then((m) => ({
    default: m.AssessmentGuidedPage,
  })),
);
const AssessmentLobby = lazy(() =>
  import("@/pages/AssessmentLobby").then((m) => ({ default: m.AssessmentLobby })),
);
const AssessmentWorkPage = lazy(() =>
  import("@/pages/AssessmentWorkPage").then((m) => ({
    default: m.AssessmentWorkPage,
  })),
);
const AssessmentAuditPlanPage = lazy(() =>
  import("@/pages/AssessmentAuditPlanPage").then((m) => ({
    default: m.AssessmentAuditPlanPage,
  })),
);
const AssessmentEvolutionPage = lazy(() =>
  import("@/pages/AssessmentEvolutionPage").then((m) => ({
    default: m.AssessmentEvolutionPage,
  })),
);
const GuidedTourPage = lazy(() =>
  import("@/pages/GuidedTourPage").then((m) => ({ default: m.GuidedTourPage })),
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <OrganizationProvider>
          <BrowserRouter>
            <Routes>
              {/* Público — sem AppShell, sem Assistente, sem tenant. */}
              <Route path="/" element={<Hotpage />} />
              <Route path="login" element={<LoginPage />} />
              {/* Não redirecionar — o code OIDC precisa permanecer na URL. */}
              <Route path="auth/callback" element={<AuthCallbackPage />} />

              <Route element={<AppShell />}>
                <Route path="guided-tour" element={<GuidedTourPage />} />
                <Route path="assessments" element={<AssessmentsPage />} />
                <Route path="assessments/new" element={<NewAssessmentPage />} />
                <Route
                  path="assessments/:assessmentId/guided"
                  element={<AssessmentGuidedPage />}
                />
                <Route
                  path="assessments/:assessmentId/work"
                  element={<AssessmentWorkPage />}
                />
                <Route
                  path="assessments/:assessmentId/audit-plan"
                  element={<AssessmentAuditPlanPage />}
                />
                <Route
                  path="assessments/:assessmentId/advanced"
                  element={<AssessmentDetailPage />}
                />
                <Route
                  path="assessments/:assessmentId/evolution"
                  element={<AssessmentEvolutionPage />}
                />
                <Route
                  path="assessments/:assessmentId"
                  element={<AssessmentEntryPage />}
                />
                <Route
                  path="avaliacao/lobby-preview"
                  element={<AssessmentLobby />}
                />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </OrganizationProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
