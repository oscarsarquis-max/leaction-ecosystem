import { bakeryTimeZone } from "./api";
import type { FinancialKind, Money } from "./types";

const STATUS_LABELS: Record<string, string> = {
  draft: "Rascunho",
  submitted: "Solicitado",
  confirmed: "Confirmado",
  in_production: "Em produção",
  ready: "Pronto — aguardando confirmação de entrega",
  completed: "Finalizado",
  cancelled: "Cancelado",
  pending: "Aguardando resposta",
  alternative_proposed: "Alternativa proposta",
  awaiting_details: "Aguardando dados",
  converted: "Convertida em pedido",
  closed: "Encerrada",
};

const MODALITY_LABELS: Record<string, string> = {
  pickup: "Retirada (histórico)",
  delivery: "Entrega",
};

const FINANCIAL_LABELS: Record<FinancialKind, string> = {
  none: "Pagamento: Sem cobrança",
  unknown: "Pagamento: Aguardando confirmação",
  open: "Pagamento: Em aberto",
  settled: "Pagamento: Pago",
};

const PAYMENT_LABELS: Record<string, string> = {
  pending: "Pendente",
  paid: "Pago",
  failed: "Falhou",
  cancelled: "Cancelado (registro)",
  partially_refunded: "Estorno parcial",
  refunded: "Estornado",
  unknown: "Desconhecido",
};

export function statusLabel(status: string, _modality?: string | null): string {
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

export function paes(amount: number): string {
  return amount === 1 ? "1 pão" : `${amount} pães`;
}

export function itens(amount: number): string {
  return amount === 1 ? "1 item" : `${amount} itens`;
}

export function formatShortDay(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const day = value.length === 10 ? `${value}T12:00:00` : value;
  const date = new Date(day);
  const weekday = new Intl.DateTimeFormat("pt-BR", { weekday: "short", timeZone: bakeryTimeZone() })
    .format(date)
    .replace(".", "")
    .toLowerCase();
  const dm = new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    timeZone: bakeryTimeZone(),
  }).format(date);
  return `${weekday}, ${dm}`;
}

export function formatDay(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const day = value.length === 10 ? `${value}T12:00:00` : value;
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeZone: bakeryTimeZone(),
  }).format(new Date(day));
}

export function pendingAgeLabel(hours: number | null | undefined): string | null {
  if (hours === null || hours === undefined) {
    return null;
  }
  if (hours < 1) {
    return "pendente há menos de 1 h";
  }
  return `pendente há ${hours} h`;
}

export function notificationStatusLabel(status: string): string {
  if (status === "pending") {
    return "Envio pendente";
  }
  if (status === "sent") {
    return "Aceito pelo serviço de e-mail — não comprova entrega na caixa";
  }
  if (status === "failed") {
    return "Falha no envio";
  }
  if (status === "skipped") {
    return "Resposta registrada; envio não disparado";
  }
  return status;
}
