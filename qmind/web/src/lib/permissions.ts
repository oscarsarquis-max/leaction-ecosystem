/**
 * Mirrors backend assessment role gates
 * (_MUTATE_ROLES / _READ_ROLES in assessments/service.py).
 */

const MUTATE_ROLES = new Set([
  "org_admin",
  "consultant_auditor",
  "quality_manager",
]);

const READ_ROLES = new Set([
  ...MUTATE_ROLES,
  "process_owner",
  "reader",
]);

export function canMutateAssessments(roles: readonly string[] | undefined): boolean {
  return (roles ?? []).some((r) => MUTATE_ROLES.has(r));
}

export function canReadAssessments(roles: readonly string[] | undefined): boolean {
  return (roles ?? []).some((r) => READ_ROLES.has(r));
}

/** Draft-only mutations (scope/team/plan) require mutate role + draft status. */
export function canEditAssessmentSetup(
  roles: readonly string[] | undefined,
  status: string | undefined,
): boolean {
  return canMutateAssessments(roles) && status === "draft";
}

/** planned → in_progress */
export function canStartAssessment(
  roles: readonly string[] | undefined,
  status: string | undefined,
): boolean {
  return canMutateAssessments(roles) && status === "planned";
}

/** Interviews / answers / evidence collection while assessment is in_progress. */
export function canEditFieldExecution(
  roles: readonly string[] | undefined,
  status: string | undefined,
): boolean {
  return canMutateAssessments(roles) && status === "in_progress";
}

export function canCollectEvidence(
  roles: readonly string[] | undefined,
  status: string | undefined,
): boolean {
  return (
    canMutateAssessments(roles) &&
    (status === "in_progress" || status === "analysis")
  );
}

const FINDING_CREATE_ROLES = new Set([
  "org_admin",
  "consultant_auditor",
  "quality_manager",
]);

const FINDING_REVIEW_ROLES = new Set(["org_admin", "quality_manager"]);

/** Assessment statuses that accept new/edited findings. */
export function canWorkFindingsOnAssessment(status: string | undefined): boolean {
  return status === "in_progress" || status === "analysis" || status === "actions";
}

export function canCreateFindings(
  roles: readonly string[] | undefined,
  assessmentStatus: string | undefined,
): boolean {
  return (
    (roles ?? []).some((r) => FINDING_CREATE_ROLES.has(r)) &&
    canWorkFindingsOnAssessment(assessmentStatus)
  );
}

export function canReviewFindings(roles: readonly string[] | undefined): boolean {
  return (roles ?? []).some((r) => FINDING_REVIEW_ROLES.has(r));
}

/** Approve SoD: reviewer role + not the author membership. */
export function canApproveFinding(
  roles: readonly string[] | undefined,
  currentMembershipId: string | null | undefined,
  authorMembershipId: string | null | undefined,
): boolean {
  if (!canReviewFindings(roles)) return false;
  if (!currentMembershipId || !authorMembershipId) return false;
  return currentMembershipId !== authorMembershipId;
}

export function isFindingAuthor(
  currentMembershipId: string | null | undefined,
  authorMembershipId: string | null | undefined,
): boolean {
  return !!currentMembershipId && currentMembershipId === authorMembershipId;
}

/** Maturity elaborate roles mirror backend _ELABORATE_ROLES. */
const MATURITY_ELABORATE_ROLES = FINDING_CREATE_ROLES;
const MATURITY_REVIEW_ROLES = FINDING_REVIEW_ROLES;

export function canWorkMaturityOnAssessment(status: string | undefined): boolean {
  return (
    status === "in_progress" ||
    status === "analysis" ||
    status === "actions" ||
    status === "report"
  );
}

export function canElaborateMaturity(
  roles: readonly string[] | undefined,
  assessmentStatus: string | undefined,
): boolean {
  return (
    (roles ?? []).some((r) => MATURITY_ELABORATE_ROLES.has(r)) &&
    canWorkMaturityOnAssessment(assessmentStatus)
  );
}

export function canReviewMaturity(roles: readonly string[] | undefined): boolean {
  return (roles ?? []).some((r) => MATURITY_REVIEW_ROLES.has(r));
}

export function canApproveMaturity(
  roles: readonly string[] | undefined,
  currentMembershipId: string | null | undefined,
  authorMembershipId: string | null | undefined,
): boolean {
  if (!canReviewMaturity(roles)) return false;
  if (!currentMembershipId || !authorMembershipId) return false;
  return currentMembershipId !== authorMembershipId;
}

export function canEditMaturityScores(
  roles: readonly string[] | undefined,
  assessmentStatus: string | undefined,
  packageStatus: string | undefined,
): boolean {
  return canElaborateMaturity(roles, assessmentStatus) && packageStatus === "draft";
}

