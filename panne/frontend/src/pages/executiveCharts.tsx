import { Component, useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { DashboardChart, DashboardChartSeries, DashboardCharts } from "../api/types";
import { ChartTable } from "../costing/charts";
import { formatDate, formatDateTime, shiftLabel } from "../format";
import { formatPercentDisplay } from "../language/costing";
import {
  costStatusLabel,
  countLabel,
  dashboardCoverageLabel,
  dashboardQuantityLabel,
  splitAgendaLabel,
} from "../language/dashboard";
import { formatMoneyAmount } from "../language/ingredients";
import { EXEC_LIMITS } from "./executiveLimits";

export const PERIOD_OPTIONS = [
  { code: "today", label: "Hoje" },
  { code: "yesterday", label: "Ontem" },
  { code: "last_7_days", label: "Últimos 7 dias" },
] as const;

export type DashboardPeriod = (typeof PERIOD_OPTIONS)[number]["code"];

function parseAmount(value: string | number | null | undefined): number | null {
  if (value == null || value === "") return null;
  const n = Number(String(value).replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

function qty(value: string | number | null | undefined, unit?: string | null): string {
  return dashboardQuantityLabel(value, unit);
}

function money(value: string | number | null | undefined, currency = "BRL"): string {
  return formatMoneyAmount(value == null ? null : String(value), currency);
}

function toneClass(status?: string | null): string {
  if (!status) return "exec-tone--info";
  if (["conforme", "done", "complete"].includes(status)) return "exec-tone--ok";
  if (["perda", "incompleto", "abaixo", "validade", "partial", "released", "running"].includes(status)) {
    return "exec-tone--warn";
  }
  if (["ruptura", "blocked", "empty"].includes(status)) return "exec-tone--bad";
  if (["sem_medicao", "planned"].includes(status)) return "exec-tone--void";
  return "exec-tone--info";
}

function metaLine(chart: DashboardChart, charts: DashboardCharts): string {
  const meta = charts.meta;
  return [
    meta.period_label,
    chart.unit || "Unidade por item",
    meta.establishment || "Todos os estabelecimentos",
    chart.source,
    `Atualizado em ${formatDate(meta.as_of)}`,
    dashboardCoverageLabel(chart.coverage),
  ].join(" · ");
}

function isPurchasedRow(row: DashboardChartSeries): boolean {
  return String(row.supply_mode || "") === "purchased" || /comprado/i.test(String(row.label || ""));
}

export function PeriodFilter({
  value,
  onChange,
  id,
}: {
  value: string;
  onChange: (period: DashboardPeriod) => void;
  id: string;
}) {
  return (
    <fieldset className="exec-period" id={id}>
      <legend className="visually-hidden">Período dos gráficos</legend>
      {PERIOD_OPTIONS.map((option) => (
        <label key={option.code} className={value === option.code ? "is-on" : undefined}>
          <input
            type="radio"
            name={id}
            value={option.code}
            checked={value === option.code}
            onChange={() => onChange(option.code)}
          />
          {option.label}
        </label>
      ))}
    </fieldset>
  );
}

export class ChartGuard extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return <p className="meta">Este recorte não pôde ser apresentado. O restante do painel segue disponível.</p>;
    }
    return this.props.children;
  }
}

