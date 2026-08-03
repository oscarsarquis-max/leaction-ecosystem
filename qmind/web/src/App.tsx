import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { AssessmentsPage } from "@/pages/AssessmentsPage";

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
              <Route element={<AppShell />}>
                <Route index element={<Navigate to="/assessments" replace />} />
                <Route path="assessments" element={<AssessmentsPage />} />
              </Route>
              <Route path="*" element={<Navigate to="/assessments" replace />} />
            </Routes>
          </BrowserRouter>
        </OrganizationProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
