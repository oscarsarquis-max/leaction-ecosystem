/**
 * Gráficos gerenciais leves em SVG (sem dependência nova no Panne).
 * Ausência ≠ zero: itens sem valor não geram barra monetária.
 */
import type { ReactNode } from "react";
import { formatMoneyAmount } from "../language/ingredients";
import { formatPercentDisplay, varianceSignal } from "../language/costing";

export type ChartBar = {
  id?: string;
  label: string;
  amount: string | null;
  sharePercent?: string | null;
  state?: string;
  pattern?: "solid" | "hatched" | "outline";
};

function money(v: string | null | undefined, currency = "BRL") {
  return formatMoneyAmount(v, currency);
}

function parseAmount(v: string | null | undefined): number | null {
  if (v == null || v === "") return null;
  const n = Number(String(v).replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

export function HorizontalBars({
  title,
  caption,
  bars,
  currency = "BRL",
  onSelect,
  selectedId,
}: {
  title: string;
  caption?: string;
  bars: ChartBar[];
  currency?: string;
  onSelect?: (bar: ChartBar) => void;
  selectedId?: string | null;
}) {
  const valued = bars.map((b) => parseAmount(b.amount)).filter((n): n is number => n != null && n > 0);
  const max = valued.length ? Math.max(...valued) : 0;
  return (
    <figure className="cost-chart" aria-labelledby={`${title}-h`}>
      <figcaption>
        <h3 id={`${title}-h`}>{title}</h3>
        {caption ? <p className="meta">{caption}</p> : null}
      </figcaption>
      <ul className="cost-chart__bars" role="list">
        {bars.map((bar) => {
          const value = parseAmount(bar.amount);
          const missing = value == null;
          const width = missing || max <= 0 ? 0 : Math.max(4, (value / max) * 100);
          const pattern = missing ? "hatched" : bar.pattern || "solid";
          return (
            <li key={bar.id || bar.label} className={selectedId === bar.id ? "is-selected" : undefined}>
              <button
                type="button"
                className={`cost-chart__row cost-chart__row--${pattern}`}
                onClick={() => onSelect?.(bar)}
                aria-label={`${bar.label}: ${missing ? "Sem informação" : money(bar.amount, currency)}`}
              >
                <span className="cost-chart__label">{bar.label}</span>
                <span className="cost-chart__track" aria-hidden="true">
                  {missing ? (
                    <span className="cost-chart__missing">Sem informação</span>
                  ) : (
                    <span className="cost-chart__fill" style={{ width: `${width}%` }} />
                  )}
                </span>
                <span className="cost-chart__value">
                  {missing ? "—" : money(bar.amount, currency)}
                  {bar.sharePercent && !missing ? ` · ${formatPercentDisplay(bar.sharePercent)}` : ""}
                  {bar.state ? ` · ${bar.state}` : ""}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </figure>
  );
}

export function WaterfallBars({
  title,
  steps,
  currency = "BRL",
}: {
  title: string;
  steps: Array<{ label: string; amount: string | null; running_total?: string | null; state?: string }>;
  currency?: string;
}) {
  const totals = steps
    .map((s) => parseAmount(s.running_total) ?? parseAmount(s.amount))
    .filter((n): n is number => n != null);
  const max = totals.length ? Math.max(...totals) : 0;
  let cursor = 0;
  return (
    <figure className="cost-chart cost-chart--waterfall" aria-labelledby={`${title}-w`}>
      <figcaption>
        <h3 id={`${title}-w`}>{title}</h3>
        <p className="meta">Como se chega ao total a partir das parcelas conhecidas.</p>
      </figcaption>
      <svg viewBox={`0 0 640 ${Math.max(120, steps.length * 36 + 24)}`} role="img" aria-label={title}>
        {steps.map((step, index) => {
          const y = 16 + index * 36;
          const amount = parseAmount(step.amount);
          const isTotal = step.state === "total";
          const missing = amount == null && !isTotal;
          let x = 120;
          let w = 0;
          if (isTotal && amount != null && max > 0) {
            x = 120;
            w = (amount / max) * 480;
            cursor = amount;
          } else if (amount != null && max > 0) {
            x = 120 + (cursor / max) * 480;
            w = (amount / max) * 480;
            cursor += amount;
          }
          return (
            <g key={`${step.label}-${index}`}>
              <text x={8} y={y + 14} className="cost-chart__svg-label">
                {step.label}
              </text>
              {missing ? (
                <text x={130} y={y + 14} className="cost-chart__svg-missing">
                  Sem informação
                </text>
              ) : (
                <rect
                  x={x}
                  y={y}
                  width={Math.max(w, 2)}
                  height={22}
                  className={isTotal ? "cost-chart__svg-total" : "cost-chart__svg-step"}
                  rx={3}
                />
              )}
              <text x={610} y={y + 14} textAnchor="end" className="cost-chart__svg-value">
                {missing ? "—" : money(step.amount, currency)}
              </text>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}

export function GroupedCompare({
  title,
  series,
  currency = "BRL",
}: {
  title: string;
  series: Array<{
    label: string;
    planned: string | null;
    actual: string | null;
    metric?: "cost" | "yield";
    delta?: string | null;
  }>;
  currency?: string;
}) {
  const nums = series.flatMap((s) => [parseAmount(s.planned), parseAmount(s.actual)]).filter((n): n is number => n != null);
  const max = nums.length ? Math.max(...nums, 0.01) : 1;
  return (
    <figure className="cost-chart" aria-labelledby={`${title}-g`}>
      <figcaption>
        <h3 id={`${title}-g`}>{title}</h3>
        <p className="meta">Barras ausentes = Sem informação (não são zero).</p>
      </figcaption>
      <ul className="cost-chart__grouped" role="list">
        {series.map((row) => {
          const p = parseAmount(row.planned);
          const a = parseAmount(row.actual);
          const signal = varianceSignal(row.metric ?? "cost", row.planned, row.actual);
          const deltaText =
            signal.delta == null
              ? "Sem informação"
              : row.metric === "yield"
                ? `${signal.delta > 0 ? "+" : ""}${signal.delta} un. · ${signal.label}`
                : `${money(String(signal.delta), currency)} · ${signal.label}`;
          return (
            <li key={row.label}>
              <div className="cost-chart__group-label">{row.label}</div>
              <div className="cost-chart__group-tracks">
                <div className="cost-chart__group-line">
                  <span>previsto</span>
                  {p == null ? (
                    <em>Sem informação</em>
                  ) : (
                    <span className="cost-chart__fill cost-chart__fill--planned" style={{ width: `${(p / max) * 100}%` }} />
                  )}
                  <strong>{p == null ? "—" : money(row.planned, currency)}</strong>
                </div>
                <div className="cost-chart__group-line">
                  <span>realizado</span>
                  {a == null ? (
                    <em>Sem informação</em>
                  ) : (
                    <span className="cost-chart__fill cost-chart__fill--actual" style={{ width: `${(a / max) * 100}%` }} />
                  )}
                  <strong>{a == null ? "—" : money(row.actual, currency)}</strong>
                </div>
              </div>
              <p className="meta">Avaliação: {deltaText}</p>
            </li>
          );
        })}
      </ul>
    </figure>
  );
}

export function ScenarioImpact({
  title,
  cost,
  currentPrice,
  simulatedPrice,
  currentMarginPct,
  simulatedMarginPct,
  currency = "BRL",
}: {
  title: string;
  cost: string | null;
  currentPrice: string | null;
  simulatedPrice: string | null;
  currentMarginPct: string | null;
  simulatedMarginPct: string | null;
  currency?: string;
}) {
  const values = [cost, currentPrice, simulatedPrice].map(parseAmount);
  const max = Math.max(...values.filter((n): n is number => n != null && n > 0), 0.01);
  const rows: Array<{ label: string; value: string | null; tone: string }> = [
    { label: "Custo-base", value: cost, tone: "cost" },
    { label: "Preço atual", value: currentPrice, tone: "current" },
    { label: "Preço simulado", value: simulatedPrice, tone: "sim" },
  ];
  return (
    <figure className="cost-chart" aria-labelledby={`${title}-s`}>
      <figcaption>
        <h3 id={`${title}-s`}>{title}</h3>
        <p className="meta">Eixo monetário separado do eixo de margem.</p>
      </figcaption>
      <ul className="cost-chart__bars" role="list">
        {rows.map((row) => {
          const n = parseAmount(row.value);
          return (
            <li key={row.label}>
              <div className="cost-chart__row">
                <span className="cost-chart__label">{row.label}</span>
                <span className="cost-chart__track" aria-hidden="true">
                  {n == null ? (
                    <span className="cost-chart__missing">Sem informação</span>
                  ) : (
                    <span className={`cost-chart__fill cost-chart__fill--${row.tone}`} style={{ width: `${(n / max) * 100}%` }} />
                  )}
                </span>
                <span className="cost-chart__value">{n == null ? "—" : money(row.value, currency)}</span>
              </div>
            </li>
          );
        })}
      </ul>
      <dl className="cost-chart__margin-band">
        <div>
          <dt>Margem atual</dt>
          <dd>{formatPercentDisplay(currentMarginPct)}</dd>
        </div>
        <div>
          <dt>Margem simulada</dt>
          <dd>{formatPercentDisplay(simulatedMarginPct)}</dd>
        </div>
      </dl>
    </figure>
  );
}

export function ChartTable({
  caption,
  headers,
  rows,
}: {
  caption: string;
  headers: string[];
  rows: ReactNode[][];
}) {
  return (
    <div className="cost-chart__table-wrap">
      <table className="cost-chart__table">
        <caption>{caption}</caption>
        <thead>
          <tr>
            {headers.map((h) => (
              <th key={h} scope="col">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={idx}>
              {row.map((cell, cidx) => (
                <td key={cidx}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
