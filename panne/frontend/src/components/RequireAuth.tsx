import { Navigate, useLocation } from "react-router-dom";
import { ApiError } from "../api/errors";
import { useAuth } from "../auth/AuthContext";
import { useOrganization } from "../session/OrganizationContext";
import { ErrorState, LoadingState } from "./Feedback";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { session } = useAuth();
  const location = useLocation();
  if (!session) {
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
  if (associations.length === 0) {
    return <ErrorState error={new Error("Nenhuma associação ativa encontrada.")} />;
  }
  if (!active && associations.length > 1) {
    return <Navigate to="/organizacao" replace />;
  }
  return children;
}

export function RequirePermission({
  code,
  children,
}: {
  code: string;
  children: React.ReactNode;
}) {
  const { hasPermission, active } = useOrganization();
  if (!active) return <Navigate to="/organizacao" replace />;
  if (!hasPermission(code)) {
    return (
      <ErrorState error={new ApiError("nao_autorizado", "Você não tem permissão para este recurso.", 403)} />
    );
  }
  return children;
}
