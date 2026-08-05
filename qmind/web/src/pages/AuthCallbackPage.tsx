import { Navigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { LoadingPanel } from "@/components/StatePanels";

/** Mantém /auth/callback na URL até o AuthProvider consumir o code OIDC. */
export function AuthCallbackPage() {
  const auth = useAuth();

  if (auth.status === "authenticated") {
    return <Navigate to="/assessments" replace />;
  }
  if (auth.status === "anonymous" || auth.status === "invalid_session") {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-16">
      <LoadingPanel title="Concluindo login…" />
    </div>
  );
}
