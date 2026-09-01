import type { DashboardAttention, DashboardMetric, DashboardTask, DashboardToday } from "../api/types";
import { formatDate, formatDecimal } from "../format";
import { formatMoneyAmount } from "./ingredients";

export function dashboardMetricLabel(metric: DashboardMetric | null | undefined): string {
  if (!metric || !metric.available) return "Sem informação";
  if (metric.empty) return "Nenhum registro";
  if (metric.value == null || metric.value === "") return "Sem informação";
  if (metric.unit && /BRL|R\$/i.test(metric.unit)) {
    const rest = metric.unit.replace(/BRL/gi, "").replace(/\s+/g, " ").trim();
    return rest ? `${formatMoneyAmount(metric.value, "BRL")} ${rest}` : formatMoneyAmount(metric.value, "BRL");
  }
  const number = formatDecimal(metric.value);
  return metric.unit ? `${number} ${metric.unit}` : number;
}

export function dashboardPeriodLine(metric: DashboardMetric): string {
  const bits = [metric.period, metric.unit || null, metric.source].filter(Boolean);
  return bits.join(" · ");
}

export function dashboardDateLabel(iso: string | undefined): string {
  return formatDate(iso);
}

export function dashboardSeverityLabel(severity: string): string {
  if (severity === "high") return "Alta";
  if (severity === "medium") return "Média";
  return "Baixa";
}

export function dashboardQuantityLabel(value: string | number | null | undefined, unit?: string | null): string {
  if (value == null || value === "") return "Sem informação";
  const number = formatDecimal(String(value));
  return unit ? `${number} ${unit}` : number;
}

export function countLabel(count: number, singular: string, plural: string): string {
  if (count === 1) return `1 ${singular}`;
  return `${count} ${plural}`;
}

export function dashboardCoverageLabel(coverage: string | undefined): string {
  if (coverage === "complete") return "Cobertura completa";
  if (coverage === "partial") return "Cobertura parcial";
  if (coverage === "empty") return "Sem dados";
  return "Cobertura não informada";
}

export function dashboardMarginLabel(metric: DashboardMetric): string {
  if (!metric.available || metric.value == null) return "Sem informação";
  const ratio = Number(metric.value);
  if (!Number.isFinite(ratio)) return "Sem informação";
  return `${formatDecimal((ratio * 100).toFixed(1))} %`;
}

export function kpiComplement(metric: DashboardMetric, hint?: string): string {
  if (!metric.available) return "sem informação";
  if (metric.empty) return "nenhum registro";
  if (hint) return hint;
  return metric.period || "recorte informado";
}

export function metricIsPresent(metric: DashboardMetric | null | undefined): boolean {
  return Boolean(metric && metric.available && !metric.empty && metric.value != null && metric.value !== "");
}

export function executiveBrief(data: DashboardToday): { lead: string; causes: string; action: string; href: string } {
  const items = [...data.attentions, ...data.today.priority_tasks];
  const count = items.length;
  const lead =
    count === 0
      ? data.headline.situation
      : count === 1
        ? "O negócio pede uma decisão hoje."
        : `O negócio pede ${count} decisões hoje.`;
  const causes = data.attentions
    .slice(0, 3)
    .map((item) => item.title)
    .filter(Boolean)
    .join("; ");
  return {
    lead,
    causes,
    action: count ? "Ver prioridades" : data.headline.next_action || "Abrir fluxo",
    href: data.headline.next_href || data.attentions[0]?.href || "/fluxo",
  };
}

export function attentionConsequence(item: DashboardAttention | DashboardTask): string {
  if ("detail" in item && item.detail) {
    if (/mínimo|abaixo/i.test(item.detail) || item.code === "critical_stock") {
      return `${item.detail}. Avaliar compra ou recebimento.`;
    }
    return item.detail;
  }
  if ("severity" in item && item.severity === "high") return "Atraso que impede o andamento do turno.";
  return "Requer uma ação humana.";
}

export function splitAgendaLabel(label: string): { activity: string; product: string } {
  const parts = label.split(" · ").map((part) => part.trim()).filter(Boolean);
  if (parts.length >= 2) return { activity: parts[0], product: parts.slice(1).join(" · ") };
  return { activity: label, product: "—" };
}

export function costStatusLabel(completeness?: string | null, fallback?: string | null): string {
  if (completeness === "complete") return "Completo";
  if (completeness === "partial") return "Parcial";
  if (completeness === "empty") return "Sem informação";
  return fallback || "Sem informação";
}

export function yesterdaySummary(data: DashboardToday): { empty: boolean; line: string } {
  const rows: Array<[string, DashboardMetric]> = [
    ["produzido", data.yesterday.produced],
    ["recebido", data.yesterday.received],
    ["consumido", data.yesterday.consumed],
    ["perdas", data.yesterday.losses],
    ["ordens concluídas", data.yesterday.orders_completed],
  ];
  const present = rows.filter(([, metric]) => metricIsPresent(metric));
  if (!present.length) {
    return { empty: true, line: "Ontem — não há produção, recebimentos ou perdas registrados." };
  }
  return {
    empty: false,
    line: present.map(([name, metric]) => `${name} ${dashboardMetricLabel(metric)}`).join(" · "),
  };
}
