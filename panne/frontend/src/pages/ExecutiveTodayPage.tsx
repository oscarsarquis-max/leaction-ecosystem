import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { DashboardAttention, DashboardMetric, DashboardTask, DashboardToday } from "../api/types";
import { useAssistantOptional } from "../assistant/AssistantContext";
import { ErrorState, LoadingState } from "../components/Feedback";
import { useAsyncResource } from "../hooks/useAsyncResource";
import {
  attentionConsequence,
  dashboardDateLabel,
  dashboardMetricLabel,
  executiveBrief,
  kpiComplement,
  yesterdaySummary,
} from "../language/dashboard";
import { useOrganization } from "../session/OrganizationContext";
import {
  AgendaPanel,
  ChartGuard,
  CostsChart,
  MovementsChart,
  PERIOD_OPTIONS,
  PeriodFilter,
  PricesChart,
  ProductionChart,
  chartUpdatedLine,
  type DashboardPeriod,
} from "./executiveCharts";
import { EXEC_LIMITS } from "./executiveLimits";

function Kpi({
  title,
  value,
  hint,
}: {
  title: string;
  value: string;
  hint: string;
}) {
  return (
    <article className="exec-kpi">
      <h3>{title}</h3>
      <p className="exec-kpi__value">{value}</p>
      <p className="exec-kpi__meta">{hint}</p>
    </article>
  );
}

function metricKpi(title: string, metric: DashboardMetric, hint?: string) {
  return {
    title,
    value: dashboardMetricLabel(metric),
    hint: kpiComplement(metric, hint),
  };
}

function PriorityIcon({ severity }: { severity: string }) {
  const mark = severity === "high" ? "!" : severity === "medium" ? "•" : "i";
  return (
    <span className={`exec-priority__icon exec-priority__icon--${severity}`} aria-hidden="true">
      {mark}
    </span>
  );
}

function buildKpis(data: DashboardToday, economy: boolean) {
  const stock = data.charts.stock;
  const stockCount = stock.available ? stock.series.length : null;
  const stockValue =
    stockCount == null ? "Sem informação" : stockCount === 0 ? "Nenhum registro" : String(stockCount);
  const stockHint =
    stockCount == null
      ? "sem informação"
      : stockCount === 0
        ? "nenhum registro"
        : stock.series[0]?.status_label || "itens abaixo do mínimo";

  const prices = data.charts.prices;
  const weakPrices = prices?.available
    ? prices.series.filter((row) => row.status === "conflict" || row.margin == null || row.basis === "ausente").length
    : null;

  const items = [
    metricKpi("Ordens de hoje", data.today.orders_planned, "recorte de hoje"),
    metricKpi("Em andamento", data.today.orders_in_progress, "pesagem, prontas ou em execução"),
    metricKpi("Entradas aguardadas", data.today.expected_receipts, "aguardando conferência"),
    { title: "Estoque crítico", value: stockValue, hint: stockHint },
  ];
  if (economy && data.business?.cost_coverage) {
    items.push(metricKpi("Custos completos", data.business.cost_coverage, "produtos analisados"));
  }
  if (economy) {
    items.push({
      title: "Preços sem base comercial",
      value: weakPrices == null ? "Sem informação" : weakPrices === 0 ? "Nenhum registro" : String(weakPrices),
      hint: weakPrices == null ? "sem informação" : weakPrices === 0 ? "nenhum registro" : "requer decisão comercial",
    });
  }
  return items.slice(0, EXEC_LIMITS.kpis);
}