function ChartShell({
  chart,
  charts,
  conclusion,
  children,
  table,
  actionHref,
  actionLabel,
  allowToggle = true,
  compactEmpty = false,
}: {
  chart: DashboardChart;
  charts: DashboardCharts;
  conclusion: string;
  children: ReactNode;
  table: { headers: string[]; rows: ReactNode[][]; caption: string };
  actionHref?: string;
  actionLabel?: string;
  allowToggle?: boolean;
  compactEmpty?: boolean;
}) {
  const [showTable, setShowTable] = useState(false);
  const emptyAction = chart.empty_href && chart.empty_action ? (
    <Link className="ghost" to={chart.empty_href}>
      {chart.empty_action}
    </Link>
  ) : null;

  if (!chart.available && compactEmpty) {
    return (
      <figure className="exec-panel exec-panel--compact-empty">
        <figcaption>
          <h2>{chart.title}</h2>
        </figcaption>
        <div className="exec-empty exec-empty--compact">
          <p>Não há movimentações neste período</p>
          <p className="meta">{chart.empty_title || "O recorte ainda não tem recebimento, consumo, ajuste ou perda."}</p>
          {emptyAction}
        </div>
      </figure>
    );
  }

  return (
    <figure className="exec-panel">
      <figcaption className="exec-panel__head">
        <div>
          <h2>{chart.title}</h2>
          {chart.available ? <p className="exec-panel__conclusion">{conclusion}</p> : null}
        </div>
        {actionHref && actionLabel ? (
          <Link className="exec-panel__action" to={actionHref}>
            {actionLabel}
          </Link>
        ) : null}
      </figcaption>
      <details className="exec-panel__details">
        <summary>Fonte e cobertura</summary>
        <p className="meta exec-panel__meta">{metaLine(chart, charts)}</p>
        {chart.coverage_note ? <p className="meta">{chart.coverage_note}</p> : null}
      </details>
      {!chart.available ? (
        <div className="exec-empty exec-empty--compact">
          <p>{chart.empty_title || "Sem informação neste recorte."}</p>
          {emptyAction}
        </div>
      ) : (
        <>
          {allowToggle ? (
            <div className="exec-panel__tools">
              <button type="button" className="ghost" onClick={() => setShowTable((open) => !open)}>
                {showTable ? "Ver gráfico" : "Ver tabela"}
              </button>
            </div>
          ) : null}
          {showTable ? <ChartTable caption={table.caption} headers={table.headers} rows={table.rows} /> : children}
        </>
      )}
    </figure>
  );
}

