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
const ImprovementCaseDetailPage = lazy(() =>
  import("@/pages/ImprovementCaseDetailPage").then((m) => ({
    default: m.ImprovementCaseDetailPage,
  })),
);
const CockpitPage = lazy(() =>
  import("@/pages/CockpitPage").then((m) => ({ default: m.CockpitPage })),
);
const GuidedTourPage = lazy(() =>
  import("@/pages/GuidedTourPage").then((m) => ({ default: m.GuidedTourPage })),
);
const ExecutionLayout = lazy(() =>
  import("@/execution/ExecutionLayout").then((m) => ({ default: m.ExecutionLayout })),
);
const BoardPage = lazy(() =>
  import("@/execution/BoardPage").then((m) => ({ default: m.BoardPage })),
);
const SquadsPage = lazy(() =>
  import("@/execution/SquadsPage").then((m) => ({ default: m.SquadsPage })),
);
const SprintsPage = lazy(() =>
  import("@/execution/SprintsPage").then((m) => ({ default: m.SprintsPage })),
);
const CeremoniesPage = lazy(() =>
  import("@/execution/CeremoniesPage").then((m) => ({ default: m.CeremoniesPage })),
);
const CardDetailPage = lazy(() =>
  import("@/execution/CardDetailPage").then((m) => ({ default: m.CardDetailPage })),
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
                <Route path="cockpit" element={<CockpitPage />} />
                <Route path="assessments" element={<AssessmentsPage />} />
                <Route path="execution" element={<ExecutionLayout />}>
                  <Route index element={<BoardPage />} />
                  <Route path="sprints" element={<SprintsPage />} />
                  <Route path="squads" element={<SquadsPage />} />
                  <Route path="ceremonies" element={<CeremoniesPage />} />
                </Route>
                <Route path="execution/cards/:actionItemId" element={<CardDetailPage />} />
                <Route
                  path="improvement-cases/:caseId"
                  element={<ImprovementCaseDetailPage />}
                />
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
