import { Link } from "react-router-dom";
import { useAssessments } from "@/hooks/useAssessments";
import { useOrganization } from "@/org/OrganizationProvider";
import { useAssessmentPermissions } from "@/hooks/useAssessmentPermissions";
import {
  AccessDeniedPanel,
  EmptyPanel,
  LoadingPanel,
} from "@/components/StatePanels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { QmindApiError } from "@/api/qmindApi";

export function AssessmentsPage() {
  const org = useOrganization();
  const perms = useAssessmentPermissions();
  const query = useAssessments();

  if (!org.currentOrganizationId) {
    return (
      <EmptyPanel
        title="Selecione uma organização"
        message="Escolha uma organização ativa no cabeçalho para ver as avaliações."
      />
    );
  }

  if (query.isLoading) {
    return <LoadingPanel title="Carregando avaliações…" />;
  }

  if (query.isError) {
    const err = query.error;
    if (err instanceof QmindApiError && (err.status === 401 || err.status === 403)) {
      return <AccessDeniedPanel message={err.message} />;
    }
    return (
      <ApiErrorBanner
        title="Erro ao carregar avaliações"
        error={err}
        onRetry={() => void query.refetch()}
      />
    );
  }

  const items = query.data ?? [];

  return (
    <section>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl tracking-tight text-teal-950">
            Avaliações
          </h1>
          <p className="mt-1 text-sm text-teal-950/70">
            {org.currentOrganization?.organizationName ?? org.currentOrganizationId}
          </p>
        </div>
        {perms.canMutate ? (
          <Link
            to="/assessments/new"
            className="rounded-md bg-teal-900 px-3 py-2 text-sm font-semibold text-white"
            data-testid="new-assessment"
          >
            Nova avaliação
          </Link>
        ) : null}
      </header>

      {items.length === 0 ? (
        <EmptyPanel
          title="Nenhuma avaliação"
          message="Esta organização ainda não possui avaliações."
        />
      ) : (
        <ul
          className="divide-y divide-teal-900/10 rounded-lg border border-teal-900/10 bg-white/70"
          data-testid="assessments-list"
        >
          {items.map((a) => (
            <li key={a.id}>
              <Link
                to={`/assessments/${a.id}`}
                className="flex flex-wrap items-baseline justify-between gap-2 px-4 py-3 hover:bg-teal-50/60"
              >
                <div>
                  <p className="font-semibold text-teal-950">{a.type}</p>
                  <p className="font-mono text-xs text-teal-950/50">{a.id}</p>
                </div>
                <span className="rounded-md bg-teal-900/10 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-teal-900">
                  {a.status}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