export function ProductionChart({
  chart,
  charts,
}: {
  chart: DashboardChart;
  charts: DashboardCharts;
}) {
  const navigate = useNavigate();
  const visible = chart.series.slice(0, EXEC_LIMITS.production);
  const hidden = Math.max(0, chart.series.length - visible.length);
  const missing = visible.filter((row) => row.actual == null).length;
  const loss = visible.filter((row) => row.status === "perda").length;
  const conclusion = !chart.available
    ? chart.empty_title || "Ainda não há produção neste recorte."
    : missing
      ? `${countLabel(missing, "ordem sem medição", "ordens sem medição")}. A falta de medição não é produção zero.`
      : loss
        ? `${countLabel(loss, "ordem com perda registrada", "ordens com perda registrada")}.`
        : "Planejado e registrado no mesmo recorte, na unidade de cada ordem.";
  const nums = visible.flatMap((row) => [parseAmount(row.planned), parseAmount(row.actual)]).filter(
    (n): n is number => n != null,
  );
  const max = nums.length ? Math.max(...nums) : 1;

  return (
    <ChartShell
      chart={{ ...chart, title: "Produção planejada × registrada" }}
      charts={charts}
      conclusion={conclusion}
      actionHref={chart.board_href || "/producao"}
      actionLabel="Abrir produção"
      table={{
        caption: "Produção planejada e registrada",
        headers: ["Produto", "Ordem", "Planejado", "Registrado", "Situação"],
        rows: visible.map((row) => [
          <Link key={`${row.label}-n`} to={String(row.href || "/producao")}>
            {splitAgendaLabel(row.label).product === "—" ? row.label : splitAgendaLabel(row.label).product}
          </Link>,
          String(row.order_code || splitAgendaLabel(row.label).activity),
          qty(row.planned, row.unit),
          row.actual == null ? "Sem medição" : qty(row.actual, row.unit),
          String(row.status_label || "—"),
        ]),
      }}
    >
      <ul className="exec-prod" role="list">
        {visible.map((row, index) => {
          const planned = parseAmount(row.planned);
          const actual = parseAmount(row.actual);
          const names = splitAgendaLabel(row.label);
          const order = String(row.order_code || (/^(ORD|OP)-/i.test(names.product) ? names.product : names.activity));
          const product = names.activity !== order ? names.activity : names.product !== order ? names.product : row.label;
          return (
            <li key={`${row.label}-${row.order_code || index}`}>
              <button
                type="button"
                className="exec-prod__row"
                onClick={() => navigate(String(row.href || "/producao"))}
              >
                <span className="exec-prod__name">
                  <strong>{product}</strong>
                  <span className="meta">{order}</span>
                </span>
                <span className="exec-prod__track" aria-hidden="true">
                  {planned != null ? (
                    <span className="exec-prod__plan" style={{ width: `${Math.max(4, (planned / max) * 100)}%` }} />
                  ) : null}
                  {actual == null ? (
                    <span className="exec-prod__missing" title="Sem medição" />
                  ) : (
                    <span className="exec-prod__actual" style={{ width: `${Math.max(4, (actual / max) * 100)}%` }} />
                  )}
                </span>
                <span className="exec-prod__readout">
                  <span className={`exec-chip ${toneClass(String(row.status))}`}>{row.status_label}</span>
                  <span className="meta">
                    {qty(row.planned, row.unit)}
                    {" · "}
                    {actual == null ? "Sem medição" : qty(row.actual, row.unit)}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      <ul className="exec-legend">
        <li>
          <i className="exec-swatch exec-swatch--planned" aria-hidden="true" /> Planejado
        </li>
        <li>
          <i className="exec-swatch exec-swatch--actual" aria-hidden="true" /> Registrado
        </li>
        <li>
          <i className="exec-swatch exec-swatch--missing" aria-hidden="true" /> Sem medição
        </li>
      </ul>
      {hidden ? (
        <p className="meta">
          Mais {countLabel(hidden, "ordem fora desta faixa", "ordens fora desta faixa")}.{" "}
          <Link to="/producao">Abrir produção</Link>
        </p>
      ) : null}
    </ChartShell>
  );
}

export function MovementsChart({
  chart,
  charts,
}: {
  chart: DashboardChart;
  charts: DashboardCharts;
}) {
  const navigate = useNavigate();
  const keys = chart.keys || [];
  const nums = chart.series.flatMap((row) => keys.map((key) => parseAmount(row[key.code]))).filter(
    (n): n is number => n != null,
  );
  const max = nums.length ? Math.max(...nums) : 1;
  const conclusion = !chart.available
    ? chart.empty_title || "Ainda não há movimentação neste recorte."
    : `Eixo em ${chart.unit || "unidade dominante"}, sem misturar unidades.`;
  return (
    <ChartShell
      chart={chart}
      charts={charts}
      conclusion={conclusion}
      compactEmpty
      allowToggle={chart.available}
      actionHref="/componentes/estoque/movimentacoes"
      actionLabel="Abrir movimentações"
      table={{
        caption: "Entradas e saídas",
        headers: ["Dia", ...keys.map((key) => key.label), "Unidade"],
        rows: chart.series.map((row) => [
          formatDate(String(row.label)),
          ...keys.map((key) => (row[key.code] == null ? "Sem informação" : qty(row[key.code], row.unit))),
          String(row.unit || chart.unit || "—"),
        ]),
      }}
    >
      <div className="exec-grouped" role="img" aria-label={chart.title}>
        <ul className="exec-grouped__list exec-grouped__list--days">
          {chart.series.map((row) => (
            <li key={String(row.label)}>
              <button
                type="button"
                className="exec-grouped__hit"
                onClick={() => navigate(String(row.href || "/componentes/estoque/movimentacoes"))}
                title={`${formatDate(String(row.label))}: ${keys
                  .map((key) => `${key.label} ${row[key.code] == null ? "sem registro" : qty(row[key.code], row.unit)}`)
                  .join("; ")}`}
              >
                <span className="exec-grouped__pair exec-grouped__pair--multi" aria-hidden="true">
                  {keys.map((key) => {
                    const value = parseAmount(row[key.code]);
                    return value == null ? (
                      <span key={key.code} className={`exec-bar exec-bar--ghost exec-bar--${key.code}`} />
                    ) : (
                      <span
                        key={key.code}
                        className={`exec-bar exec-bar--${key.code}`}
                        style={{ height: `${Math.max(8, (value / max) * 100)}%` }}
                      />
                    );
                  })}
                </span>
                <strong>{formatDate(String(row.label))}</strong>
              </button>
            </li>
          ))}
        </ul>
        <ul className="exec-legend">
          {keys.map((key) => (
            <li key={key.code}>
              <i className={`exec-swatch exec-swatch--${key.code}`} aria-hidden="true" /> {key.label}
            </li>
          ))}
        </ul>
      </div>
    </ChartShell>
  );
}

export function AgendaPanel({
  chart,
}: {
  chart: DashboardChart;
}) {
  const visible = chart.series.slice(0, EXEC_LIMITS.agenda);
  const hidden = Math.max(0, chart.series.length - visible.length);
  return (
    <section className="exec-panel" aria-labelledby="exec-agenda-title">
      <div className="exec-panel__head">
        <div>
          <h2 id="exec-agenda-title">Agenda operacional</h2>
          <p className="exec-panel__conclusion">
            {chart.available
              ? "Próximas atividades, limitadas às cinco mais relevantes."
              : chart.empty_title || "Não há ordem neste recorte."}
          </p>
        </div>
        <Link className="exec-panel__action" to={chart.board_href || "/producao"}>
          Agenda completa
        </Link>
      </div>
      {!chart.available || !visible.length ? (
        <div className="exec-empty exec-empty--compact">
          <p>Nenhum registro na agenda deste recorte.</p>
          <Link className="ghost" to={chart.board_href || "/producao"}>
            Abrir quadro
          </Link>
        </div>
      ) : (
        <div className="exec-agenda-wrap">
          <table className="exec-agenda-table">
            <caption className="visually-hidden">Agenda operacional</caption>
            <thead>
              <tr>
                <th>Horário</th>
                <th>Atividade</th>
                <th>Produto</th>
                <th>Situação</th>
                <th>Ação</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => {
                const parts = splitAgendaLabel(row.label);
                return (
                  <tr key={row.label}>
                    <td>{shiftLabel(String(row.when_label || "")) || row.when_label || "—"}</td>
                    <td>{parts.activity}</td>
                    <td>{parts.product}</td>
                    <td>
                      <span className={`exec-chip ${toneClass(String(row.status))}`}>{row.status_label}</span>
                    </td>
                    <td>
                      <Link to={String(row.href || chart.board_href || "/producao")}>Abrir</Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {hidden ? (
            <p className="meta">
              Mais {countLabel(hidden, "item fora desta faixa", "itens fora desta faixa")}.{" "}
              <Link to={chart.board_href || "/producao"}>Abrir quadro</Link>
            </p>
          ) : null}
        </div>
      )}
    </section>
  );
}

function costRowTotal(row: DashboardChartSeries, keys: Array<{ code: string }>): number {
  return keys.reduce((sum, key) => sum + (parseAmount(row[key.code]) ?? 0), 0);
}

export function prioritizeCostRows(rows: DashboardChartSeries[], producedLabels: string[]): DashboardChartSeries[] {
  const rank = (row: DashboardChartSeries) => {
    if (row.completeness === "partial") return 0;
    if (row.completeness === "empty") return 1;
    if (producedLabels.some((label) => label.includes(row.label) || row.label.includes(label))) return 2;
    return 3;
  };
  return [...rows].sort((a, b) => rank(a) - rank(b));
}

export function CostsChart({
  chart,
  charts,
  producedLabels = [],
}: {
  chart: DashboardChart;
  charts: DashboardCharts;
  producedLabels?: string[];
}) {
  const navigate = useNavigate();
  const keys = chart.keys || [];
  const purchased = chart.series.filter(isPurchasedRow);
  const produced = prioritizeCostRows(chart.series.filter((row) => !isPurchasedRow(row)), producedLabels).slice(
    0,
    EXEC_LIMITS.costsProduced,
  );
  const purchasedVisible = purchased.slice(0, EXEC_LIMITS.costsPurchased);
  const scaleRows = produced.filter((row) => keys.some((key) => parseAmount(row[key.code]) != null));
  const max = scaleRows.reduce((current, row) => Math.max(current, costRowTotal(row, keys)), 0) || 1;
  const usedKeys = keys.filter((key) => produced.some((row) => parseAmount(row[key.code]) != null));
  const conclusion = !chart.available
    ? chart.empty_title || "Ainda não há formação de custo."
    : "Barras na mesma escala. Categoria ausente não entra como zero.";

  return (
    <ChartShell
      chart={chart}
      charts={charts}
      conclusion={conclusion}
      allowToggle={chart.available}
      actionHref="/gestao/custos"
      actionLabel="Analisar todos os custos"
      table={{
        caption: "Composição do custo",
        headers: ["Produto", ...keys.map((key) => key.label), "Situação"],
        rows: produced.map((row, index) => [
          <Link key={`${row.label}-${index}-n`} to={String(row.href || "/gestao/custos")}>
            {row.label}
          </Link>,
          ...keys.map((key) => (row[key.code] == null ? "Ausente" : money(row[key.code], String(row.currency || "BRL")))),
          costStatusLabel(String(row.completeness || ""), String(row.completeness_label || "")),
        ]),
      }}
    >
      <ul className="exec-stack" role="list">
        {produced.map((row, index) => {
          const parts = keys
            .map((key) => ({ key: key.code, label: key.label, value: parseAmount(row[key.code]) }))
            .filter((part) => part.value != null) as Array<{ key: string; label: string; value: number }>;
          const unitCost = parseAmount(row.unit_cost);
          return (
            <li key={`${row.label}-${index}`}>
              <button
                type="button"
                className="exec-stack__row"
                onClick={() => navigate(String(row.href || "/gestao/custos/formacao"))}
              >
                <span className="exec-stack__name">{row.label}</span>
                <span className="exec-stack__track" aria-hidden="true">
                  {parts.length ? (
                    parts.map((part) => (
                      <span
                        key={part.key}
                        className={`exec-stack__seg exec-stack__seg--${part.key}`}
                        style={{ width: `${(part.value / max) * 100}%` }}
                      />
                    ))
                  ) : (
                    <span className="exec-hbar__missing">Sem informação</span>
                  )}
                </span>
                <span className="exec-stack__readout">
                  <span className="meta">
                    {unitCost == null ? "—" : money(row.unit_cost, String(row.currency || "BRL"))}
                  </span>
                  <span className={`exec-chip ${toneClass(String(row.completeness))}`}>
                    {costStatusLabel(String(row.completeness || ""), String(row.completeness_label || ""))}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {usedKeys.length ? (
        <ul className="exec-legend">
          {usedKeys.map((key) => (
            <li key={key.code}>
              <i className={`exec-swatch exec-swatch--${key.code}`} aria-hidden="true" /> {key.label}
            </li>
          ))}
        </ul>
      ) : null}
      {purchasedVisible.length ? (
        <ul className="exec-purchase" aria-label="Produtos comprados">
          {purchasedVisible.map((row) => {
            const acquisition = parseAmount(row.unit_cost) ?? keys.map((key) => parseAmount(row[key.code])).find((n) => n != null);
            return (
              <li key={row.label}>
                <span>
                  <strong>Produto comprado</strong>
                  {" · "}
                  {row.label}
                </span>
                <strong>
                  {acquisition == null
                    ? "Aquisição sem valor conhecido"
                    : `Aquisição ${money(acquisition, String(row.currency || "BRL"))} por unidade`}
                </strong>
              </li>
            );
          })}
        </ul>
      ) : null}
      {purchased.length > purchasedVisible.length ? (
        <p className="meta">
          <Link to="/gestao/custos">Ver todos os custos de aquisição</Link>
        </p>
      ) : null}
    </ChartShell>
  );
}

export function PricesChart({
  chart,
  charts,
}: {
  chart: DashboardChart;
  charts: DashboardCharts;
}) {
  const navigate = useNavigate();
  const visible = chart.series.slice(0, EXEC_LIMITS.prices);
  const nums = visible.flatMap((row) => [parseAmount(row.cost), parseAmount(row.price)]).filter(
    (n): n is number => n != null,
  );
  const max = nums.length ? Math.max(...nums) : 1;
  const calculable = visible.filter((row) => row.margin != null).length;
  const conflicts = visible.filter((row) => row.status === "conflict").length;
  const conclusion = !chart.available
    ? chart.empty_title || "Não há preço vigente comparável."
    : conflicts
      ? `${countLabel(conflicts, "produto com conflito de preços vigentes", "produtos com conflito de preços vigentes")}. Sem escolha silenciosa.`
      : calculable
        ? `${countLabel(calculable, "produto com margem calculável", "produtos com margem calculável")}. Markup e margem não compartilham o eixo.`
        : "Há preço, mas a margem não é calculável sem base comercial comparável.";
  return (
    <ChartShell
      chart={chart}
      charts={charts}
      conclusion={conclusion}
      allowToggle={chart.available}
      actionHref="/gestao/custos/precos"
      actionLabel="Preços e histórico"
      table={{
        caption: "Preço, custo e margem",
        headers: ["Produto", "Custo", "Preço", "Margem", "Base"],
        rows: visible.map((row, index) => [
          <Link key={`${row.label}-${index}`} to={String(row.href || "/gestao/custos/precos")}>
            {row.label}
          </Link>,
          row.cost == null ? "Sem informação" : money(row.cost, String(row.currency || "BRL")),
          row.status === "conflict"
            ? "Conflito de preços vigentes"
            : row.price == null
              ? "Sem informação"
              : money(row.price, String(row.currency || "BRL")),
          row.status === "conflict" || row.margin == null ? "Não calculável" : formatPercentDisplay(String(row.margin)),
          row.basis === "conflito" ? "Conflito" : row.basis === "ausente" ? "Base ausente" : "Base informada",
        ]),
      }}
    >
      <ul className="exec-price" role="list">
        {visible.map((row, index) => {
          const cost = parseAmount(row.cost);
          const price = parseAmount(row.price);
          return (
            <li key={`${row.label}-${index}`}>
              <button
                type="button"
                className="exec-price__row"
                onClick={() => navigate(String(row.href || "/gestao/custos/precos"))}
              >
                <strong>{row.label}</strong>
                <span className="exec-price__axis" aria-hidden="true">
                  {cost == null ? (
                    <span className="exec-hbar__missing">Custo ausente</span>
                  ) : (
                    <span className="exec-hbar__fill exec-tone--info" style={{ width: `${Math.max(6, (cost / max) * 100)}%` }} />
                  )}
                  {price == null ? (
                    <span className="exec-hbar__missing">
                      {row.status === "conflict" ? "Conflito de preços vigentes" : "Preço ausente"}
                    </span>
                  ) : (
                    <span className="exec-hbar__fill exec-bar--planned" style={{ width: `${Math.max(6, (price / max) * 100)}%` }} />
                  )}
                </span>
                <span className="exec-price__margin">
                  {row.status === "conflict" ? (
                    <span className="exec-chip exec-tone--warn">Conflito de preços vigentes</span>
                  ) : row.margin == null ? (
                    <span className="exec-chip exec-tone--void">Não calculável</span>
                  ) : (
                    <span className="exec-chip exec-tone--ok">Margem {formatPercentDisplay(String(row.margin))}</span>
                  )}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      <ul className="exec-legend">
        <li>
          <i className="exec-swatch exec-swatch--info" aria-hidden="true" /> Custo
        </li>
        <li>
          <i className="exec-swatch exec-swatch--planned" aria-hidden="true" /> Preço
        </li>
        <li>Margem em faixa própria, não no eixo monetário</li>
      </ul>
    </ChartShell>
  );
}

export function chartUpdatedLine(charts: DashboardCharts): string {
  return `Atualizado em ${formatDateTime(charts.meta.generated_at)}`;
}
