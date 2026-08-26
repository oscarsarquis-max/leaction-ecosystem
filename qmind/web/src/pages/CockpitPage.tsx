import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import { canReadCockpit } from "@/lib/permissions";
import { queryKeys } from "@/api/queryKeys";
import { QmindApiError } from "@/api/qmindApi";
import {
  AccessDeniedPanel,
  LoadingPanel,
} from "@/components/StatePanels";
import { GuidedEmptyState, PageHeader } from "@/components/qm";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import {
  useIsoIntelligenceCockpitActivity,
  useIsoIntelligenceCockpitCases,
  useIsoIntelligenceCockpitSummary,
  type CockpitCaseFilters,
} from "@/hooks/useIsoIntelligenceCockpit";
import type {
  CockpitCaseItemOut,
  LabeledCount,
  MeasurementPosture,
  SignalCountOut,
} from "@qmind/api-client";
import {
  MEASUREMENT_POSTURE_LABELS,
  TARGET_POSTURE_LABELS,
} from "@/execution/measurementLabels";

const EXECUTION_POSTURE_LABELS: Record<string, string> = {
  insufficient_information: "Informações insuficientes",
  not_started: "Execução ainda não iniciada",
  progressing: "Execução em andamento",
  attention_required: "Execução requer atenção",
  stalled: "Execução sem avanço recente",
  awaiting_result_evaluation: "Aguardando avaliação do resultado",
  result_observed: "Resultado observado",
};

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

const PRIORITY_BAND_VALUES = [
  "immediate_attention",
  "attention",
  "follow_up",
  "on_course",
  "completed_or_observed",
] as const;

const FRESHNESS_VALUES = ["current", "stale", "never_analyzed"] as const;

const MEASUREMENT_VALUES = [
  "not_planned",
  "awaiting_baseline",
  "awaiting_measurement",
  "on_time",
  "overdue",
] as const satisfies readonly MeasurementPosture[];

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return "—";
  }
}

function labeledDisplay(item: LabeledCount, map?: Record<string, string>): string {
  if (map?.[item.code]) return map[item.code]!;
  if (item.label && item.label !== item.code) return item.label;
  return map?.[item.code] ?? item.label;
}

function signalLabel(signal: SignalCountOut): string {
  const category = signal.category
    ? SIGNAL_CATEGORY_LABELS[signal.category] ?? "Categoria"
    : "Sem categoria";
  const level = signal.level
    ? SIGNAL_LEVEL_LABELS[signal.level] ?? "Nível"
    : "Sem nível";
  return `${category} · ${level}`;
}

function countFromDistribution(
  items: LabeledCount[] | undefined,
  code: string,
): number {
  return items?.find((item) => item.code === code)?.count ?? 0;
}

type UrlFilterState = {
  priority_band?: CockpitCaseFilters["priority_band"];
  intelligence_freshness?: CockpitCaseFilters["intelligence_freshness"];
  measurement_posture?: MeasurementPosture;
  execution_posture?: CockpitCaseFilters["execution_posture"];
  signal_category?: CockpitCaseFilters["signal_category"];
  search?: string;
  related_process?: string;
  ready_for_review?: boolean;
  has_overdue_actions?: boolean;
  has_active_impediment?: boolean;
};

function parseUrlFilters(params: URLSearchParams): UrlFilterState {
  const priority = params.get("priority_band");
  const freshness = params.get("intelligence_freshness");
  const measurement = params.get("measurement_posture");
  const execution = params.get("execution_posture");
  const signal = params.get("signal_category");
  return {
    priority_band: PRIORITY_BAND_VALUES.includes(
      priority as (typeof PRIORITY_BAND_VALUES)[number],
    )
      ? (priority as UrlFilterState["priority_band"])
      : undefined,
    intelligence_freshness: FRESHNESS_VALUES.includes(
      freshness as (typeof FRESHNESS_VALUES)[number],
    )
      ? (freshness as UrlFilterState["intelligence_freshness"])
      : undefined,
    measurement_posture: MEASUREMENT_VALUES.includes(
      measurement as MeasurementPosture,
    )
      ? (measurement as MeasurementPosture)
      : undefined,
    execution_posture: execution
      ? (execution as UrlFilterState["execution_posture"])
      : undefined,
    signal_category: signal
      ? (signal as UrlFilterState["signal_category"])
      : undefined,
    search: params.get("search")?.trim() || undefined,
    related_process: params.get("related_process")?.trim() || undefined,
    ready_for_review: params.get("ready_for_review") === "1",
    has_overdue_actions: params.get("has_overdue_actions") === "1",
    has_active_impediment: params.get("has_active_impediment") === "1",
  };
}

