import type { ReactNode } from "react";
import { Link } from "react-router-dom";

type Action =
  | { label: string; onClick: () => void }
  | { label: string; to: string };

type Props = {
  title: string;
  message?: string;
  example?: string;
  action?: Action;
  children?: ReactNode;
};

export function LoadingPanel({ title = "Carregando…" }: { title?: string }) {
  return (
    <div
      className="qm-panel qm-panel--soft flex min-h-[12rem] items-center justify-center px-6 py-10"
      role="status"
      aria-live="polite"
    >
      <p className="text-sm font-semibold text-[var(--qm-muted)]">{title}</p>
    </div>
  );
}

export function EmptyPanel({ title, message, example, action }: Props) {
  return (
    <div className="qm-panel qm-panel--dashed px-6 py-10 text-center">
      <h2 className="font-display text-xl text-[var(--qm-ink)]">{title}</h2>
      {message ? (
        <p className="mx-auto mt-2 max-w-md text-sm text-[var(--qm-muted)]">
          {message}
        </p>
      ) : null}
      {example ? (
        <p className="mx-auto mt-3 max-w-md text-sm text-[var(--qm-muted)]">
          <span className="font-semibold text-[var(--qm-ink)]">Exemplo: </span>
          {example}
        </p>
      ) : null}
      {action ? <ActionButton action={action} /> : null}
    </div>
  );
}

export function ErrorPanel({ title, message, action }: Props) {
  return (
    <div className="qm-panel qm-panel--danger px-6 py-8" role="alert">
      <h2 className="font-display text-xl text-[var(--qm-ink)]">{title}</h2>
      {message ? (
        <p className="mt-2 text-sm text-[var(--qm-muted)]">{message}</p>
      ) : null}
      {action ? <ActionButton action={action} /> : null}
    </div>
  );
}

function friendlyAccessMessage(message?: string): string {
  if (!message) {
    return "Sua conta não pode ver este conteúdo nesta organização. Peça acesso a quem administra a organização ou troque de organização no topo da página.";
  }
  const technical = /\b(403|401|forbidden|unauthorized|STATUS_)\b/i.test(message);
  if (technical) {
    return "Você não tem permissão para acessar este conteúdo nesta organização.";
  }
  return message;
}

export function AccessDeniedPanel({ message }: { message?: string }) {
  return (
    <div className="qm-panel qm-panel--warn px-6 py-8" role="alert">
      <h2 className="font-display text-xl text-[var(--qm-ink)]">Sem permissão aqui</h2>
      <p className="mt-2 text-sm text-[var(--qm-muted)]">{friendlyAccessMessage(message)}</p>
      <p className="mt-3 text-sm text-[var(--qm-muted)]">
        Próxima etapa: escolha outra organização no seletor do cabeçalho, ou fale com o administrador.
      </p>
    </div>
  );
}

function ActionButton({ action }: { action: Action }) {
  if ("to" in action) {
    return (
      <Link to={action.to} className="qm-btn-primary mt-5 inline-flex">
        {action.label}
      </Link>
    );
  }
  return (
    <button type="button" onClick={action.onClick} className="qm-btn-primary mt-5">
      {action.label}
    </button>
  );
}
