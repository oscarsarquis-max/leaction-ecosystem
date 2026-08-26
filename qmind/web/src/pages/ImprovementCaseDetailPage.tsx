import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  useImprovementCase,
  usePatchImprovementCase,
} from "@/hooks/useImprovementCases";
import {
  useCreateImprovementCaseAnalysisRun,
  useImprovementCaseAnalysisRuns,
} from "@/hooks/useImprovementCaseAnalysis";
import { useOrgProfile } from "@/hooks/useOrgProfile";
import {
  canManageImprovementCases,
  canRunExecutionIntelligence,
} from "@/lib/permissions";
import {
  FindingActionControls,
  ImprovementCaseActionsSection,
} from "@/components/ImprovementCaseActions";
import { ImprovementCaseEvolutionSection } from "@/components/ImprovementCaseEvolution";
import {
  allowedImprovementCaseTransitions,
  labelHypothesisSupportStatus,
  labelImprovementCaseStatus,
  labelProblemContextStatus,
} from "@/lib/improvementCaseLabels";
import { AccessDeniedPanel, LoadingPanel } from "@/components/StatePanels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { PageHeader } from "@/components/qm";
import { QmindApiError } from "@/api/qmindApi";
import type { ImprovementCaseAnalysisRunOut } from "@qmind/api-client";

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
  const canAnalyzeExecution = canRunExecutionIntelligence(
    org.currentOrganization?.roles,
  );
  const query = useImprovementCase(caseId);
  const patch = usePatchImprovementCase(caseId);
  const profile = useOrgProfile();
  const runsQuery = useImprovementCaseAnalysisRuns(caseId);
  const createRun = useCreateImprovementCaseAnalysisRun(caseId);

  const [editing, setEditing] = useState(false);
  const [problem, setProblem] = useState("");
  const [impact, setImpact] = useState("");
  const [processName, setProcessName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isoOpen, setIsoOpen] = useState(false);
  const [viewRunId, setViewRunId] = useState<string | null>(null);
  const [highlightFinding, setHighlightFinding] = useState<string | null>(null);

  const data = query.data;
  const runs = runsQuery.data ?? [];
  const latest = runs[0] ?? null;
  const viewed: ImprovementCaseAnalysisRunOut | null =
    (viewRunId ? runs.find((r) => r.id === viewRunId) : null) ?? latest;

  useEffect(() => {
    if (!data) return;
    setProblem(data.problem_statement);
    setImpact(data.impact_statement);
    setProcessName(data.related_process);
  }, [data]);

  useEffect(() => {
    setViewRunId(null);
  }, [org.currentOrganizationId, caseId]);

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

  async function generateAnalysis() {
    setError(null);
    try {
      const run = await createRun.mutateAsync();
      setViewRunId(run.id);
    } catch (err) {
      setError(
        err instanceof QmindApiError
          ? err.message
          : "Não foi possível gerar a análise.",
      );
    }
  }

  const analysis = viewed?.analysis;
  const hypotheses = analysis?.hypotheses ?? [];
  const findings = analysis?.findings ?? [];
  const limitations = analysis?.limitations ?? [];
  const isViewingLatest = !viewed || viewed.id === latest?.id;

  return (
    <section className="space-y-6" data-testid="improvement-case-detail">
      <PageHeader
        title={data.problem_statement}
        explanation={`Status: ${labelImprovementCaseStatus(data.status)}. Processo: ${data.related_process}. Atualizado em ${formatUpdatedAt(data.updated_at)}.`}
        expectedResult="Fatos do problema claros e prontos para a próxima etapa de inteligência."
        nextStep="Manter o acompanhamento ou gerar a análise do QMind."
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

      <div className="qm-panel" data-testid="ic-section-context">
        <h2 className="text-base font-semibold text-slate-900">Contexto</h2>
        <dl className="mt-3 space-y-2 text-sm">
          <div>
            <dt className="font-medium text-slate-700">Problema</dt>
            <dd>{data.problem_statement}</dd>
          </div>
          <div>
            <dt className="font-medium text-slate-700">Impacto</dt>
            <dd>{data.impact_statement}</dd>
          </div>
          <div>
            <dt className="font-medium text-slate-700">Processo relacionado</dt>
            <dd>{data.related_process}</dd>
          </div>
          <div data-testid="ic-context-org-summary">
            <dt className="font-medium text-slate-700">
              Resumo organizacional
            </dt>
            <dd>
              {[
                profile.data?.trade_name,
                profile.data?.industry,
                profile.data?.business_model,
              ]
                .filter(Boolean)
                .join(" · ") || "Perfil organizacional ainda incompleto."}
            </dd>
          </div>
          {latest ? (
            <div>
              <dt className="font-medium text-slate-700">
                Status de contexto (análise mais recente)
              </dt>
              <dd data-testid="ic-context-status">
                {labelProblemContextStatus(latest.analysis.context_status)}
              </dd>
            </div>
          ) : (
            <p className="text-slate-600" data-testid="ic-context-no-analysis">
              Ainda não há análise para avaliar o contexto deste problema.
            </p>
          )}
        </dl>
        {latest?.analysis.hypotheses?.[0]?.missing_information?.length ? (
          <ul
            className="mt-3 list-disc pl-5 text-sm text-slate-600"
            data-testid="ic-context-missing"
          >
            {latest.analysis.hypotheses[0].missing_information.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        ) : null}
      </div>

      <div className="qm-panel space-y-3" data-testid="ic-section-analysis">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-base font-semibold text-slate-900">
            Análise do QMind
          </h2>
          {canWrite ? (
            <button
              type="button"
              className="qm-btn-primary"
              data-testid="ic-generate-analysis"
              disabled={createRun.isPending}
              onClick={() => void generateAnalysis()}
            >
              {createRun.isPending
                ? "Gerando…"
                : latest
                  ? "Atualizar análise"
                  : "Gerar análise"}
            </button>
          ) : null}
        </div>

        {createRun.isPending ? (
          <p data-testid="ic-analysis-loading">Gerando análise…</p>
        ) : null}

        {latest?.is_stale && isViewingLatest ? (
          <div
            className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-950"
            data-testid="ic-analysis-stale"
          >
            <p>
              O problema ou seu contexto foi atualizado. Gere uma nova análise
              para considerar as informações atuais.
            </p>
            {canWrite ? (
              <button
                type="button"
                className="qm-btn-secondary mt-2"
                data-testid="ic-refresh-analysis"
                disabled={createRun.isPending}
                onClick={() => void generateAnalysis()}
              >
                Atualizar análise
              </button>
            ) : null}
          </div>
        ) : null}

        {!analysis ? (
          <p
            className="text-sm text-slate-600"
            data-testid="ic-analysis-empty"
          >
            Nenhuma análise foi gerada para este problema.
          </p>
        ) : (
          <div className="space-y-4 text-sm" data-testid="ic-analysis-content">
            <p className="text-xs text-slate-500">
              {formatUpdatedAt(viewed!.generated_at)}
              {!isViewingLatest ? " · snapshot histórico" : null}
            </p>
            <div>
              <h3 className="font-medium text-slate-800">Interpretação</h3>
              <p data-testid="ic-interpretation">
                {analysis.interpretation_summary}
              </p>
            </div>

            {hypotheses.map((h) => (
              <div key={h.code} data-testid={`ic-hypothesis-${h.code}`}>
                <h3 className="font-medium text-slate-800">Hipótese</h3>
                <p>{h.statement}</p>
                <p className="mt-1 text-slate-600">
                  Sustentação: {labelHypothesisSupportStatus(h.support_status)}
                </p>
              </div>
            ))}

            {findings.map((f) => (
              <div
                key={f.code}
                id={`ic-finding-anchor-${f.code}`}
                data-testid={`ic-finding-${f.code}`}
                className={
                  highlightFinding === f.code
                    ? "rounded ring-2 ring-slate-400 p-2"
                    : undefined
                }
              >
                <h3 className="font-medium text-slate-800">{f.title}</h3>
                <p>{f.description}</p>
                <p className="mt-1 text-slate-600">
                  Relação com o problema: {f.relationship_to_problem}
                </p>
                <p className="text-slate-600">
                  Impacto empresarial: {f.business_impact}
                </p>
                <p className="mt-1" data-testid="ic-recommended-next-step">
                  Próximo passo: {f.recommended_next_step}
                </p>
                {caseId && viewed ? (
                  <FindingActionControls
                    caseId={caseId}
                    run={viewed}
                    finding={f}
                  />
                ) : null}
              </div>
            ))}

            {limitations.length > 0 ? (
              <div data-testid="ic-limitations">
                <h3 className="font-medium text-slate-800">Limitações</h3>
                <ul className="list-disc pl-5 text-slate-600">
                  {limitations.map((lim) => (
                    <li key={lim}>{lim}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div data-testid="ic-iso-basis">
              <button
                type="button"
                className="text-sm font-medium text-slate-800 underline"
                data-testid="ic-iso-toggle"
                onClick={() => setIsoOpen((v) => !v)}
              >
                Fundamentação ISO {isoOpen ? "(ocultar)" : "(mostrar)"}
              </button>
              {isoOpen ? (
                <div className="mt-2 space-y-2 text-slate-600">
                  <p data-testid="ic-iso-disclaimer">
                    Esta análise utiliza a ISO 9001 como estrutura de
                    interpretação. Não representa auditoria, conformidade ou
                    garantia de certificação.
                  </p>
                  <p>
                    Bases:{" "}
                    {[
                      ...new Set(
                        [
                          ...hypotheses.flatMap((h) => h.iso_basis ?? []),
                          ...findings.flatMap((f) => f.iso_basis ?? []),
                        ].map(String),
                      ),
                    ].join(", ") || "—"}
                  </p>
                </div>
              ) : null}
            </div>
          </div>
        )}
      </div>

      <div className="qm-panel" data-testid="ic-section-history">
        <h2 className="text-base font-semibold text-slate-900">Histórico</h2>
        {runs.length === 0 ? (
          <p className="mt-2 text-sm text-slate-600">
            Nenhuma análise registrada ainda.
          </p>
        ) : (
          <ul className="mt-3 space-y-2 text-sm">
            {runs.map((run, idx) => (
              <li
                key={run.id}
                className="flex flex-wrap items-center justify-between gap-2"
                data-testid={`ic-history-${run.id}`}
              >
                <span>
                  {formatUpdatedAt(run.generated_at)} ·{" "}
                  {labelProblemContextStatus(run.analysis.context_status)}
                  {idx === 0
                    ? run.is_stale
                      ? " · desatualizada"
                      : " · atual"
                    : " · histórica"}
                </span>
                <button
                  type="button"
                  className="qm-btn-secondary"
                  onClick={() => setViewRunId(run.id)}
                >
                  Ver snapshot
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {caseId ? (
        <ImprovementCaseActionsSection
          caseId={caseId}
          runs={runs}
          onOpenRunFinding={(runId, findingCode) => {
            setViewRunId(runId);
            setHighlightFinding(findingCode);
            window.setTimeout(() => {
              document
                .getElementById(`ic-finding-anchor-${findingCode}`)
                ?.scrollIntoView({ behavior: "smooth", block: "center" });
            }, 50);
          }}
        />
      ) : null}

      {caseId ? (
        <ImprovementCaseEvolutionSection
          caseId={caseId}
          canWrite={canWrite}
          canAnalyzeExecution={canAnalyzeExecution}
        />
      ) : null}
    </section>
  );
}
