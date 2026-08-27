import { useEffect, type ReactNode } from "react";
import { ApiError, isCancelledError } from "../api/errors";
import { useAssistantOptional } from "../assistant/AssistantContext";
import type { LiveOverlay, PageKind } from "../assistant/liveContext";

function usePublishKind(kind: PageKind, overlay: LiveOverlay = {}) {
  const assistant = useAssistantOptional();
  const publish = assistant?.publishLive;
  useEffect(() => {
    publish?.({ pageKind: kind, ...overlay });
    return () => {
      if (kind === "loading") {
        publish?.({ pageKind: "ok" });
      }
    };
  }, [publish, kind, overlay.entityLabel, overlay.status, overlay.pending, overlay.blocked, overlay.next]);
}

export function ListLive({
  kind,
  empty,
  entityLabel,
  status,
  next,
}: {
  kind: string;
  empty?: boolean;
  entityLabel?: string;
  status?: string;
  next?: string;
}) {
  const pageKind: PageKind =
    kind === "carregando" ? "loading" : kind === "erro" ? "error" : empty ? "empty" : "ok";
  usePublishKind(pageKind, { entityLabel, status, next });
  return null;
}

export function LoadingState({ children = "Carregando…" }: { children?: ReactNode }) {
  usePublishKind("loading", { status: "carregando", next: "Aguardar o recorte." });
  return (
    <p className="feedback" role="status">
      {children}
    </p>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  usePublishKind("empty", { status: "vazio", next: "Criar, limpar filtro ou trocar contexto." });
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
  // Cinto de segurança: cancelamento nunca deve ser tela de erro persistente.
  if (isCancelledError(error)) {
    return <LoadingState>Carregando…</LoadingState>;
  }
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
  const denied = api?.code === "nao_autorizado";
  usePublishKind(denied ? "denied" : "error", {
    status: denied ? "acesso negado" : "erro",
    blocked: title,
    next: denied ? "Trocar de perfil ou voltar." : "Tentar de novo.",
  });
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
