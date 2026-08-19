/** Labels for ImprovementCase status — never show raw tokens. */

const STATUS_LABEL: Record<string, string> = {
  open: "Aberto",
  analyzing: "Em análise",
  acting: "Em tratamento",
  reviewing: "Em revisão",
  closed: "Encerrado",
};

const CONTEXT_STATUS_LABEL: Record<string, string> = {
  insufficient_context: "Contexto insuficiente",
  ready_for_initial_analysis: "Pronto para análise inicial",
};

const SUPPORT_STATUS_LABEL: Record<string, string> = {
  requires_validation: "Requer validação",
  partially_supported: "Parcialmente sustentada",
  supported_by_available_facts: "Sustentada pelos fatos disponíveis",
};

const RESULT_DIRECTION_LABEL: Record<string, string> = {
  improved: "Melhorou",
  unchanged: "Permaneceu igual",
  worsened: "Piorou",
  not_yet_measured: "Ainda não foi medido",
};

const CLOSURE_READINESS_LABEL: Record<string, string> = {
  insufficient_information: "Ainda faltam elementos para revisar o caso",
  ready_for_review: "O caso possui elementos para revisão",
};

export function labelImprovementCaseStatus(status: string | undefined): string {
  if (!status) return "—";
  return STATUS_LABEL[status] ?? status;
}

export function labelProblemContextStatus(status: string | undefined): string {
  if (!status) return "—";
  return CONTEXT_STATUS_LABEL[status] ?? status;
}

export function labelHypothesisSupportStatus(
  status: string | undefined,
): string {
  if (!status) return "—";
  return SUPPORT_STATUS_LABEL[status] ?? status;
}

export function labelResultDirection(direction: string | undefined): string {
  if (!direction) return "—";
  return RESULT_DIRECTION_LABEL[direction] ?? direction;
}

export function labelClosureReadiness(value: string | undefined): string {
  if (!value) return "—";
  return CLOSURE_READINESS_LABEL[value] ?? value;
}

export const RESULT_DIRECTION_OPTIONS = [
  { value: "improved", label: "Melhorou" },
  { value: "unchanged", label: "Permaneceu igual" },
  { value: "worsened", label: "Piorou" },
  { value: "not_yet_measured", label: "Ainda não foi medido" },
] as const;

export const IMPROVEMENT_CASE_STATUS_OPTIONS = [
  { value: "open", label: "Aberto" },
  { value: "analyzing", label: "Em análise" },
  { value: "acting", label: "Em tratamento" },
  { value: "reviewing", label: "Em revisão" },
  { value: "closed", label: "Encerrado" },
] as const;

/** Allowed next statuses from current (mirrors backend). */
export function allowedImprovementCaseTransitions(
  current: string,
): readonly string[] {
  const map: Record<string, readonly string[]> = {
    open: ["analyzing"],
    analyzing: ["open", "acting"],
    acting: ["analyzing", "reviewing"],
    reviewing: ["acting", "closed"],
    closed: ["reviewing"],
  };
  return map[current] ?? [];
}
