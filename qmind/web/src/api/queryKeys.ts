/** All org-scoped React Query keys include organization_id. */

export const queryKeys = {
  memberships: ["memberships"] as const,
  assessments: (organizationId: string) =>
    ["org", organizationId, "assessments"] as const,
  assessment: (organizationId: string, assessmentId: string) =>
    ["org", organizationId, "assessment", assessmentId] as const,
  assessmentScopes: (organizationId: string, assessmentId: string) =>
    ["org", organizationId, "assessment", assessmentId, "scopes"] as const,
  assessmentTeam: (organizationId: string, assessmentId: string) =>
    ["org", organizationId, "assessment", assessmentId, "team"] as const,
  assessmentQuestions: (organizationId: string, assessmentId: string) =>
    ["org", organizationId, "assessment", assessmentId, "questions"] as const,
  assessmentInterviews: (organizationId: string, assessmentId: string) =>
    ["org", organizationId, "assessment", assessmentId, "interviews"] as const,
  interviewAnswers: (organizationId: string, interviewId: string) =>
    ["org", organizationId, "interview", interviewId, "answers"] as const,
  assessmentEvidences: (organizationId: string, assessmentId: string) =>
    ["org", organizationId, "assessment", assessmentId, "evidences"] as const,
  evidenceLinks: (organizationId: string, evidenceId: string) =>
    ["org", organizationId, "evidence", evidenceId, "links"] as const,
  assessmentFindings: (organizationId: string, assessmentId: string) =>
    ["org", organizationId, "assessment", assessmentId, "findings"] as const,
  finding: (organizationId: string, findingId: string) =>
    ["org", organizationId, "finding", findingId] as const,
  assessmentMaturity: (organizationId: string, assessmentId: string) =>
    ["org", organizationId, "assessment", assessmentId, "maturity"] as const,
  maturityPackage: (organizationId: string, packageId: string) =>
    ["org", organizationId, "maturity", packageId] as const,
  assessmentActionPlans: (organizationId: string, assessmentId: string) =>
    ["org", organizationId, "assessment", assessmentId, "action-plans"] as const,
  actionPlanItems: (organizationId: string, planId: string) =>
    ["org", organizationId, "action-plan", planId, "items"] as const,
  health: ["health"] as const,
};

export function isOrgScopedKey(queryKey: readonly unknown[]): boolean {
  return queryKey[0] === "org";
}
