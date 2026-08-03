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
