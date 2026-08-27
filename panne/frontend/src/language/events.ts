/** Catálogo de eventos de produção e afins — linguagem operacional. */
export const EVENT_LABEL: Record<string, string> = {
  "plan.created": "Plano criado",
  "plan.item_upserted": "Item do plano atualizado",
  "plan.item_removed": "Item do plano removido",
  "plan.scheduled": "Plano programado",
  "order.created": "Ordem criada",
  "order.scheduled": "Ordem programada",
  "dependency.added": "Dependência registrada",
  "batch.split": "Batelada criada ou dividida",
  "order.released": "Ordem liberada",
  "order.held": "Ordem colocada em espera",
  "order.cancelled": "Ordem cancelada",
  "order.substituted": "Ordem substituída",
  "order.completed": "Ordem concluída",
  "order.short_closed": "Ordem encerrada parcialmente",
  "execution.policy_set": "Política de execução definida",
  "execution.policy_adopted": "Política de execução adotada",
  "weighing.session_opened": "Pesagem iniciada",
  "weighing.session_completed": "Pesagem encerrada",
  "weighing.session_cancelled": "Pesagem cancelada",
  "weighing.recorded": "Pesagem registrada",
  "weighing.verified": "Pesagem conferida",
  "step.started": "Etapa iniciada",
  "step.completed": "Etapa concluída",
  "step.held": "Etapa pausada",
  "step.resumed": "Etapa retomada",
  "step.transitioned": "Etapa atualizada",
  "consumption.recorded": "Consumo registrado",
  "yield.recorded": "Rendimento registrado",
  "occurrence.recorded": "Ocorrência registrada",
  "occurrence.resolved": "Ocorrência resolvida",
  "sheet.issued": "Ficha emitida",
  "order.in_weighing": "Ordem em pesagem",
  "order.ready": "Ordem pronta",
  "order.started": "Ordem iniciada",
  "order.resumed": "Ordem retomada",
  "batch.status_changed": "Estado da batelada atualizado",
  "dependency.overridden": "Dependência sobrescrita",
};

export const UNKNOWN_EVENT_LABEL = "Evento técnico não catalogado";

export function eventLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return EVENT_LABEL[value] ?? UNKNOWN_EVENT_LABEL;
}

export const DEPENDENCY_TYPE_LABEL: Record<string, string> = {
  soft: "Dependência flexível",
  hard: "Dependência obrigatória",
  finish_to_start: "Concluir antes de iniciar",
  start_to_start: "Iniciar junto",
};

export function dependencyTypeLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return DEPENDENCY_TYPE_LABEL[value] ?? "Dependência";
}
