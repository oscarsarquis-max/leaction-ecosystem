import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  useImprovementCase,
  usePatchImprovementCase,
} from "@/hooks/useImprovementCases";
import { canManageImprovementCases } from "@/lib/permissions";
import {
  allowedImprovementCaseTransitions,
  labelImprovementCaseStatus,
} from "@/lib/improvementCaseLabels";
import { AccessDeniedPanel, LoadingPanel } from "@/components/StatePanels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { PageHeader } from "@/components/qm";
import { QmindApiError } from "@/api/qmindApi";

function formatUpdatedAt(iso: string): string {
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function ImprovementCaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const org = useOrganization();
  const canWrite = canManageImprovementCases(org.currentOrganization?.roles);
  const query = useImprovementCase(caseId);
  const patch = usePatchImprovementCase(caseId);

  const [editing, setEditing] = useState(false);
  const [problem, setProblem] = useState("");
  const [impact, setImpact] = useState("");
  const [processName, setProcessName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const data = query.data;

  useEffect(() => {
    if (!data) return;
    setProblem(data.problem_statement);
    setImpact(data.impact_statement);
    setProcessName(data.related_process);
  }, [data]);

  const nextStatuses = useMemo(
    () => (data ? allowedImprovementCaseTransitions(data.status) : []),
    [data],
  );

  if (!org.currentOrganizationId) {
    return (
      <AccessDeniedPanel message="Selecione uma organização para ver o problema." />
    );
  }

  if (query.isLoading) {
    return <LoadingPanel title="Carregando problema…" />;
  }

  if (query.isError) {
    return (
      <ApiErrorBanner
        title="Não foi possível carregar o problema"
        error={query.error}
        onRetry={() => void query.refetch()}
      />
    );
  }

  if (!data) {
    return (
      <AccessDeniedPanel message="Problema não encontrado nesta organização." />
    );
  }

  async function saveFacts(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await patch.mutateAsync({
        problem_statement: problem,
        impact_statement: impact,
        related_process: processName,
      });
      setEditing(false);
    } catch (err) {
      setError(
        err instanceof QmindApiError
          ? err.message
          : "Não foi possível salvar as alterações.",
      );
    }
  }

  async function changeStatus(next: string) {
    setError(null);
    try {
      await patch.mutateAsync({
        status: next as
          | "open"
          | "analyzing"
          | "acting"
          | "reviewing"
          | "closed",
      });
    } catch (err) {
      setError(
        err instanceof QmindApiError
          ? err.message
          : "Transição de status não permitida.",
      );
    }
  }

  return (
    <section className="space-y-6" data-testid="improvement-case-detail">
      <PageHeader
        title={data.problem_statement}
        explanation={`Status: ${labelImprovementCaseStatus(data.status)}. Processo: ${data.related_process}. Atualizado em ${formatUpdatedAt(data.updated_at)}.`}
        expectedResult="Fatos do problema claros e prontos para a próxima etapa de inteligência."
        nextStep="Manter o acompanhamento ou aguardar a análise do QMind."
        actions={
          <Link to="/assessments" className="qm-btn-secondary">
            Voltar
          </Link>
        }
      />

      <div className="qm-panel space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-base font-semibold text-slate-900">
            Problema e impacto
          </h2>
          {canWrite ? (
            <button
              type="button"
              className="qm-btn-secondary"
              data-testid="ic-edit-toggle"
              onClick={() => {
                setEditing((v) => !v);
                setError(null);
              }}
            >
              {editing ? "Cancelar edição" : "Editar"}
            </button>
          ) : null}
        </div>

        {editing && canWrite ? (
          <form className="space-y-3" onSubmit={(e) => void saveFacts(e)}>
            <label className="block text-sm">
              <span className="font-medium">Problema</span>
              <textarea
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
                rows={3}
                required
                value={problem}
                onChange={(e) => setProblem(e.target.value)}
                data-testid="ic-detail-problem"
              />
            </label>
            <label className="block text-sm">
              <span className="font-medium">Impacto</span>
              <textarea
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
                rows={2}
                required
                value={impact}
                onChange={(e) => setImpact(e.target.value)}
                data-testid="ic-detail-impact"
              />
            </label>
            <label className="block text-sm">
              <span className="font-medium">Processo</span>
              <input
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
                required
                value={processName}
                onChange={(e) => setProcessName(e.target.value)}
                data-testid="ic-detail-process"
              />
            </label>
            <button
              type="submit"
              className="qm-btn-primary"
              disabled={patch.isPending}
              data-testid="ic-detail-save"
            >
              Salvar
            </button>
          </form>
        ) : (
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="font-medium text-slate-700">Problema</dt>
              <dd className="text-slate-900">{data.problem_statement}</dd>
            </div>
            <div>
              <dt className="font-medium text-slate-700">Impacto</dt>
              <dd className="text-slate-900">{data.impact_statement}</dd>
            </div>
            <div>
              <dt className="font-medium text-slate-700">Processo</dt>
              <dd className="text-slate-900">{data.related_process}</dd>
            </div>
            <div>
              <dt className="font-medium text-slate-700">Status</dt>
              <dd data-testid="ic-detail-status">
                {labelImprovementCaseStatus(data.status)}
              </dd>
            </div>
          </dl>
        )}

        {canWrite && nextStatuses.length > 0 ? (
          <div className="flex flex-wrap gap-2 pt-2">
            {nextStatuses.map((s) => (
              <button
                key={s}
                type="button"
                className="qm-btn-secondary"
                data-testid={`ic-status-${s}`}
                disabled={patch.isPending}
                onClick={() => void changeStatus(s)}
              >
                Ir para {labelImprovementCaseStatus(s)}
              </button>
            ))}
          </div>
        ) : null}

        {error ? (
          <p className="text-sm text-red-700" role="alert">
            {error}
          </p>
        ) : null}
      </div>

      <div className="qm-panel qm-panel--soft" data-testid="ic-section-context">
        <h2 className="text-base font-semibold text-slate-900">Contexto</h2>
        <p className="mt-2 text-sm text-slate-600">
          A análise de contexto deste problema será disponibilizada na próxima
          etapa da ISO Intelligence.
        </p>
      </div>

      <div className="qm-panel qm-panel--soft" data-testid="ic-section-analysis">
        <h2 className="text-base font-semibold text-slate-900">
          Análise do QMind
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Nenhuma análise foi gerada para este problema.
        </p>
      </div>

      <div className="qm-panel qm-panel--soft" data-testid="ic-section-actions">
        <h2 className="text-base font-semibold text-slate-900">Ações</h2>
        <p className="mt-2 text-sm text-slate-600">
          As ações relacionadas ao problema serão disponibilizadas após a
          primeira análise.
        </p>
      </div>

      <div
        className="qm-panel qm-panel--soft"
        data-testid="ic-section-evolution"
      >
        <h2 className="text-base font-semibold text-slate-900">Evolução</h2>
        <p className="mt-2 text-sm text-slate-600">
          A evolução será exibida após existirem análises e ações.
        </p>
      </div>
    </section>
  );
}
