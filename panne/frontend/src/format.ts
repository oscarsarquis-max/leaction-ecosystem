import { SURFACE_ENUM_LABEL } from "./language/surface";

const dateTime = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
});

const dateOnly = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" });

export function formatDecimal(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  if (!/^-?\d+(?:\.\d+)?$/.test(value)) return value;
  const negative = value.startsWith("-");
  const raw = negative ? value.slice(1) : value;
  const [whole, fraction = ""] = raw.split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const trimmed = fraction.replace(/0+$/, "");
  const formatted = trimmed ? `${grouped},${trimmed}` : grouped;
  return negative ? `−${formatted}` : formatted;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return dateTime.format(parsed);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split("-");
    return `${day}/${month}/${year}`;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return dateOnly.format(parsed);
}

export function formatContextDate(value: string | null | undefined): string {
  if (!value) return "—";
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return formatDate(value);
  const months = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  return `${Number(match[3])} ${months[Number(match[2]) - 1]} ${match[1]}`;
}

export function todayIso(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

/** Data inicial do Quadro: âncora do cenário no modo demo; senão, data operacional local. */
export function boardDefaultOperationalDate(
  demoMode: boolean,
  demoAnchorDate: string,
  today: string = todayIso(),
): string {
  if (demoMode && /^\d{4}-\d{2}-\d{2}$/.test(demoAnchorDate)) return demoAnchorDate;
  return today;
}

/** Alvo operacional com unidade explícita (massa em g; unidades em un). */
export function formatTargetQuantity(
  quantity: string | null | undefined,
  targetMode: string | null | undefined,
): string {
  const amount = formatDecimal(quantity);
  if (amount === "—") return amount;
  if (targetMode === "mass") return `${amount} g`;
  if (targetMode === "units") return `${amount} un`;
  if (targetMode) return `${amount} ${targetMode}`;
  return amount;
}

/**
 * Prioridade de item/ordem: inteiro 1–99 (padrão 50).
 * Sem faixas canônicas Alta/Média/Baixa no contrato — expor como ordem relativa.
 */
export function formatProcessingOrder(priority: number | null | undefined): string {
  if (priority == null || !Number.isFinite(priority)) return "—";
  return `${priority} · relativa (1–99; padrão 50)`;
}

export const PROCESSING_ORDER_HELP =
  "Valor relativo de 1 a 99 (padrão 50). Não há faixas Alta/Média/Baixa no contrato operacional.";


export const STATUS_LABEL: Record<string, string> = {
  draft: "Rascunho",
  scheduled: "Programada",
  released: "Liberada",
  in_weighing: "Em pesagem",
  ready: "Pronta",
  in_progress: "Em execução",
  on_hold: "Em espera",
  completed: "Concluída",
  short_closed: "Encerrada parcial",
  cancelled: "Cancelada",
  open: "Aberta",
  resolved: "Resolvida",
  accepted: "Aceita",
  rejected: "Rejeitada",
  available: "Disponível",
  posted: "Lançado",
  approved: "Aprovado",
  issued: "Emitido",
  received: "Recebido",
  reserved: "Reservado",
  closed: "Encerrado",
  partial: "Parcial",
  partially_received: "Recebido em parte",
  submitted: "Enviado",
  converted: "Convertido",
  counting: "Em contagem",
  review: "Em revisão",
  blocked: "Bloqueado",
  expired: "Vencido",
  failed: "Falhou",
  quarantined: "Em quarentena",
  confirmed: "Confirmado",
  published: "Publicada",
  active: "Ativo",
  inactive: "Inativo",
  planned: "Planejada",
  retired: "Aposentado",
};

export const YIELD_LABEL: Record<string, string> = {
  pre_bake_mass: "Massa pré-forno",
  post_bake_mass: "Massa pós-forno",
  good_units: "Unidades boas",
  rejected_units: "Unidades rejeitadas",
  leftover: "Sobra",
  scrap: "Descarte",
  other: "Outro",
};

export const OCCURRENCE_LABEL: Record<string, string> = {
  material: "Material",
  substitution: "Substituição",
  equipment: "Equipamento",
  quality: "Qualidade",
  process: "Processo",
  safety: "Segurança",
  allergen: "Alergênico",
  time: "Tempo",
  temperature: "Temperatura",
  other: "Outro",
};

export const SEVERITY_LABEL: Record<string, string> = {
  low: "Baixa",
  medium: "Média",
  high: "Alta",
  critical: "Crítica",
};

export const CONSUMPTION_LABEL: Record<string, string> = {
  consume: "Consumo",
  return: "Retorno",
  waste: "Desperdício",
  correction: "Correção",
};

export const WEIGH_STATE_LABEL: Record<string, string> = {
  pending: "Pendente",
  recorded: "Registrada",
  awaiting_verification: "Aguardando conferência",
  accepted: "Aceita",
  rejected: "Rejeitada",
};

export const ACTION_LABEL: Record<string, string> = {
  schedule_order: "Programar ordem",
  release_order: "Liberar ordem",
  adopt_execution_policy: "Adotar política",
  open_weighing_session: "Abrir pesagem",
  record_weighing: "Registrar pesagem",
  start_step: "Iniciar etapa",
  complete_step: "Concluir etapa",
  resume_order: "Retomar ordem",
};

export const SHIFT_LABEL: Record<string, string> = {
  morning: "Manhã",
  afternoon: "Tarde",
  night: "Noite",
};

export function statusLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return STATUS_LABEL[value] ?? SURFACE_ENUM_LABEL[value] ?? value;
}

export function actionLabel(value: string | null | undefined): string {
  if (!value) return "Nenhuma ação de leitura";
  return ACTION_LABEL[value] ?? value;
}

export function shiftLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return SHIFT_LABEL[value] ?? SURFACE_ENUM_LABEL[value] ?? value;
}

export function catalogLabel(map: Record<string, string>, value: string | null | undefined): string {
  if (!value) return "—";
  return map[value] ?? value;
}
