import type { FlowStepId } from "./steps";

/** Papéis conhecidos da demo / membership (rótulos humanos via display). */
export type FlowRoleHint =
  | "owner"
  | "production_manager"
  | "technical_responsible"
  | "baker_operator"
  | "regulatory_reviewer"
  | "commercial"
  | "viewer"
  | "other";

export function resolveFlowRole(roles: string[] | undefined | null): FlowRoleHint {
  const list = roles ?? [];
  if (list.includes("owner")) return "owner";
  if (list.includes("production_manager")) return "production_manager";
  if (list.includes("technical_responsible")) return "technical_responsible";
  if (list.includes("baker_operator")) return "baker_operator";
  if (list.includes("regulatory_reviewer")) return "regulatory_reviewer";
  if (list.includes("commercial")) return "commercial";
  if (list.includes("viewer")) return "viewer";
  return "other";
}

export function roleDisplayLabel(hint: FlowRoleHint): string {
  switch (hint) {
    case "owner":
      return "Proprietário";
    case "production_manager":
      return "Gestor de produção";
    case "technical_responsible":
      return "Formulador";
    case "baker_operator":
      return "Padeiro";
    case "regulatory_reviewer":
      return "Revisor";
    case "commercial":
      return "Comercial / compras";
    case "viewer":
      return "Leitor";
    default:
      return "Perfil operacional";
  }
}

/** Etapa sugerida ao abrir `/fluxo` (sem query). */
export function preferredStepForRole(hint: FlowRoleHint): FlowStepId {
  switch (hint) {
    case "baker_operator":
      return 6;
    case "regulatory_reviewer":
      return 7;
    case "technical_responsible":
      return 4;
    case "commercial":
      return 1;
    case "viewer":
      return 5;
    case "production_manager":
      return 5;
    case "owner":
    default:
      return 1;
  }
}

/**
 * Etapas em foco para o perfil (demais podem aparecer como contexto).
 * Custos (8) nunca entram se sem permissão — tratado fora.
 */
export function focusStepsForRole(hint: FlowRoleHint): Set<FlowStepId> {
  switch (hint) {
    case "baker_operator":
      return new Set([5, 6, 7]);
    case "regulatory_reviewer":
      return new Set([7, 4]);
    case "technical_responsible":
      return new Set([2, 3, 4]);
    case "commercial":
      return new Set([1, 2, 8]);
    case "viewer":
      return new Set([1, 2, 3, 4, 5, 6, 7, 8]);
    case "production_manager":
      return new Set([2, 4, 5, 6, 7, 8]);
    case "owner":
    default:
      return new Set([1, 2, 3, 4, 5, 6, 7, 8]);
  }
}
