import type { ReactNode } from "react";
import { ApiError } from "../api/errors";

export function LoadingState({ children = "Carregando…" }: { children?: ReactNode }) {
  return (
    <p className="feedback" role="status">
      {children}
    </p>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <p className="feedback" role="status">
      {children}
    </p>
  );
}

export function ErrorState({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  const api = error instanceof ApiError ? error : null;
  const title =
    api?.code === "nao_autenticado"
      ? "Sessão expirada"
      : api?.code === "nao_autorizado"
        ? "Acesso negado"
        : api?.code === "indisponivel"
          ? "API indisponível"
          : api?.code === "conflito"
            ? "Conflito de estado"
            : "Não foi possível carregar";
  const message = api?.message ?? (error instanceof Error ? error.message : "Erro inesperado.");
  return (
    <div className="feedback" role="alert">
      <h2>{title}</h2>
      <p>{message}</p>
      {onRetry ? (
        <button type="button" className="primary" onClick={onRetry}>
          Tentar de novo
        </button>
      ) : null}
    </div>
  );
}

export function StatusBadge({
  tone,
  label,
}: {
  tone: "sucesso" | "atencao" | "erro" | "info" | "neutro";
  label: string;
}) {
  return <span className={`badge badge-${tone}`}>{label}</span>;
}
