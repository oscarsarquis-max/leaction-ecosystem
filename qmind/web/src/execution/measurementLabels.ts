/**
 * Plain-language vocabulary for evidence and result measurement (ISOI-008).
 *
 * Decimal values arrive from the API as strings and stay strings: an indicator
 * is audit evidence, so `Number()` never touches a value on its way to screen.
 */
import type {
  BaselineStatus,
  EvidenceStatus,
  IndicatorDirection,
  IndicatorUnitKind,
  MeasurementPosture,
  SubstantiationLevel,
  TargetEvaluationState,
  TargetPosture,
} from "@/execution/api";

/**
 * Said on every screen that shows a target, and repeated in the efficacy step:
 * the number is an input to the human decision, never the decision itself.
 */
export const TARGET_NOT_EFFICACY_WARNING =
  "Meta atingida não equivale, por si só, à eficácia confirmada.";

export const MEASUREMENT_POSTURE_LABELS: Record<MeasurementPosture, string> = {
  not_planned: "Sem medição planejada",
  awaiting_baseline: "Falta ponto de partida",
  awaiting_measurement: "Aguardando medição",
  on_time: "Medição em dia",
  overdue: "Medição atrasada",
};

export const TARGET_POSTURE_LABELS: Record<TargetPosture, string> = {
  unknown: "Meta ainda sem resposta",
  met: "Meta atingida",
  not_met: "Meta não atingida",
  mixed: "Metas com resultados diferentes",
};

export const TARGET_STATE_LABELS: Record<TargetEvaluationState, string> = {
  not_planned: "Sem medição planejada",
  awaiting_baseline: "Falta ponto de partida",
  awaiting_measurement: "Aguardando primeira medição",
  on_track: "Em andamento",
  target_met: "Meta atingida",
  target_not_met: "Meta não atingida no prazo",
  inconclusive: "Sem meta definida",
};

export const SUBSTANTIATION_LABELS: Record<SubstantiationLevel, string> = {
  none: "Sem documento que sustente o número",
  partial: "Documento anexado, ainda não aprovado",
  verified: "Sustentado por documento aprovado",
};

export const INDICATOR_DIRECTION_LABELS: Record<IndicatorDirection, string> = {
  higher_is_better: "Quanto maior, melhor",
  lower_is_better: "Quanto menor, melhor",
  within_range: "Precisa entrar em uma faixa",
  maintain_range: "Precisa continuar dentro da faixa",
};

/** Directions whose target is a range instead of a single number. */
export function isRangeDirection(direction: IndicatorDirection): boolean {
  return direction === "within_range" || direction === "maintain_range";
}

export const BASELINE_STATUS_LABELS: Record<BaselineStatus, string> = {
  missing: "Ponto de partida ainda não registrado",
  unavailable_justified: "Ponto de partida indisponível, com justificativa",
  recorded: "Ponto de partida registrado",
};

/**
 * How the unit reads in a form. The server also sends `unit_label` ready for
 * display; these labels are for choosing the kind before the indicator exists.
 */
export const UNIT_KIND_LABELS: Record<IndicatorUnitKind, string> = {
  percentage: "Porcentagem (%)",
  count: "Contagem (ocorrências, peças…)",
  currency: "Valor em dinheiro",
  ratio: "Proporção",
  score: "Pontuação",
  duration_minutes: "Duração em minutos",
  duration_hours: "Duração em horas",
  duration_days: "Duração em dias",
  dimensionless: "Número sem unidade",
  custom: "Outra unidade (descrever)",
};

export const EVIDENCE_STATUS_LABELS: Record<EvidenceStatus, string> = {
  upload_pending: "Envio em andamento",
  quarantined: "Recebida, aguardando verificação",
  rejected: "Recusada na verificação",
  approved: "Aprovada",
  superseded: "Substituída por versão mais recente",
  pending_disposal: "Marcada para descarte",
  disposed: "Descartada",
};

/** Postures worth a coloured badge — everything else stays neutral. */
export function measurementPostureTone(
  posture: MeasurementPosture,
): "danger" | "warn" | "muted" | "ok" {
  if (posture === "overdue") return "danger";
  if (posture === "awaiting_baseline" || posture === "awaiting_measurement") {
    return "warn";
  }
  if (posture === "on_time") return "ok";
  return "muted";
}

export function targetPostureTone(
  posture: TargetPosture,
): "danger" | "warn" | "muted" | "ok" {
  if (posture === "not_met") return "danger";
  if (posture === "mixed") return "warn";
  if (posture === "met") return "ok";
  return "muted";
}

const CONTENT_TYPE_LABELS: [RegExp, string][] = [
  [/^application\/pdf$/, "Documento PDF"],
  [/^image\//, "Imagem"],
  [/^video\//, "Vídeo"],
  [/^audio\//, "Áudio"],
  [/spreadsheet|excel|^text\/csv$/, "Planilha"],
  [/wordprocessing|msword/, "Documento de texto"],
  [/presentation|powerpoint/, "Apresentação"],
  [/^text\//, "Arquivo de texto"],
];

/** What kind of file this is, in words — never the storage key or the id. */
export function evidenceTypeLabel(contentType: string | null | undefined): string {
  const value = (contentType ?? "").trim().toLowerCase();
  if (!value) return "Arquivo";
  for (const [pattern, label] of CONTENT_TYPE_LABELS) {
    if (pattern.test(value)) return label;
  }
  return "Arquivo";
}

export function formatByteSize(bytes: number | null | undefined): string {
  if (bytes == null || !Number.isFinite(bytes)) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * The value exactly as the server stated it, with the unit appended.
 * No parsing, no rounding: a currency or a rate must read the same on screen
 * as it does in the record behind it.
 */
export function formatMeasurementValue(
  value: string | number | null | undefined,
  unit?: string | null,
): string {
  if (value === null || value === undefined || value === "") return "—";
  const text = typeof value === "string" ? value : String(value);
  const suffix = (unit ?? "").trim();
  return suffix ? `${text} ${suffix}` : text;
}

/** How the target reads for a person: a single number, or a range. */
export function formatTarget(
  target: {
    target_value?: string | null;
    target_min?: string | null;
    target_max?: string | null;
  },
  unit?: string | null,
): string {
  if (target.target_value != null && target.target_value !== "") {
    return formatMeasurementValue(target.target_value, unit);
  }
  if (target.target_min != null && target.target_max != null) {
    return `${formatMeasurementValue(target.target_min, unit)} a ${formatMeasurementValue(
      target.target_max,
      unit,
    )}`;
  }
  return "Sem meta definida";
}

export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
