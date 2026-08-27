/** Estados em que a rota operacional `/producao/ordens/:id/executar` é a entrada legítima do chão. */
export const FLOOR_EXECUTION_STATUSES = new Set([
  "released",
  "in_weighing",
  "ready",
  "in_progress",
  "on_hold",
]);

const EXECUTION_PERMS = [
  "production.weighing.record",
  "production.step.execute",
  "production.consumption.record",
] as const;

const TERMINAL_STATUSES = new Set(["completed", "cancelled", "short_closed"]);

/**
 * Alinhado a `board._next_action`: rascunho/programada pedem programar/liberar (detalhe),
 * não a tela de pesagem/etapas. Terminais não oferecem execução.
 */
export function canOfferFloorExecution(
  status: string,
  hasPermission: (code: string) => boolean,
): boolean {
  if (TERMINAL_STATUSES.has(status)) return false;
  if (!FLOOR_EXECUTION_STATUSES.has(status)) return false;
  return EXECUTION_PERMS.some((code) => hasPermission(code));
}

export function floorExecutionHint(status: string): string | null {
  if (TERMINAL_STATUSES.has(status)) return "Execução encerrada";
  if (status === "draft") return "Aguardando programação";
  if (status === "scheduled") return "Aguardando liberação";
  if (!FLOOR_EXECUTION_STATUSES.has(status)) return "Execução indisponível neste estado";
  return "Sem permissão para executar";
}
