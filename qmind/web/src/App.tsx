import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { AuthCallbackPage } from "@/pages/AuthCallbackPage";
import { AssessmentsPage } from "@/pages/AssessmentsPage";
import { NewAssessmentPage } from "@/pages/NewAssessmentPage";
import { AssessmentDetailPage } from "@/pages/AssessmentDetailPage";
import { AssessmentEntryPage } from "@/pages/AssessmentEntryPage";
import { AssessmentGuidedPage } from "@/pages/AssessmentGuidedPage";
import { AssessmentLobby } from "@/pages/AssessmentLobby";
import { AssessmentWorkPage } from "@/pages/AssessmentWorkPage";

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
              {/* Não redirecionar — o code OIDC precisa permanecer na URL. */}
              <Route path="auth/callback" element={<AuthCallbackPage />} />
              <Route element={<AppShell />}>
                <Route index element={<Navigate to="/assessments" replace />} />
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
                  path="assessments/:assessmentId/advanced"
                  element={<AssessmentDetailPage />}
                />
                <Route
                  path="assessments/:assessmentId"
                  element={<AssessmentEntryPage />}
                />
                {/* Preview estático do layout visual (sem dados de negócio). */}
                <Route
                  path="avaliacao/lobby-preview"
                  element={<AssessmentLobby />}
                />
              </Route>
              <Route path="*" element={<Navigate to="/assessments" replace />} />
            </Routes>
          </BrowserRouter>
        </OrganizationProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
