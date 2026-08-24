import type {
  ActionItemStatus,
  ActionKind,
  AgileRole,
  BoardColumnKey,
  CardPriority,
  CeremonyType,
  CheckInHealth,
  ImpedimentSeverity,
  SprintStatus,
} from "@/execution/api";

export const BOARD_COLUMN_LABELS: Record<BoardColumnKey, string> = {
  backlog: "Backlog",
  selected: "Selecionado",
  in_progress: "Em execução",
  implemented: "Aguardando validação",
  validated: "Aguardando eficácia",
  ineffective: "Requer revisão",
  done: "Concluído",
};

export const BOARD_COLUMN_ORDER: BoardColumnKey[] = [
  "backlog",
  "selected",
  "in_progress",
  "implemented",
  "validated",
  "ineffective",
  "done",
];

export const ACTION_KIND_LABELS: Record<ActionKind, string> = {
  correction: "Correção",
  corrective_action: "Ação corretiva",
  improvement: "Melhoria",
};

export const PRIORITY_LABELS: Record<CardPriority, string> = {
  critical: "Crítica",
  high: "Alta",
  medium: "Média",
  low: "Baixa",
};

export const STATUS_LABELS: Record<ActionItemStatus, string> = {
  open: "Aberta",
  in_progress: "Em execução",
  implemented: "Implementada",
  validated: "Validada",
  done: "Concluída",
  ineffective: "Ineficaz",
  cancelled: "Cancelada",
  ineffective_closed: "Encerrada (ineficaz)",
};

export const SPRINT_STATUS_LABELS: Record<SprintStatus, string> = {
  planned: "Planejada",
  active: "Ativa",
  completed: "Concluída",
  cancelled: "Cancelada",
};

export const AGILE_ROLE_LABELS: Record<AgileRole, string> = {
  value_owner: "Dono de valor",
  facilitator: "Facilitador",
  execution_member: "Membro de execução",
  stakeholder: "Stakeholder",
};

export const CHECKIN_HEALTH_LABELS: Record<CheckInHealth, string> = {
  on_track: "No trilho",
  attention: "Precisa de atenção",
  blocked: "Bloqueado",
};

export const IMPEDIMENT_SEVERITY_LABELS: Record<ImpedimentSeverity, string> = {
  low: "Baixa",
  medium: "Média",
  high: "Alta",
  critical: "Crítica",
};

export const CEREMONY_TYPE_LABELS: Record<CeremonyType, string> = {
  sprint_planning: "Planejamento da sprint",
  daily_check_in: "Check-in diário",
  sprint_review: "Revisão da sprint",
  retrospective: "Retrospectiva",
};

/** Mirrors backend agile.schemas.CHECK_IN_STALE_WINDOW_HOURS. */
export const STALE_CHECK_IN_HOURS = 72;

export function formatShortDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" }).format(
      new Date(iso),
    );
  } catch {
    return iso;
  }
}

export function formatRelativeAge(iso: string | null | undefined): string {
  if (!iso) return "Sem check-in";
  const ms = Date.now() - Date.parse(iso);
  if (Number.isNaN(ms)) return "Sem check-in";
  const days = Math.floor(ms / (24 * 60 * 60 * 1000));
  if (days <= 0) return "Hoje";
  if (days === 1) return "Há 1 dia";
  return `Há ${days} dias`;
}

export function isCheckInStale(
  iso: string | null | undefined,
  windowHours: number = STALE_CHECK_IN_HOURS,
): boolean {
  if (!iso) return true;
  const ms = Date.now() - Date.parse(iso);
  if (Number.isNaN(ms)) return true;
  return ms > windowHours * 60 * 60 * 1000;
}

export function originLinkLabel(card: {
  improvement_case_id?: string | null;
  assessment_id?: string | null;
}): { label: string; href: string | null } {
  if (card.improvement_case_id) {
    return {
      label: "Caso de melhoria",
      href: `/improvement-cases/${card.improvement_case_id}`,
    };
  }
  if (card.assessment_id) {
    return {
      label: "Avaliação",
      href: `/assessments/${card.assessment_id}`,
    };
  }
  return { label: "Plano de ação", href: null };
}

/**
 * Where to review the QMind analysis that produced this card.
 * Deep-links to the originating finding when the code is known.
 */
export function analysisProvenanceLink(card: {
  improvement_case_id?: string | null;
  source_analysis_run_id?: string | null;
  source_finding_code?: string | null;
}): { label: string; href: string } | null {
  if (!card.source_analysis_run_id || !card.improvement_case_id) return null;
  const anchor = card.source_finding_code
    ? `#ic-finding-anchor-${card.source_finding_code}`
    : "";
  const label = card.source_finding_code
    ? `Rever análise (achado ${card.source_finding_code})`
    : "Rever análise do caso";
  return { label, href: `/improvement-cases/${card.improvement_case_id}${anchor}` };
}

export function formatHours(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (value < 24) return `${value.toFixed(1)} h`;
  return `${(value / 24).toFixed(1)} d`;
}
