import type { AuditPlan, AuditPlanStatus } from "@/api/auditPlanTypes";

/** Rótulos de descoberta na navegação da avaliação. */
export type AuditPlanDiscoveryState =
  | "not_started"
  | "in_progress"
  | "ready"
  | "amended";

export function auditPlanDiscoveryState(
  plan: AuditPlan | null | undefined,
): AuditPlanDiscoveryState {
  if (!plan) return "not_started";
  if (plan.plan_status === "amended") return "amended";
  if (plan.plan_status === "ready") return "ready";
  const percent = plan.readiness?.percent ?? 0;
  const hasSubstance =
    percent > 0 ||
    !!(plan.objective || "").trim() ||
    !!(plan.planned_start && plan.planned_end);
  return hasSubstance ? "in_progress" : "not_started";
}

export function auditPlanDiscoveryLabel(
  plan: AuditPlan | null | undefined,
): string {
  switch (auditPlanDiscoveryState(plan)) {
    case "amended":
      return "Com emenda";
    case "ready":
      return "Pronto";
    case "in_progress":
      return "Em elaboração";
    default:
      return "Não iniciado";
  }
}

/** CTA principal de descoberta do plano (mapa / próxima ação). */
export function auditPlanDiscoveryAction(
  assessmentId: string,
  plan: AuditPlan | null | undefined,
  assessmentStatus: string | undefined | null,
): { href: string; label: string } {
  const href = `/assessments/${assessmentId}/audit-plan`;
  const state = auditPlanDiscoveryState(plan);
  if (state === "not_started") {
    return { href, label: "Criar Plano da Auditoria" };
  }
  if (state === "in_progress") {
    return { href, label: "Continuar Plano da Auditoria" };
  }
  // ready | amended
  if (assessmentStatus === "planned" || assessmentStatus === "in_progress") {
    return {
      href: `/assessments/${assessmentId}/work`,
      label: "Iniciar execução em campo",
    };
  }
  return { href, label: "Revisar programação" };
}

export function planStatusDiscoveryLabel(status: AuditPlanStatus): string {
  if (status === "ready") return "Pronto";
  if (status === "amended") return "Com emenda";
  return "Em elaboração";
}
