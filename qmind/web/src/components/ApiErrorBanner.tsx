import { QmindApiError } from "@/api/qmindApi";

type Props = {
  title?: string;
  error: unknown;
  onRetry?: () => void;
};

/** Standardized ErrorBody presentation (code, message, correlation_id, field_errors). */
export function ApiErrorBanner({ title = "Erro", error, onRetry }: Props) {
  if (!error) return null;

  if (error instanceof QmindApiError) {
    return (
      <div
        className="rounded-lg border border-rose-300/60 bg-rose-50/90 px-4 py-3"
        role="alert"
        data-testid="api-error"
      >
        <p className="font-semibold text-rose-950">{title}</p>
        <p className="mt-1 text-sm text-rose-900/90">{error.message}</p>
        <dl className="mt-2 space-y-0.5 font-mono text-xs text-rose-900/70">
          <div>
            <dt className="inline">code: </dt>
            <dd className="inline" data-testid="api-error-code">
              {error.code}
            </dd>
          </div>
          <div>
            <dt className="inline">status: </dt>
            <dd className="inline">{error.status}</dd>
          </div>
          {error.correlationId ? (
            <div>
              <dt className="inline">correlation_id: </dt>
              <dd className="inline" data-testid="api-error-correlation">
                {error.correlationId}
              </dd>
            </div>
          ) : null}
        </dl>
        {error.fieldErrors.length > 0 ? (
          <ul className="mt-2 list-inside list-disc text-xs text-rose-900/80">
            {error.fieldErrors.map((f) => (
              <li key={`${f.field}-${f.code}`}>
                {f.field}: {f.message}
              </li>
            ))}
          </ul>
        ) : null}
        {onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="mt-3 rounded-md bg-rose-900 px-3 py-1.5 text-sm font-semibold text-white"
          >
            Recarregar
          </button>
        ) : null}
      </div>
    );
  }

  const message = error instanceof Error ? error.message : "Erro desconhecido";
  return (
    <div
      className="rounded-lg border border-rose-300/60 bg-rose-50/90 px-4 py-3"
      role="alert"
      data-testid="api-error"
    >
      <p className="font-semibold text-rose-950">{title}</p>
      <p className="mt-1 text-sm text-rose-900/90">{message}</p>
    </div>
  );
}
