import { Navigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { LoadingPanel } from "@/components/StatePanels";
import { consumeReturnUrl } from "@/lib/returnUrl";

/** Mantém /auth/callback na URL até o AuthProvider consumir o code OIDC. */
export function AuthCallbackPage() {
  const auth = useAuth();

  if (auth.status === "authenticated") {
    const dest = consumeReturnUrl("/assessments");
    return <Navigate to={dest} replace />;
  }
  if (auth.status === "anonymous" || auth.status === "invalid_session") {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-16">
      <LoadingPanel title="Concluindo login…" />
    </div>
  );
}
