import { Navigate, useLocation } from "react-router-dom";
import { ApiError } from "../api/errors";
import { useAuth } from "../auth/AuthContext";
import { FirstAccess } from "./FirstAccess";
import { useOrganization } from "../session/OrganizationContext";
import { ErrorState, LoadingState } from "./Feedback";

const RETURN_KEY = "panne.returnTo";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { session } = useAuth();
  const location = useLocation();
  if (!session) {
    if (location.pathname !== "/entrar" && location.pathname !== "/callback") {
      try {
        sessionStorage.setItem(RETURN_KEY, location.pathname);
      } catch {
        /* o retorno é conveniência; a entrada continua */
      }
    }
    return <Navigate to="/entrar" replace state={{ from: location.pathname }} />;
  }
  return children;
}

export function RequireOrganization({ children }: { children: React.ReactNode }) {
  const { status, associations, active } = useOrganization();
  if (status.kind === "carregando") return <LoadingState>Carregando perfil…</LoadingState>;
  if (status.kind === "erro") {
    if (status.error instanceof ApiError && status.error.code === "nao_autenticado") {
      return <Navigate to="/entrar" replace />;
    }
    return <ErrorState error={status.error} />;
  }
  const access = status.kind === "pronto" ? status.me.access_state : undefined;
  if (access === "autorizado" || access === "convidado" || access === "sem_autorizacao" || associations.length === 0) {
    return <FirstAccess />;
  }
  if (!active && associations.length > 1) {
    return <Navigate to="/organizacao" replace />;
  }
  return children;
}

export function RequirePermission({
  code,
  anyOf,
  children,
}: {
  code?: string;
  /** Basta uma das permissões; usado onde um domínio novo ainda convive com o código antigo. */
  anyOf?: string[];
  children: React.ReactNode;
}) {
  const { hasPermission, active } = useOrganization();
  const codes = anyOf ?? (code ? [code] : []);
  if (!active) return <Navigate to="/organizacao" replace />;
  if (!codes.some((item) => hasPermission(item))) {
    return (
      <ErrorState error={new ApiError("nao_autorizado", "Você não tem permissão para este recurso.", 403)} />
    );
  }
  return children;
}