function mergePriorities(data: DashboardToday): Array<(DashboardAttention | DashboardTask) & { kind: "attention" | "task" }> {
  const attentions = data.attentions.map((item) => ({ ...item, kind: "attention" as const }));
  const tasks = data.today.priority_tasks.map((item) => ({ ...item, kind: "task" as const }));
  const seen = new Set<string>();
  const out: Array<(DashboardAttention | DashboardTask) & { kind: "attention" | "task" }> = [];
  for (const item of [...attentions, ...tasks]) {
    const key = `${item.title}|${item.href}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(item);
  }
  return out;
}

export function ExecutiveTodayPage() {
  const { api, hasPermission, active } = useOrganization();
  const assistant = useAssistantOptional();
  const orgId = active?.organization_id ?? null;
  const [period, setPeriod] = useState<DashboardPeriod>("today");
  const { state, reload } = useAsyncResource<DashboardToday>(
    () => api.getDashboardToday(undefined, period),
    [api, orgId, period],
    Boolean(orgId),
  );

  const liveData = state.kind === "ok" ? state.data : null;
  const publishLive = assistant?.publishLive;
  useEffect(() => {
    if (!publishLive || !liveData) return;
    const brief = executiveBrief(liveData);
    publishLive({
      goal: brief.lead,
      pending: liveData.headline.attention || liveData.attentions[0]?.title || "Nenhuma pendência destacada.",
      next: brief.action,
    });
  }, [publishLive, liveData]);

  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={() => reload()} />;

  const data = state.data;
  const economy = Boolean(data.business && data.permissions.economy && hasPermission("costing.read"));
  const charts = data.charts;
  const brief = executiveBrief(data);
  const kpis = buildKpis(data, economy);
  const priorities = mergePriorities(data);
  const visiblePriorities = priorities.slice(0, EXEC_LIMITS.priorities);
  const extraPriorities = priorities.length - visiblePriorities.length;
  const yesterday = yesterdaySummary(data);
  const producedLabels = charts.production.series.map((row) => row.label);

  return (
    <div className="exec-today">
      <header className="exec-topline">
        <div>
          <p className="exec-eyebrow">Painel do proprietário</p>
          <h1 id="exec-title">Hoje na Panne</h1>
          <p className="exec-context">
            {dashboardDateLabel(data.operational_date)}
            {" · "}
            {data.organization.name || "Organização"}
            {data.establishment?.name ? ` · ${data.establishment.name}` : ""}
            {" · "}
            {chartUpdatedLine(charts)}
          </p>
        </div>
      </header>

      <aside className="exec-brief" aria-label="Resumo executivo">
        <div>
          <p>
            <strong>{brief.lead}</strong>
            {brief.causes ? ` ${brief.causes}.` : ""}
          </p>
        </div>
        {brief.action === "Ver prioridades" ? (
          <a
            className="exec-brief__action"
            href="#exec-priorities"
            onClick={(event) => {
              event.preventDefault();
              document.getElementById("exec-priorities")?.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
          >
            {brief.action}
          </a>
        ) : (
          <Link className="exec-brief__action" to={brief.href}>
            {brief.action}
          </Link>
        )}
      </aside>

      <section className="exec-kpis" role="region" aria-label="Indicadores principais">
        {kpis.map((item) => (
          <Kpi key={item.title} title={item.title} value={item.value} hint={item.hint} />
        ))}
      </section>

      <div className="exec-charts-head">
        <p className="meta">
          Indicadores de hoje e de ontem não mudam de sentido. O período vale para os gráficos.
        </p>
        <PeriodFilter id="exec-period-charts" value={period} onChange={setPeriod} />
      </div>

      <div className="exec-primary">
        <ChartGuard>
          <ProductionChart chart={charts.production} charts={charts} />
        </ChartGuard>
        <aside className="exec-panel exec-priorities" id="exec-priorities" aria-labelledby="exec-priorities-title">
          <div className="exec-panel__head">
            <div>
              <h2 id="exec-priorities-title">Prioridades</h2>
              <p className="exec-panel__conclusion">Exceções que exigem uma ação humana.</p>
            </div>
            {extraPriorities > 0 ? (
              <Link className="exec-panel__action" to="/gestao/relatorios">
                Ver todas
              </Link>
            ) : null}
          </div>
          {visiblePriorities.length ? (
            <ul className="exec-priority">
              {visiblePriorities.map((item) => (
                <li key={`${item.title}-${item.href}`} className={`exec-priority__item exec-priority__item--${item.severity}`}>
                  <PriorityIcon severity={item.severity} />
                  <div>
                    <p className="exec-priority__title">{item.title}</p>
                    <p className="meta">{attentionConsequence(item)}</p>
                    <Link to={item.href}>{item.kind === "task" ? "Abrir tarefa" : "Resolver"}</Link>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="meta">Nenhuma prioridade neste recorte.</p>
          )}
        </aside>
      </div>

      <ChartGuard>
        <MovementsChart chart={charts.movements} charts={charts} />
      </ChartGuard>

      <div className="exec-work">
        <ChartGuard>
          <AgendaPanel chart={charts.agenda} />
        </ChartGuard>
        {economy && charts.costs ? (
          <ChartGuard>
            <CostsChart chart={charts.costs} charts={charts} producedLabels={producedLabels} />
          </ChartGuard>
        ) : null}
      </div>

      {economy && charts.prices ? (
        <ChartGuard>
          <PricesChart chart={charts.prices} charts={charts} />
        </ChartGuard>
      ) : null}

      <section className="exec-yesterday" aria-labelledby="exec-yesterday">
        <h2 id="exec-yesterday">Ontem</h2>
        <p>{yesterday.line}</p>
        {yesterday.empty ? (
          <button type="button" className="ghost" onClick={() => setPeriod("yesterday")}>
            Consultar o período
          </button>
        ) : null}
      </section>

      <footer className="exec-footer">
        <p className="meta">
          Período dos gráficos: {PERIOD_OPTIONS.find((option) => option.code === period)?.label}.
        </p>
        <Link className="primary" to="/fluxo">
          Abrir Fluxo produtivo
        </Link>
        {hasPermission("production.board.read") ? (
          <Link className="ghost" to="/producao">
            Abrir produção
          </Link>
        ) : null}
        {hasPermission("costing.read") ? (
          <Link className="ghost" to="/gestao/custos">
            Abrir custos e preços
          </Link>
        ) : null}
        <Link className="ghost" to="/gestao/relatorios">
          Ver todas as pendências
        </Link>
      </footer>
    </div>
  );
}