/** Soft client hints — server still enforces on submit. */
export function maturityEvidenceHint(level: number | null | undefined): string | null {
  if (level == null) return null;
  if (level >= 5) {
    return "Nível 5: evidência aprovada + justificativa de ciclo de melhoria.";
  }
  if (level >= 4) {
    return "Nível 4: evidência aprovada + justificativa de medição/uso de dados.";
  }
  if (level >= 3) {
    return "Nível 3+: ≥1 evidência aprovada vinculada (exigido no envio).";
  }
  return null;
}

const ACTION_PLAN_ROLES = FINDING_CREATE_ROLES;
const ACTION_VALIDATE_ROLES = new Set(["org_admin", "quality_manager", "process_owner"]);
const ACTION_EFFICACY_ROLES = new Set(["org_admin", "quality_manager"]);

export function canWorkActionPlansOnAssessment(status: string | undefined): boolean {
  return status === "analysis" || status === "actions" || status === "report";
}

export function canManageActionPlans(
  roles: readonly string[] | undefined,
  assessmentStatus: string | undefined,
): boolean {
  return (
    (roles ?? []).some((r) => ACTION_PLAN_ROLES.has(r)) &&
    (assessmentStatus === "analysis" || assessmentStatus === "actions")
  );
}

export function canValidateActionItems(roles: readonly string[] | undefined): boolean {
  return (roles ?? []).some((r) => ACTION_VALIDATE_ROLES.has(r));
}

export function canConfirmActionEfficacy(roles: readonly string[] | undefined): boolean {
  return (roles ?? []).some((r) => ACTION_EFFICACY_ROLES.has(r));
}

/** SoD: validator/confirmer must differ from item owner. */
export function canActAsActionValidator(
  roles: readonly string[] | undefined,
  currentMembershipId: string | null | undefined,
  ownerMembershipId: string | null | undefined,
  mode: "validate" | "efficacy",
): boolean {
  const roleOk =
    mode === "validate"
      ? canValidateActionItems(roles)
      : canConfirmActionEfficacy(roles);
  if (!roleOk || !currentMembershipId || !ownerMembershipId) return false;
  return currentMembershipId !== ownerMembershipId;
}

/** Client-side overdue hint when backend flag is false but due_at elapsed. */
export function isActionItemOverdueDisplay(item: {
  is_overdue?: boolean;
  due_at?: string;
  status?: string;
}): boolean {
  if (item.is_overdue) return true;
  const terminal = new Set(["done", "cancelled", "ineffective_closed"]);
  if (!item.due_at || (item.status && terminal.has(item.status))) return false;
  return Date.parse(item.due_at) < Date.now();
}

const REPORT_ELABORATE_ROLES = FINDING_CREATE_ROLES;
const REPORT_PUBLISH_ROLES = new Set(["org_admin", "quality_manager"]);
const ASSESSMENT_CLOSE_ROLES = FINDING_CREATE_ROLES;
const ASSESSMENT_REOPEN_ROLES = new Set(["org_admin", "quality_manager"]);

export function canWorkReportsOnAssessment(status: string | undefined): boolean {
  return status === "actions" || status === "report" || status === "closed";
}

export function canElaborateReports(
  roles: readonly string[] | undefined,
  assessmentStatus: string | undefined,
): boolean {
  return (
    (roles ?? []).some((r) => REPORT_ELABORATE_ROLES.has(r)) &&
    (assessmentStatus === "actions" || assessmentStatus === "report")
  );
}

export function canReviewReports(roles: readonly string[] | undefined): boolean {
  return (roles ?? []).some((r) => REPORT_PUBLISH_ROLES.has(r));
}

/** Soft SoD: publisher must differ from report author. */
export function canPublishReport(
  roles: readonly string[] | undefined,
  currentMembershipId: string | null | undefined,
  authorMembershipId: string | null | undefined,
): boolean {
  if (!canReviewReports(roles) || !currentMembershipId || !authorMembershipId) {
    return false;
  }
  return currentMembershipId !== authorMembershipId;
}

export function canCloseAssessment(
  roles: readonly string[] | undefined,
  assessmentStatus: string | undefined,
): boolean {
  return (
    (roles ?? []).some((r) => ASSESSMENT_CLOSE_ROLES.has(r)) &&
    assessmentStatus === "report"
  );
}

export function canReopenAssessment(
  roles: readonly string[] | undefined,
  assessmentStatus: string | undefined,
): boolean {
  return (
    (roles ?? []).some((r) => ASSESSMENT_REOPEN_ROLES.has(r)) &&
    assessmentStatus === "closed"
  );
}

export function canBeginAssessmentReport(
  roles: readonly string[] | undefined,
  assessmentStatus: string | undefined,
): boolean {
  return (
    (roles ?? []).some((r) => ASSESSMENT_CLOSE_ROLES.has(r)) &&
    assessmentStatus === "actions"
  );
}
