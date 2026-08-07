import { NavLink } from "react-router-dom";
import { useAuditPlan } from "@/hooks/useAuditPlan";
import { useAssessment } from "@/hooks/useAssessmentDetail";
import { auditPlanDiscoveryLabel } from "@/lib/auditPlanDiscovery";

type Props = {
  assessmentId: string;
};

const linkClass = ({ isActive }: { isActive: boolean }) =>
  [
    "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-semibold transition-colors",
    isActive
      ? "bg-[var(--qm-ink)] text-white"
      : "text-[var(--qm-ink)] hover:bg-[var(--qm-surface-soft)]",
  ].join(" ");

/**
 * Navegação de descoberta da avaliação — inclui Análise/Relatório após o campo.
 */
export function AssessmentSectionNav({ assessmentId }: Props) {
  const planQ = useAuditPlan(assessmentId);
  const assessment = useAssessment(assessmentId);
  const planLabel = auditPlanDiscoveryLabel(planQ.data);
  const status = assessment.data?.status;
  const showPhaseWork =
    status === "in_progress" ||
    status === "analysis" ||
    status === "actions" ||
    status === "report" ||
    status === "closed";

  const phaseWorkLabel = "Análise, ações e relatório";

  return (
    <nav
      className="flex flex-wrap gap-1 rounded-lg border border-[var(--qm-line)] bg-[var(--qm-surface)] p-1"
      aria-label="Seções da avaliação"
      data-testid="assessment-section-nav"
    >
      <NavLink
        to={`/assessments/${assessmentId}`}
        end
        className={linkClass}
        data-testid="nav-overview"
      >
        Visão geral
      </NavLink>
      <NavLink
        to={`/assessments/${assessmentId}/guided`}
        className={linkClass}
        data-testid="nav-preparation"
      >
        Preparação
      </NavLink>
      <NavLink
        to={`/assessments/${assessmentId}/audit-plan`}
        className={linkClass}
        data-testid="nav-audit-plan"
      >
        Plano da Auditoria
        <span
          className="rounded bg-black/10 px-1.5 py-0.5 text-[11px] font-semibold"
          data-testid="nav-audit-plan-status"
        >
          {planQ.isLoading ? "…" : planLabel}
        </span>
      </NavLink>
      <NavLink
        to={`/assessments/${assessmentId}/work`}
        className={linkClass}
        data-testid="nav-field"
      >
        Execução em campo
      </NavLink>
      {showPhaseWork ? (
        <NavLink
          to={`/assessments/${assessmentId}/advanced`}
          className={linkClass}
          data-testid="nav-phase-work"
        >
          {phaseWorkLabel}
        </NavLink>
      ) : null}
    </nav>
  );
}
