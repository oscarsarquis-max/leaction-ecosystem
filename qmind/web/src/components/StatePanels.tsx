type Props = {
  title: string;
  message?: string;
  action?: { label: string; onClick: () => void };
};

export function LoadingPanel({ title = "Carregando…" }: { title?: string }) {
  return (
    <div
      className="flex min-h-[12rem] items-center justify-center rounded-lg border border-teal-900/10 bg-white/60 px-6 py-10"
      role="status"
      aria-live="polite"
    >
      <p className="text-sm font-semibold text-teal-950/70">{title}</p>
    </div>
  );
}

export function EmptyPanel({ title, message }: Props) {
  return (
    <div className="rounded-lg border border-dashed border-teal-900/20 bg-white/40 px-6 py-10 text-center">
      <h2 className="font-display text-xl text-teal-950">{title}</h2>
      {message ? <p className="mt-2 text-sm text-teal-950/70">{message}</p> : null}
    </div>
  );
}

export function ErrorPanel({ title, message, action }: Props) {
  return (
    <div
      className="rounded-lg border border-rose-300/60 bg-rose-50/80 px-6 py-8"
      role="alert"
    >
      <h2 className="font-display text-xl text-rose-950">{title}</h2>
      {message ? <p className="mt-2 text-sm text-rose-900/80">{message}</p> : null}
      {action ? (
        <button
          type="button"
          onClick={action.onClick}
          className="mt-4 rounded-md bg-rose-900 px-3 py-1.5 text-sm font-semibold text-white"
        >
          {action.label}
        </button>
      ) : null}
    </div>
  );
}

export function AccessDeniedPanel({ message }: { message?: string }) {
  return (
    <div
      className="rounded-lg border border-amber-300/70 bg-amber-50/90 px-6 py-8"
      role="alert"
    >
      <h2 className="font-display text-xl text-amber-950">Acesso negado</h2>
      <p className="mt-2 text-sm text-amber-950/80">
        {message ?? "Você não tem permissão para este contexto."}
      </p>
    </div>
  );
}
