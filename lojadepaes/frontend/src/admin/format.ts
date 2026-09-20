import { bakeryTimeZone } from "./api";
import type { FinancialKind, Money } from "./types";

const STATUS_LABELS: Record<string, string> = {
  draft: "Rascunho",
  confirmed: "Confirmado",
  in_production: "Em produção",
  ready: "Pronto",
  completed: "Concluído",
  cancelled: "Cancelado",
};

const MODALITY_LABELS: Record<string, string> = {
  pickup: "Retirada",
  delivery: "Entrega",
};

const FINANCIAL_LABELS: Record<FinancialKind, string> = {
  none: "Sem registro financeiro",
  unknown: "Financeiro indefinido",
  open: "Há registros, sem quitação conferida",
  settled: "Quitação conferida (regra interna)",
};

const PAYMENT_LABELS: Record<string, string> = {
  pending: "Pendente",
  paid: "Pago (registro)",
  failed: "Falhou",
  cancelled: "Cancelado (registro)",
  partially_refunded: "Estorno parcial",
  refunded: "Estornado",
  unknown: "Desconhecido",
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export function modalityLabel(value: string | null): string {
  if (!value) {
    return "Não informado";
  }
  return MODALITY_LABELS[value] ?? value;
}

export function financialKindLabel(kind: FinancialKind): string {
  return FINANCIAL_LABELS[kind];
}

export function paymentStatusLabel(status: string): string {
  return PAYMENT_LABELS[status] ?? status;
}

export function formatMoney(money: Money | null | undefined): string {
  if (!money || money.cents === null || money.cents === undefined) {
    return "Não calculado";
  }
  return (money.cents / 100).toLocaleString("pt-BR", {
    style: "currency",
    currency: money.currency || "BRL",
  });
}

export function formatCents(cents: number | null, currency = "BRL"): string {
  if (cents === null) {
    return "Não calculado";
  }
  return (cents / 100).toLocaleString("pt-BR", { style: "currency", currency });
}

export function formatDateTime(value: string | null): string {
  if (!value) {
    return "—";
  }
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: bakeryTimeZone(),
  }).format(new Date(value));
}
