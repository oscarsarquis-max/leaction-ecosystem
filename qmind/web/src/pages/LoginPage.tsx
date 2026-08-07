import { useEffect } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { AccessGate } from "@/components/AccessGate";
import {
  consumeReturnUrl,
  isSafeReturnUrl,
  writeReturnUrl,
} from "@/lib/returnUrl";
import { LoadingPanel } from "@/components/StatePanels";

/**
 * Entrada explícita de autenticação — AccessGate associado ao login,
 * sem competir com a hotpage pública.
 */
export function LoginPage() {
  const auth = useAuth();
  const [params] = useSearchParams();

  const returnParam = params.get("return");
  const returnPath = isSafeReturnUrl(returnParam)
    ? returnParam
    : isSafeReturnUrl(params.get("returnUrl"))
      ? params.get("returnUrl")!
      : null;

  useEffect(() => {
    if (returnPath) writeReturnUrl(returnPath);
  }, [returnPath]);

  useEffect(() => {
    document.title = "Entrar no QMind";
  }, []);

  if (auth.status === "loading") {
    return (
      <div className="mx-auto max-w-5xl px-4 py-16">
        <LoadingPanel title="Validando sua sessão…" />
      </div>
    );
  }

  if (auth.status === "authenticated") {
    const dest = consumeReturnUrl(returnPath ?? "/assessments");
    return <Navigate to={dest} replace />;
  }

  const status =
    auth.status === "invalid_session" ? "invalid_session" : "anonymous";

  return (
    <div data-testid="login-page">
      <div className="absolute left-4 top-4 z-10">
        <Link
          to="/"
          className="text-sm font-medium text-[var(--qm-muted)] underline-offset-4 hover:text-[var(--qm-ink)] hover:underline"
        >
          Voltar à apresentação
        </Link>
      </div>
      <AccessGate
        status={status}
        onLogin={() => {
          writeReturnUrl(returnPath ?? "/assessments");
          void auth.login();
          // AUTH_MODE=dev: status autenticado dispara Navigate abaixo.
          // Cognito: redirect externo; retorno via /auth/callback.
        }}
      />
    </div>
  );
}
