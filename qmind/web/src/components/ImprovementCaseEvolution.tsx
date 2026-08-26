import { useRef, useState } from "react";
import {
  useCreateExecutionIntelligenceRun,
  useCreateOutcomeObservation,
  useExecutionIntelligenceRuns,
  useImprovementCaseEvolution,
} from "@/hooks/useImprovementCaseEvolution";
import type {
  ExecutionIntelligenceRunOut,
  ExecutionSignal,
} from "@qmind/api-client";
import { usePatchImprovementCase } from "@/hooks/useImprovementCases";
import {
  labelClosureReadiness,
  labelImprovementCaseStatus,
  labelProblemContextStatus,
  labelResultDirection,
  RESULT_DIRECTION_OPTIONS,
} from "@/lib/improvementCaseLabels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { LoadingPanel } from "@/components/StatePanels";
import { MeasurementSummaryPanel } from "@/execution/MeasurementSummaryPanel";
import { QmindApiError } from "@/api/qmindApi";

type ResultDirection =
  | "improved"
  | "unchanged"
  | "worsened"
  | "not_yet_measured";

function formatWhen(iso: string): string {
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function CodeList({
  items,
  empty,
}: {
  items: string[];
  empty: string;
}) {
  if (items.length === 0) {
    return <p className="text-slate-500">{empty}</p>;
  }
  return (
    <ul className="list-disc pl-5">
      {items.map((c) => (
        <li key={c}>{c}</li>
      ))}
    </ul>
  );
}

type Props = {
  caseId: string;
  canWrite: boolean;
  canAnalyzeExecution: boolean;
};

function executionPostureLabel(value: string): string {
  return (
    {
      insufficient_information: "Informações insuficientes",
      not_started: "Execução ainda não iniciada",
      progressing: "Execução em andamento",
      attention_required: "Execução requer atenção",
      stalled: "Execução sem avanço recente",
      awaiting_result_evaluation: "Aguardando avaliação do resultado",
      result_observed: "Resultado observado",
    }[value] ?? "Interpretação disponível"
  );
}

const SIGNAL_CATEGORY_LABELS: Record<string, string> = {
  flow: "Fluxo da execução",
  schedule: "Prazos",
  blocker: "Impedimentos",
  dependency: "Dependências",
  evidence: "Evidências",
  measurement: "Medição",
  outcome: "Resultado",
};

const SIGNAL_LEVEL_LABELS: Record<string, string> = {
  information: "Informação",
  watch: "Acompanhar",
  attention: "Requer atenção",
};

const FACT_FIELD_LABELS: Record<string, string> = {
  status: "situação atual",
  owner_assigned: "responsabilidade atribuída",
  due_at: "prazo",
  is_overdue: "prazo vencido",
  last_check_in_at: "última atualização",
  active_impediment_count: "impedimentos ativos",
  open_dependency_count: "dependências abertas",
  overdue_dependency_count: "dependências vencidas",
  approved_evidence_count: "evidências aprovadas",
  is_terminal: "encerramento da ação",
  claims_execution: "execução declarada",
  baseline_value: "valor de referência",
  baseline_status: "situação do valor de referência",
  latest_value: "último valor medido",
  measurement_posture: "situação da medição",
  is_measurement_overdue: "medição vencida",
  substantiation: "sustentação da leitura",
  target_posture: "situação da meta",
};

function factLabel(run: ExecutionIntelligenceRunOut, ref: string): string {
  if (ref === "case.status") return "Situação do caso";
  if (ref === "execution.plan.status") return "Situação do plano de ação";
  if (ref === "outcome.latest.result_direction") {
    return "Direção do resultado observado";
  }
  const action = /^execution\.action:(.+):([^:]+)$/.exec(ref);
  if (action) {
    const item = run.input_snapshot.execution.actions?.find(
      (candidate) => candidate.action_ref === action[1],
    );
    return `${item?.label ?? "Ação"} — ${FACT_FIELD_LABELS[action[2]] ?? "fato relacionado"}`;
  }
  const indicator = /^measurement\.indicator:(.+):([^:]+)$/.exec(ref);
  if (indicator) {
    const item = run.input_snapshot.measurement.indicators?.find(
      (candidate) => candidate.indicator_ref === indicator[1],
    );
    return `${item?.name ?? "Indicador"} — ${FACT_FIELD_LABELS[indicator[2]] ?? "fato relacionado"}`;
  }
  return "Fato relacionado à interpretação";
}

function mechanismLabel(value: string): string {
  return value === "execution-intelligence-rules-v1"
    ? "Regras determinísticas de inteligência da execução — versão 1"
    : "Mecanismo determinístico versionado";
}

export function ImprovementCaseEvolutionSection({
  caseId,
  canWrite,
  canAnalyzeExecution,
}: Props) {
  const query = useImprovementCaseEvolution(caseId);
  const executionQuery = useExecutionIntelligenceRuns(caseId);
  const retainedExecution = useRef(executionQuery.data);
  if (executionQuery.data) retainedExecution.current = executionQuery.data;
  const createObs = useCreateOutcomeObservation(caseId);
  const createExecutionIntelligence = useCreateExecutionIntelligenceRun(caseId);
  const patch = usePatchImprovementCase(caseId);

  const [formOpen, setFormOpen] = useState(false);
  const [direction, setDirection] = useState<ResultDirection>("improved");
  const [statement, setStatement] = useState("");
  const [basis, setBasis] = useState("");
  const [observedLocal, setObservedLocal] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmClose, setConfirmClose] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);

  if (query.isLoading) {
    return <LoadingPanel title="Carregando evolução…" />;
  }

  if (query.isError) {
    return (
      <ApiErrorBanner
        title="Não foi possível carregar a evolução"
        error={query.error}
        onRetry={() => void query.refetch()}
      />
    );
  }

  const evo = query.data;
  if (!evo) {
    return (
      <div className="qm-panel qm-panel--soft" data-testid="ic-section-evolution">
        <h2 className="text-base font-semibold text-slate-900">Evolução</h2>
        <p className="mt-2 text-sm text-slate-600">
          Evolução indisponível para este problema nesta organização.
        </p>
      </div>
    );
  }

  const latest = evo.analysis_summary.latest_run;
  const comparison = evo.analysis_summary.comparison;
  const actions = evo.action_summary;
  const byStatus = actions.by_status ?? [];
  const observations = evo.outcome_observations ?? [];
  const pending = Math.max(0, actions.total - actions.completed);
  const latestObs = evo.latest_outcome_observation;
  const ready = evo.closure_readiness === "ready_for_review";
  const caseStatus = evo.case.status;
  const executionIntelligence = evo.execution_intelligence;
  const executionData = executionQuery.data ?? retainedExecution.current;
  const fullExecution = executionData?.latest ?? null;
  const executionResult = fullExecution?.result;
  const signalGroups = (executionResult?.signals ?? []).reduce<
    Record<string, ExecutionSignal[]>
  >((groups, signal) => {
    (groups[signal.category] ??= []).push(signal);
    return groups;
  }, {});

  async function submitObservation(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!observedLocal) {
      setFormError("Informe quando a observação foi realizada.");
      return;
    }
    const observedAt = new Date(observedLocal);
    if (Number.isNaN(observedAt.getTime())) {
      setFormError("Data/hora inválida.");
      return;
    }
    try {
      await createObs.mutateAsync({
        result_direction: direction,
        observation_statement: statement,
        measurement_basis: basis,
        observed_at: observedAt.toISOString(),
      });
      setFormOpen(false);
      setStatement("");
      setBasis("");
      setObservedLocal("");
      setDirection("improved");
    } catch (err) {
      setFormError(
        err instanceof QmindApiError
          ? err.message
          : "Não foi possível registrar a observação.",
      );
    }
  }

  async function moveToReview() {
    setStatusError(null);
    try {
      await patch.mutateAsync({ status: "reviewing" });
    } catch (err) {
      setStatusError(
        err instanceof QmindApiError
          ? err.message
          : "Não foi possível colocar o caso em revisão.",
      );
    }
  }

  async function confirmCloseCase() {
    setStatusError(null);
    try {
      await patch.mutateAsync({ status: "closed" });
      setConfirmClose(false);
    } catch (err) {
      setStatusError(
        err instanceof QmindApiError
          ? err.message
          : "Não foi possível encerrar o caso.",
      );
    }
  }

  return (
    <div className="space-y-4" data-testid="ic-section-evolution">
      <div className="qm-panel space-y-3">
        <h2 className="text-base font-semibold text-slate-900">Evolução</h2>
        <p className="text-sm text-slate-600">
          Evolução da gestão (análises e ações) é distinta da evolução do
          resultado empresarial (observação declarada pela organização).
        </p>

        <div data-testid="ic-evo-situation" className="space-y-2 text-sm">
          <h3 className="font-medium text-slate-800">Situação do caso</h3>
          <ul className="space-y-1 text-slate-700">
            <li>Status: {labelImprovementCaseStatus(caseStatus)}</li>
            <li>
              Análise:{" "}
              {latest
                ? latest.is_stale
                  ? "desatualizada"
                  : "atual"
                : "nenhuma"}
            </li>
            <li>Total de análises: {evo.analysis_summary.total_runs}</li>
            <li>
              Ações: {actions.total} · concluídas {actions.completed} ·
              pendentes {pending}
              {actions.overdue > 0 ? ` · vencidas ${actions.overdue}` : ""}
            </li>
            <li>
              Observação mais recente:{" "}
              {latestObs
                ? labelResultDirection(latestObs.result_direction)
                : "nenhuma"}
            </li>
            <li data-testid="ic-evo-closure">
              {labelClosureReadiness(evo.closure_readiness)}
              {evo.closure_readiness_reason
                ? ` — ${evo.closure_readiness_reason}`
                : ""}
            </li>
          </ul>
          {latest?.is_stale ? (
            <p
              className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-amber-950"
              data-testid="ic-evo-stale"
            >
              A análise atual não considera as informações mais recentes do
              problema.
            </p>
          ) : null}
        </div>
      </div>

      {evo.measurement_summary ? (
        <div className="qm-panel space-y-3" data-testid="ic-evo-measurement">
          <h3 className="font-medium text-slate-800">Medição do resultado</h3>
          <p className="text-sm text-slate-600">
            O que os indicadores das ações deste problema dizem sobre a mudança —
            antes de qualquer declaração de eficácia.
          </p>
          <MeasurementSummaryPanel
            summary={evo.measurement_summary}
            testId="ic-evo-measurement-summary"
          />
        </div>
      ) : null}

      <div className="qm-panel space-y-3" data-testid="ic-evo-execution-intelligence">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-medium text-slate-800">Inteligência da execução</h3>
          <span className="rounded-full bg-violet-50 px-2 py-1 text-xs font-medium text-violet-800">
            Interpretação QMind OI
          </span>
        </div>
        {createExecutionIntelligence.isPending ? (
          <p className="text-sm text-slate-600" data-testid="ic-ei-analyzing">
            Analisando os fatos atuais da execução…
          </p>
        ) : fullExecution || executionIntelligence ? (
          <div className="space-y-4 text-sm" data-testid="ic-ei-result">
            <p className="font-medium text-slate-800">
              {executionPostureLabel(
                executionResult?.execution_posture ??
                  executionIntelligence?.execution_posture ??
                  "",
              )}
            </p>
            <p className="text-slate-700">
              {executionResult?.interpretation_summary ??
                executionIntelligence?.interpretation_summary}
            </p>
            <p className="text-slate-500">
              {(executionResult?.signals?.length ??
                executionIntelligence?.signal_count ??
                0) === 1
                ? "1 sinal"
                : `${executionResult?.signals?.length ?? executionIntelligence?.signal_count ?? 0} sinais`}{" "}
              ·{" "}
              {formatWhen(
                fullExecution?.generated_at ??
                  executionIntelligence?.generated_at ??
                  "",
              )}
            </p>
            {(executionResult?.interpretability_status ??
              executionIntelligence?.interpretability_status) ===
            "insufficient_facts" ? (
              <p className="rounded border border-slate-200 bg-slate-50 px-3 py-2 text-slate-700">
                Ainda faltam fatos para uma interpretação completa.
              </p>
            ) : null}
            {(fullExecution?.is_stale ?? executionIntelligence?.is_stale) ? (
              <p
                className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-amber-950"
                data-testid="ic-ei-stale"
              >
                A execução mudou desde esta interpretação. Gere uma leitura atualizada.
              </p>
            ) : (
              <p className="text-emerald-700" data-testid="ic-ei-current">
                Interpretação atual para os fatos disponíveis.
              </p>
            )}

            {executionResult && fullExecution ? (
              <>
                <p data-testid="ic-ei-mechanism" className="text-slate-600">
                  Como foi analisado: {mechanismLabel(executionResult.mechanism_version)}
                </p>

                {Object.entries(signalGroups).map(([category, signals]) => (
                  <section
                    key={category}
                    className="space-y-2 border-t border-slate-100 pt-3"
                  >
                    <h4 className="font-medium text-slate-800">
                      {SIGNAL_CATEGORY_LABELS[category] ?? "Sinais da execução"}
                    </h4>
                    {signals.map((signal) => (
                      <article
                        key={signal.code}
                        className="rounded border border-slate-200 p-3"
                        data-testid="ic-ei-signal"
                      >
                        <p className="font-medium text-slate-900">
                          {SIGNAL_LEVEL_LABELS[signal.level]} — {signal.title}
                        </p>
                        <p className="mt-1 text-slate-700">{signal.interpretation}</p>
                        <div className="mt-2">
                          <p className="font-medium text-slate-700">
                            Fatos considerados
                          </p>
                          <ul className="list-disc pl-5 text-slate-600">
                            {signal.supporting_fact_refs.map((ref) => (
                              <li key={ref}>{factLabel(fullExecution, ref)}</li>
                            ))}
                          </ul>
                        </div>
                        <p className="mt-2 text-slate-600">
                          Base ISO 9001: {signal.iso_basis.join(", ")}
                        </p>
                        <p className="mt-2 text-slate-800">
                          <span className="font-medium">Próximo passo recomendado:</span>{" "}
                          {signal.recommended_next_step}
                        </p>
                      </article>
                    ))}
                  </section>
                ))}

                {(executionResult.missing_information?.length ?? 0) > 0 ? (
                  <section data-testid="ic-ei-missing">
                    <h4 className="font-medium text-slate-800">
                      Informações que ainda faltam
                    </h4>
                    <CodeList
                      items={executionResult.missing_information ?? []}
                      empty="Nenhuma informação adicional indicada."
                    />
                  </section>
                ) : null}
                {(executionResult.limitations?.length ?? 0) > 0 ? (
                  <section data-testid="ic-ei-limitations">
                    <h4 className="font-medium text-slate-800">
                      Limites desta interpretação
                    </h4>
                    <CodeList
                      items={executionResult.limitations ?? []}
                      empty="Nenhuma limitação informada."
                    />
                  </section>
                ) : null}

                <div
                  className="rounded border border-violet-200 bg-violet-50 px-3 py-2 text-violet-950"
                  data-testid="ic-ei-human-warning"
                >
                  Esta interpretação sempre requer validação humana. Meta atingida não
                  significa eficácia comprovada, e os sinais não alteram decisões do caso.
                </div>

                {(executionData?.history.length ?? 0) > 0 ? (
                  <section className="border-t border-slate-100 pt-3" data-testid="ic-ei-history">
                    <h4 className="font-medium text-slate-800">
                      Histórico de interpretações
                    </h4>
                    <ul className="mt-1 space-y-1 text-slate-600">
                      {executionData?.history.map((item, index) => (
                        <li key={item.id}>
                          {index === 0 ? "Mais recente" : "Anterior"} ·{" "}
                          {formatWhen(item.generated_at)} ·{" "}
                          {executionPostureLabel(item.result.execution_posture)} ·{" "}
                          {item.is_stale ? "desatualizada" : "atual"}
                        </li>
                      ))}
                    </ul>
                  </section>
                ) : null}
              </>
            ) : (
              <p className="text-slate-500">
                Os detalhes completos estão temporariamente indisponíveis; o último
                resumo foi preservado.
              </p>
            )}
          </div>
        ) : (
          <p className="text-sm text-slate-600" data-testid="ic-ei-never">
            A execução ainda não foi interpretada pelo QMind OI.
          </p>
        )}
        {createExecutionIntelligence.isError ? (
          <p className="text-sm text-red-700" role="alert" data-testid="ic-ei-error">
            Não foi possível interpretar a execução agora. Os dados do caso não foram alterados.
          </p>
        ) : null}
        {executionQuery.isError ? (
          <p className="text-sm text-amber-800" role="alert" data-testid="ic-ei-load-error">
            Não foi possível atualizar os detalhes agora. A última interpretação
            disponível foi preservada.
          </p>
        ) : null}
        {canAnalyzeExecution ? (
          <button
            type="button"
            className="qm-btn-secondary"
            disabled={createExecutionIntelligence.isPending}
            onClick={() => createExecutionIntelligence.mutate()}
            data-testid="ic-ei-run"
          >
            {executionIntelligence ? "Atualizar interpretação" : "Interpretar execução"}
          </button>
        ) : null}
      </div>

      <div className="qm-panel space-y-3" data-testid="ic-evo-outcome">
        <h3 className="font-medium text-slate-800">Resultado observado</h3>
        {!latestObs ? (
          <p className="text-sm text-slate-600" data-testid="ic-evo-outcome-empty">
            Nenhum resultado foi registrado para este problema.
          </p>
        ) : null}

        {canWrite ? (
          formOpen ? (
            <form
              className="space-y-3"
              onSubmit={(e) => void submitObservation(e)}
              data-testid="ic-evo-outcome-form"
            >
              <label className="block text-sm">
                <span className="text-slate-700">
                  Como a situação se apresenta agora?
                </span>
                <select
                  className="qm-input mt-1 w-full"
                  value={direction}
                  onChange={(e) =>
                    setDirection(e.target.value as ResultDirection)
                  }
                  data-testid="ic-evo-direction"
                >
                  {RESULT_DIRECTION_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                <span className="text-slate-700">
                  O que foi observado depois das ações?
                </span>
                <textarea
                  className="qm-input mt-1 w-full"
                  rows={3}
                  value={statement}
                  onChange={(e) => setStatement(e.target.value)}
                  required
                  data-testid="ic-evo-statement"
                />
              </label>
              <label className="block text-sm">
                <span className="text-slate-700">
                  Em que informação essa observação se baseia?
                </span>
                <textarea
                  className="qm-input mt-1 w-full"
                  rows={2}
                  value={basis}
                  onChange={(e) => setBasis(e.target.value)}
                  required
                  data-testid="ic-evo-basis"
                />
              </label>
              <label className="block text-sm">
                <span className="text-slate-700">
                  Quando essa observação foi realizada?
                </span>
                <input
                  type="datetime-local"
                  className="qm-input mt-1 w-full"
                  value={observedLocal}
                  onChange={(e) => setObservedLocal(e.target.value)}
                  required
                  data-testid="ic-evo-observed-at"
                />
              </label>
              {formError ? (
                <p className="text-sm text-red-700" role="alert">
                  {formError}
                </p>
              ) : null}
              <div className="flex flex-wrap gap-2">
                <button
                  type="submit"
                  className="qm-btn-primary"
                  disabled={createObs.isPending}
                >
                  Salvar observação
                </button>
                <button
                  type="button"
                  className="qm-btn-secondary"
                  onClick={() => setFormOpen(false)}
                >
                  Cancelar
                </button>
              </div>
            </form>
          ) : (
            <button
              type="button"
              className="qm-btn-secondary"
              data-testid="ic-evo-register-outcome"
              onClick={() => setFormOpen(true)}
            >
              Registrar resultado observado
            </button>
          )
        ) : null}

        {observations.length > 0 ? (
          <ul className="space-y-2 text-sm" data-testid="ic-evo-outcome-history">
            {observations.map((o) => (
              <li
                key={o.id}
                className="border-t border-slate-100 pt-2"
                data-testid={`ic-evo-obs-${o.id}`}
              >
                <div className="font-medium text-slate-800">
                  {labelResultDirection(o.result_direction)} ·{" "}
                  {formatWhen(o.observed_at)}
                </div>
                <p className="text-slate-700">{o.observation_statement}</p>
                <p className="text-slate-500">Base: {o.measurement_basis}</p>
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <div className="qm-panel space-y-3" data-testid="ic-evo-comparison">
        <h3 className="font-medium text-slate-800">Comparação das análises</h3>
        {!comparison ? (
          <p
            className="text-sm text-slate-600"
            data-testid="ic-evo-comparison-empty"
          >
            São necessárias pelo menos duas análises para visualizar mudanças.
          </p>
        ) : (
          <div className="space-y-3 text-sm text-slate-700">
            <p>
              Contexto:{" "}
              {labelProblemContextStatus(comparison.context_status_before)} →{" "}
              {labelProblemContextStatus(comparison.context_status_after)}
            </p>
            <div>
              <p className="font-medium text-slate-800">Pontos novos</p>
              <CodeList
                items={comparison.findings_added ?? []}
                empty="Nenhum"
              />
            </div>
            <div>
              <p className="font-medium text-slate-800">
                Pontos que permanecem
              </p>
              <CodeList
                items={comparison.findings_persisting ?? []}
                empty="Nenhum"
              />
            </div>
            <div>
              <p className="font-medium text-slate-800">
                Pontos que não aparecem na análise mais recente
              </p>
              <CodeList
                items={comparison.findings_removed ?? []}
                empty="Nenhum"
              />
              <p className="mt-1 text-slate-500" data-testid="ic-evo-removed-copy">
                Este ponto não aparece na análise mais recente.
              </p>
            </div>
            <div>
              <p className="font-medium text-slate-800">
                Informações ausentes adicionadas
              </p>
              <CodeList
                items={comparison.missing_information_added ?? []}
                empty="Nenhuma"
              />
            </div>
            <div>
              <p className="font-medium text-slate-800">
                Informações ausentes removidas
              </p>
              <CodeList
                items={comparison.missing_information_removed ?? []}
                empty="Nenhuma"
              />
            </div>
            <div>
              <p className="font-medium text-slate-800">
                Limitações adicionadas
              </p>
              <CodeList
                items={comparison.limitations_added ?? []}
                empty="Nenhuma"
              />
            </div>
            <div>
              <p className="font-medium text-slate-800">
                Limitações removidas
              </p>
              <CodeList
                items={comparison.limitations_removed ?? []}
                empty="Nenhuma"
              />
            </div>
          </div>
        )}
      </div>

      <div className="qm-panel space-y-3" data-testid="ic-evo-actions-review">
        <h3 className="font-medium text-slate-800">Ações e revisão</h3>
        <ul className="text-sm text-slate-700 space-y-1">
          <li>Total de ações: {actions.total}</li>
          <li>Concluídas: {actions.completed}</li>
          <li>Pendentes: {pending}</li>
          <li>Vencidas: {actions.overdue}</li>
          {byStatus.map((s) => (
            <li key={s.status}>
              {s.status}: {s.count}
            </li>
          ))}
        </ul>
        <p className="text-sm text-slate-500">
          Ação concluída não implica eficácia comprovada nem resolução do
          problema.
        </p>

        {statusError ? (
          <p className="text-sm text-red-700" role="alert">
            {statusError}
          </p>
        ) : null}

        {canWrite && ready && caseStatus === "acting" ? (
          <button
            type="button"
            className="qm-btn-primary"
            data-testid="ic-evo-to-review"
            onClick={() => void moveToReview()}
            disabled={patch.isPending}
          >
            Colocar em revisão
          </button>
        ) : null}

        {canWrite && caseStatus === "reviewing" ? (
          confirmClose ? (
            <div
              className="space-y-2 rounded border border-slate-200 p-3"
              data-testid="ic-evo-close-confirm"
            >
              <p className="text-sm text-slate-700">
                Encerrar o acompanhamento registra uma decisão da organização.
                Não representa conformidade, certificação ou comprovação
                automática de eficácia.
              </p>
              <p className="text-sm text-slate-600">
                Resumo: {evo.analysis_summary.total_runs} análises ·{" "}
                {actions.total} ações · observação:{" "}
                {latestObs
                  ? labelResultDirection(latestObs.result_direction)
                  : "nenhuma"}
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="qm-btn-primary"
                  data-testid="ic-evo-close-confirm-yes"
                  onClick={() => void confirmCloseCase()}
                  disabled={patch.isPending}
                >
                  Confirmar encerramento
                </button>
                <button
                  type="button"
                  className="qm-btn-secondary"
                  onClick={() => setConfirmClose(false)}
                >
                  Cancelar
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              className="qm-btn-secondary"
              data-testid="ic-evo-close"
              onClick={() => setConfirmClose(true)}
            >
              Encerrar
            </button>
          )
        ) : null}
      </div>
    </div>
  );
}