function hasAnyFilter(f: UrlFilterState): boolean {
  return Boolean(
    f.priority_band ||
      f.intelligence_freshness ||
      f.measurement_posture ||
      f.execution_posture ||
      f.signal_category ||
      f.search ||
      f.related_process ||
      f.ready_for_review ||
      f.has_overdue_actions ||
      f.has_active_impediment,
  );
}

function DistributionBlock({
  title,
  items,
  labelMap,
  testId,
  onSelect,
}: {
  title: string;
  items: LabeledCount[];
  labelMap?: Record<string, string>;
  testId: string;
  onSelect?: (code: string) => void;
}) {
  const max = Math.max(...items.map((item) => item.count), 1);
  return (
    <section className="qm-panel space-y-3 px-4 py-4" data-testid={testId}>
      <h3 className="text-sm font-semibold text-[var(--qm-ink)]">{title}</h3>
      {items.length === 0 ? (
        <p className="text-sm text-[var(--qm-muted)]">Sem dados nesta distribuição.</p>
      ) : (
        <>
          <ul className="space-y-2" role="list">
            {items.map((item) => {
              const label = labeledDisplay(item, labelMap);
              const width = `${Math.max((item.count / max) * 100, item.count > 0 ? 4 : 0)}%`;
              const content = (
                <>
                  <div className="flex items-center justify-between gap-2 text-sm">
                    <span className="text-[var(--qm-ink)]">{label}</span>
                    <span className="tabular-nums text-[var(--qm-muted)]">
                      {item.count}
                    </span>
                  </div>
                  <div
                    className="mt-1 h-2 rounded bg-[var(--qm-surface-soft)]"
                    aria-hidden
                  >
                    <div
                      className="h-2 rounded bg-[var(--qm-ink)]/35"
                      style={{ width }}
                    />
                  </div>
                </>
              );
              return (
                <li key={item.code}>
                  {onSelect ? (
                    <button
                      type="button"
                      className="w-full rounded text-left hover:bg-[var(--qm-surface-soft)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--qm-focus)]"
                      onClick={() => onSelect(item.code)}
                      aria-label={`${label}: ${item.count}`}
                    >
                      {content}
                    </button>
                  ) : (
                    <div aria-label={`${label}: ${item.count}`}>{content}</div>
                  )}
                </li>
              );
            })}
          </ul>
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{title} — tabela equivalente</caption>
            <thead>
              <tr className="text-[var(--qm-muted)]">
                <th scope="col" className="py-1 font-medium">
                  Faixa
                </th>
                <th scope="col" className="py-1 font-medium">
                  Quantidade
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={`t-${item.code}`} className="border-t border-[var(--qm-line)]">
                  <td className="py-1 text-[var(--qm-ink)]">
                    {labeledDisplay(item, labelMap)}
                  </td>
                  <td className="py-1 tabular-nums text-[var(--qm-muted)]">
                    {item.count}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}

function SignalDistribution({
  title,
  items,
  testId,
}: {
  title: string;
  items: SignalCountOut[];
  testId: string;
}) {
  const max = Math.max(...items.map((item) => item.count), 1);
  return (
    <section className="qm-panel space-y-3 px-4 py-4" data-testid={testId}>
      <h3 className="text-sm font-semibold text-[var(--qm-ink)]">{title}</h3>
      {items.length === 0 ? (
        <p className="text-sm text-[var(--qm-muted)]">Nenhum sinal atual.</p>
      ) : (
        <>
          <ul className="space-y-2" role="list">
            {items.map((item, index) => {
              const label = signalLabel(item);
              const width = `${Math.max((item.count / max) * 100, item.count > 0 ? 4 : 0)}%`;
              return (
                <li key={`${item.category ?? "x"}-${item.level ?? "y"}-${index}`}>
                  <div aria-label={`${label}: ${item.count}`}>
                    <div className="flex items-center justify-between gap-2 text-sm">
                      <span className="text-[var(--qm-ink)]">{label}</span>
                      <span className="tabular-nums text-[var(--qm-muted)]">
                        {item.count}
                      </span>
                    </div>
                    <div
                      className="mt-1 h-2 rounded bg-[var(--qm-surface-soft)]"
                      aria-hidden
                    >
                      <div
                        className="h-2 rounded bg-[var(--qm-ink)]/35"
                        style={{ width }}
                      />
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{title} — tabela equivalente</caption>
            <thead>
              <tr className="text-[var(--qm-muted)]">
                <th scope="col" className="py-1 font-medium">
                  Sinal
                </th>
                <th scope="col" className="py-1 font-medium">
                  Quantidade
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => (
                <tr
                  key={`st-${item.category ?? "x"}-${item.level ?? "y"}-${index}`}
                  className="border-t border-[var(--qm-line)]"
                >
                  <td className="py-1">{signalLabel(item)}</td>
                  <td className="py-1 tabular-nums">{item.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}

type SynthCard = {
  id: string;
  label: string;
  value: number;
  active: boolean;
  onClick: () => void;
};

function SynthesisCards({ cards }: { cards: SynthCard[] }) {
  return (
    <div
      className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
      data-testid="cockpit-summary"
    >
      {cards.map((card) => (
        <button
          key={card.id}
          type="button"
          data-testid={
            card.id === "immediate"
              ? "cockpit-filter-immediate"
              : `cockpit-synth-${card.id}`
          }
          aria-pressed={card.active}
          onClick={card.onClick}
          className={`qm-panel px-4 py-3 text-left transition ${
            card.active
              ? "border-[var(--qm-ink)] ring-1 ring-[var(--qm-ink)]"
              : "hover:bg-[var(--qm-surface-soft)]"
          }`}
        >
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--qm-muted)]">
            {card.label}
          </p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-[var(--qm-ink)]">
            {card.value}
          </p>
        </button>
      ))}
    </div>
  );
}

function CaseQueue({ items }: { items: CockpitCaseItemOut[] }) {
  return (
    <section className="space-y-3" data-testid="cockpit-queue">
      <h2 className="text-base font-semibold text-[var(--qm-ink)]">
        Fila de atenção
      </h2>

      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[48rem] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-[var(--qm-line)] text-[var(--qm-muted)]">
              <th scope="col" className="px-2 py-2 font-medium">
                Problema / processo
              </th>
              <th scope="col" className="px-2 py-2 font-medium">
                Faixa e motivos
              </th>
              <th scope="col" className="px-2 py-2 font-medium">
                Execução
              </th>
              <th scope="col" className="px-2 py-2 font-medium">
                Medição
              </th>
              <th scope="col" className="px-2 py-2 font-medium">
                Inteligência
              </th>
              <th scope="col" className="px-2 py-2 font-medium">
                Última atividade
              </th>
              <th scope="col" className="px-2 py-2 font-medium">
                Ação
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr
                key={item.case_id}
                className="border-b border-[var(--qm-line)] align-top"
                data-testid="cockpit-queue-row"
              >
                <td className="px-2 py-3">
                  <p className="font-medium text-[var(--qm-ink)]">
                    {item.problem_label}
                  </p>
                  {item.related_process ? (
                    <p className="text-[var(--qm-muted)]">{item.related_process}</p>
                  ) : null}
                </td>
                <td className="px-2 py-3">
                  <p className="font-medium">{item.priority_band_label}</p>
                  {(item.priority_reasons?.length ?? 0) > 0 ? (
                    <ul className="mt-1 list-inside list-disc text-[var(--qm-muted)]">
                      {item.priority_reasons!.map((reason) => (
                        <li key={reason.code}>{reason.label}</li>
                      ))}
                    </ul>
                  ) : null}
                </td>
                <td className="px-2 py-3">
                  {item.execution_posture
                    ? EXECUTION_POSTURE_LABELS[item.execution_posture] ??
                      "Postura disponível"
                    : "Sem leitura de execução"}
                </td>
                <td className="px-2 py-3">
                  {MEASUREMENT_POSTURE_LABELS[item.measurement_posture]}
                  <span className="block text-[var(--qm-muted)]">
                    {TARGET_POSTURE_LABELS[item.target_posture]}
                  </span>
                </td>
                <td className="px-2 py-3">
                  <span data-testid="cockpit-freshness-label">
                    {item.intelligence_freshness_label}
                  </span>
                </td>
                <td className="px-2 py-3 tabular-nums text-[var(--qm-muted)]">
                  {formatWhen(item.last_activity_at)}
                </td>
                <td className="px-2 py-3">
                  <Link
                    to={`/improvement-cases/${item.case_id}`}
                    className="qm-btn-secondary !px-3 !py-1.5 text-sm"
                    data-testid="cockpit-open-case"
                  >
                    Abrir caso
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className="space-y-3 md:hidden" data-testid="cockpit-queue-mobile">
        {items.map((item) => (
          <li
            key={item.case_id}
            className="qm-panel space-y-2 px-4 py-3"
            data-testid="cockpit-queue-card"
          >
            <p className="font-medium text-[var(--qm-ink)]">{item.problem_label}</p>
            {item.related_process ? (
              <p className="text-sm text-[var(--qm-muted)]">{item.related_process}</p>
            ) : null}
            <p className="text-sm">
              <span className="font-medium">{item.priority_band_label}</span>
            </p>
            {(item.priority_reasons?.length ?? 0) > 0 ? (
              <ul className="list-inside list-disc text-sm text-[var(--qm-muted)]">
                {item.priority_reasons!.map((reason) => (
                  <li key={reason.code}>{reason.label}</li>
                ))}
              </ul>
            ) : null}
            <p className="text-sm text-[var(--qm-muted)]">
              Execução:{" "}
              {item.execution_posture
                ? EXECUTION_POSTURE_LABELS[item.execution_posture] ??
                  "Postura disponível"
                : "Sem leitura"}
            </p>
            <p className="text-sm text-[var(--qm-muted)]">
              Medição: {MEASUREMENT_POSTURE_LABELS[item.measurement_posture]}
            </p>
            <p className="text-sm">
              Inteligência:{" "}
              <span data-testid="cockpit-freshness-label">
                {item.intelligence_freshness_label}
              </span>
            </p>
            <p className="text-sm text-[var(--qm-muted)]">
              Última atividade: {formatWhen(item.last_activity_at)}
            </p>
            <Link
              to={`/improvement-cases/${item.case_id}`}
              className="qm-btn-secondary inline-flex !px-3 !py-1.5 text-sm"
              data-testid="cockpit-open-case"
            >
              Abrir caso
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function CockpitPage() {
  const org = useOrganization();
  const qc = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchDraft, setSearchDraft] = useState(
    () => searchParams.get("search") ?? "",
  );

  const roles = org.currentOrganization?.roles;
  const canRead = canReadCockpit(roles);
  const orgName =
    org.currentOrganization?.organizationName ?? "organização selecionada";
  const orgId = org.currentOrganizationId;

  const filters = useMemo(
    () => parseUrlFilters(searchParams),
    [searchParams],
  );

  const apiFilters: CockpitCaseFilters = {
    priority_band: filters.priority_band,
    intelligence_freshness: filters.intelligence_freshness,
    measurement_posture: filters.measurement_posture,
    execution_posture: filters.execution_posture,
    signal_category: filters.signal_category,
    search: filters.search,
    related_process: filters.related_process,
    ready_for_review: filters.ready_for_review || undefined,
    has_overdue_actions: filters.has_overdue_actions || undefined,
    has_active_impediment: filters.has_active_impediment || undefined,
    limit: 25,
  };

  const summaryQuery = useIsoIntelligenceCockpitSummary();
  const casesQuery = useIsoIntelligenceCockpitCases(apiFilters);
  const activityQuery = useIsoIntelligenceCockpitActivity({ limit: 15 });

  const setFilterPatch = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(patch)) {
      if (value == null || value === "") next.delete(key);
      else next.set(key, value);
    }
    setSearchParams(next, { replace: true });
  };

  const clearFilters = () => {
    setSearchDraft("");
    setSearchParams({}, { replace: true });
  };

  const toggleParam = (key: string, value: string) => {
    const current = searchParams.get(key);
    setFilterPatch({ [key]: current === value ? null : value });
  };

  const refreshVision = async () => {
    if (!orgId) return;
    await Promise.all([
      qc.invalidateQueries({
        queryKey: queryKeys.isoIntelligenceCockpitSummary(orgId),
      }),
      qc.invalidateQueries({
        queryKey: [
          "org",
          orgId,
          "iso-intelligence",
          "cockpit",
          "cases",
        ],
      }),
      qc.invalidateQueries({
        queryKey: [
          "org",
          orgId,
          "iso-intelligence",
          "cockpit",
          "activity",
        ],
      }),
    ]);
  };

  if (!org.loading && org.memberships.length === 0) {
    return (
      <AccessDeniedPanel message="Você ainda não possui acesso a uma organização." />
    );
  }

  if (!orgId) {
    return (
      <GuidedEmptyState
        title="Escolha uma organização para abrir o Cockpit"
        why="O Cockpit resume a inteligência ISO da organização selecionada."
        example="Selecione a organização no cabeçalho."
        howToStart="Use o seletor “Organização” no topo."
      />
    );
  }

  if (!canRead) {
    return (
      <AccessDeniedPanel message="Seu papel nesta organização não inclui leitura do Cockpit de Inteligência ISO." />
    );
  }

  const summaryLoading = summaryQuery.isLoading && !summaryQuery.data;
  const casesLoading = casesQuery.isLoading && !casesQuery.data;
  if (summaryLoading || casesLoading) {
    return <LoadingPanel title="Carregando o Cockpit…" />;
  }

  const summary = summaryQuery.data;
  const casesPages = casesQuery.data?.pages ?? [];
  const casesPage = casesPages[0];
  const items = casesPages.flatMap((page) => page.items ?? []);
  const filtered = hasAnyFilter(filters);
  const orgEmpty =
    !filtered &&
    (summary?.case_totals.total ?? 0) === 0 &&
    items.length === 0;

  const immediate = countFromDistribution(
    summary?.priority_distribution,
    "immediate_attention",
  );
  const attention = countFromDistribution(
    summary?.priority_distribution,
    "attention",
  );

  const synthCards: SynthCard[] = [
    {
      id: "active",
      label: "Casos ativos",
      value: summary?.case_totals.active ?? 0,
      active: !filtered,
      onClick: clearFilters,
    },
    {
      id: "immediate",
      label: "Atenção imediata",
      value: immediate,
      active: filters.priority_band === "immediate_attention",
      onClick: () => toggleParam("priority_band", "immediate_attention"),
    },
    {
      id: "attention",
      label: "Atenção",
      value: attention,
      active: filters.priority_band === "attention",
      onClick: () => toggleParam("priority_band", "attention"),
    },
    {
      id: "overdue-actions",
      label: "Ações vencidas",
      value: summary?.execution.overdue_actions ?? 0,
      active: Boolean(filters.has_overdue_actions),
      onClick: () =>
        toggleParam(
          "has_overdue_actions",
          filters.has_overdue_actions ? "" : "1",
        ),
    },
    {
      id: "blocked",
      label: "Casos bloqueados",
      value: summary?.execution.blocked_cases ?? 0,
      active: Boolean(filters.has_active_impediment),
      onClick: () =>
        toggleParam(
          "has_active_impediment",
          filters.has_active_impediment ? "" : "1",
        ),
    },
    {
      id: "overdue-measurement",
      label: "Medições atrasadas",
      value: summary?.measurement.overdue_indicators ?? 0,
      active: filters.measurement_posture === "overdue",
      onClick: () => toggleParam("measurement_posture", "overdue"),
    },
    {
      id: "ready-review",
      label: "Prontos para revisão",
      value: summary?.case_totals.ready_for_review ?? 0,
      active: Boolean(filters.ready_for_review),
      onClick: () =>
        toggleParam(
          "ready_for_review",
          filters.ready_for_review ? "" : "1",
        ),
    },
    {
      id: "ei-current",
      label: "EI atual",
      value: summary?.intelligence_coverage.current ?? 0,
      active: filters.intelligence_freshness === "current",
      onClick: () => toggleParam("intelligence_freshness", "current"),
    },
    {
      id: "ei-stale",
      label: "EI desatualizada",
      value: summary?.intelligence_coverage.stale ?? 0,
      active: filters.intelligence_freshness === "stale",
      onClick: () => toggleParam("intelligence_freshness", "stale"),
    },
    {
      id: "ei-never",
      label: "EI nunca analisada",
      value: summary?.intelligence_coverage.never_analyzed ?? 0,
      active: filters.intelligence_freshness === "never_analyzed",
      onClick: () => toggleParam("intelligence_freshness", "never_analyzed"),
    },
  ];

  const asOf = summary?.as_of ?? casesPage?.as_of;
  const activityItems = activityQuery.data?.items ?? summary?.recent_activity ?? [];

  const summaryDenied =
    summaryQuery.isError &&
    summaryQuery.error instanceof QmindApiError &&
    (summaryQuery.error.status === 401 || summaryQuery.error.status === 403);
  const casesDenied =
    casesQuery.isError &&
    casesQuery.error instanceof QmindApiError &&
    (casesQuery.error.status === 401 || casesQuery.error.status === 403);

  if ((summaryDenied || casesDenied) && !summary && !casesPage) {
    return <AccessDeniedPanel message="Acesso negado ao Cockpit." />;
  }

  return (
    <section className="space-y-6" data-testid="cockpit-page">
      <PageHeader
        title="Cockpit de Inteligência ISO"
        explanation={`Visão consolidada de ${orgName}. Os números apoiam a decisão humana; não substituem julgamento nem fecham casos automaticamente.`}
        expectedResult="Fila priorizada com motivos legíveis e leitura atual da execução."
        nextStep="Abrir um caso que peça atenção e decidir o próximo passo humano."
        actions={
          <button
            type="button"
            className="qm-btn-secondary"
            data-testid="cockpit-refresh"
            onClick={() => void refreshVision()}
          >
            Atualizar visão
          </button>
        }
      >
        <p className="mt-2 text-sm text-[var(--qm-muted)]" data-testid="cockpit-as-of">
          Dados atualizados em {formatWhen(asOf)}
        </p>
        <p className="mt-1 text-sm text-[var(--qm-muted)]">
          Decisões permanecem humanas — o Cockpit não gera nova análise OI ao
          atualizar.
        </p>
      </PageHeader>

      {summaryQuery.isError && summary ? (
        <ApiErrorBanner
          title="Falha ao atualizar o resumo (dados anteriores mantidos)"
          error={summaryQuery.error}
          onRetry={() => void summaryQuery.refetch()}
        />
      ) : null}
      {casesQuery.isError && casesPage ? (
        <ApiErrorBanner
          title="Falha ao atualizar a fila (dados anteriores mantidos)"
          error={casesQuery.error}
          onRetry={() => void casesQuery.refetch()}
        />
      ) : null}
      {activityQuery.isError && activityQuery.data ? (
        <ApiErrorBanner
          title="Falha ao atualizar a atividade recente (dados anteriores mantidos)"
          error={activityQuery.error}
          onRetry={() => void activityQuery.refetch()}
        />
      ) : null}

      {summaryQuery.isError && !summary ? (
        <ApiErrorBanner
          title="Não foi possível carregar o resumo do Cockpit"
          error={summaryQuery.error}
          onRetry={() => void summaryQuery.refetch()}
        />
      ) : null}
      {casesQuery.isError && !casesPage ? (
        <ApiErrorBanner
          title="Não foi possível carregar a fila do Cockpit"
          error={casesQuery.error}
          onRetry={() => void casesQuery.refetch()}
        />
      ) : null}

      {summary ? <SynthesisCards cards={synthCards} /> : null}

      {summary ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <DistributionBlock
            title="Distribuição por prioridade"
            items={summary.priority_distribution ?? []}
            testId="cockpit-dist-priority"
            onSelect={(code) => toggleParam("priority_band", code)}
          />
          <DistributionBlock
            title="Postura de execução (atual)"
            items={summary.execution_posture_distribution_current ?? []}
            labelMap={EXECUTION_POSTURE_LABELS}
            testId="cockpit-dist-execution-current"
            onSelect={(code) => toggleParam("execution_posture", code)}
          />
          <DistributionBlock
            title="Postura de execução (desatualizada)"
            items={summary.execution_posture_distribution_stale ?? []}
            labelMap={EXECUTION_POSTURE_LABELS}
            testId="cockpit-dist-execution-stale"
          />
          <DistributionBlock
            title="Cobertura de inteligência"
            items={[
              {
                code: "current",
                label: "Atual",
                count: summary.intelligence_coverage.current,
                unit: summary.intelligence_coverage.unit,
              },
              {
                code: "stale",
                label: "Desatualizada",
                count: summary.intelligence_coverage.stale,
                unit: summary.intelligence_coverage.unit,
              },
              {
                code: "never_analyzed",
                label: "Nunca analisada",
                count: summary.intelligence_coverage.never_analyzed,
                unit: summary.intelligence_coverage.unit,
              },
            ]}
            testId="cockpit-dist-intelligence"
            onSelect={(code) => toggleParam("intelligence_freshness", code)}
          />
          <DistributionBlock
            title="Posturas de medição"
            items={summary.measurement.by_measurement_posture ?? []}
            labelMap={MEASUREMENT_POSTURE_LABELS}
            testId="cockpit-dist-measurement"
            onSelect={(code) => toggleParam("measurement_posture", code)}
          />
          <SignalDistribution
            title="Sinais atuais"
            items={summary.signals_current ?? []}
            testId="cockpit-dist-signals-current"
          />
        </div>
      ) : null}

      <section className="qm-panel space-y-3 px-4 py-4" data-testid="cockpit-filters">
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex min-w-[12rem] flex-1 flex-col gap-1 text-sm">
            <span className="text-[var(--qm-muted)]">Buscar</span>
            <input
              value={searchDraft}
              onChange={(e) => setSearchDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  setFilterPatch({ search: searchDraft.trim() || null });
                }
              }}
              className="qm-field"
              placeholder="Problema ou processo"
              data-testid="cockpit-search"
            />
          </label>
          <button
            type="button"
            className="qm-btn-secondary !px-3 !py-2"
            onClick={() =>
              setFilterPatch({ search: searchDraft.trim() || null })
            }
          >
            Aplicar busca
          </button>
          {filtered ? (
            <button
              type="button"
              className="qm-btn-secondary !px-3 !py-2"
              data-testid="cockpit-clear-filters"
              onClick={clearFilters}
            >
              Limpar filtros
            </button>
          ) : null}
        </div>
        {filtered ? (
          <p className="text-sm text-[var(--qm-muted)]" data-testid="cockpit-filter-active">
            Filtros ativos na URL — voltam ao retornar do caso.
          </p>
        ) : null}
      </section>

      {orgEmpty ? (
        <GuidedEmptyState
          title="Nenhum caso de melhoria nesta organização"
          why="O Cockpit ganha sentido quando há casos ativos com execução e medição."
          example="Crie um caso a partir do perfil da organização ou de uma avaliação."
          howToStart="Volte à home da organização e abra Casos de melhoria."
        />
      ) : items.length === 0 ? (
        <div
          className="qm-panel--dashed qm-panel px-4 py-6 text-sm text-[var(--qm-muted)]"
          data-testid="cockpit-empty-filter"
        >
          Nenhum caso corresponde aos filtros atuais. Ajuste ou limpe os filtros
          para voltar à fila completa.
        </div>
      ) : (
        <div className="space-y-3">
          <CaseQueue items={items} />
          {casesQuery.hasNextPage ? (
            <div className="flex justify-center">
              <button
                type="button"
                className="qm-btn-secondary"
                data-testid="cockpit-load-more"
                disabled={casesQuery.isFetchingNextPage}
                onClick={() => void casesQuery.fetchNextPage()}
              >
                {casesQuery.isFetchingNextPage
                  ? "Carregando…"
                  : "Carregar mais"}
              </button>
            </div>
          ) : null}
        </div>
      )}

      <section className="qm-panel space-y-3 px-4 py-4" data-testid="cockpit-activity">
        <h2 className="text-base font-semibold text-[var(--qm-ink)]">
          Atividade recente
        </h2>
        {activityQuery.isLoading && !activityQuery.data ? (
          <p className="text-sm text-[var(--qm-muted)]">Carregando atividade…</p>
        ) : activityItems.length === 0 ? (
          <p className="text-sm text-[var(--qm-muted)]">
            Nenhuma atividade operacional recente no período.
          </p>
        ) : (
          <ul className="space-y-2 text-sm">
            {activityItems.map((item, index) => (
              <li
                key={`${item.event_type}-${item.occurred_at}-${index}`}
                className="border-b border-[var(--qm-line)] pb-2 last:border-0"
              >
                <p className="font-medium text-[var(--qm-ink)]">
                  {item.event_type_label}
                </p>
                <p className="text-[var(--qm-muted)]">{item.summary}</p>
                <p className="tabular-nums text-[var(--qm-muted)]">
                  {formatWhen(item.occurred_at)}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
