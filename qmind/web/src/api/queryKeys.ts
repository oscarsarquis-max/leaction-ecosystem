/** All org-scoped React Query keys include organization_id. */

export const queryKeys = {
  memberships: ["memberships"] as const,
  assessments: (organizationId: string) =>
    ["org", organizationId, "assessments"] as const,
  assessment: (organizationId: string, assessmentId: string) =>
    ["org", organizationId, "assessment", assessmentId] as const,
  assessmentScopes: (organizationId: string, assessmentId: string) =>
    ["org", organizationId, "assessment", assessmentId, "scopes"] as const,
  assessmentScopeOptions: (organizationId: string, assessmentId: string) =>
    ["org", organizationId, "assessment", assessmentId, "scope-options"] as const,
  assessmentTeam: (organizationId: string, assessmentId: string) =>
    ["org", organizationId, "assessment", assessmentId, "team"] as const,
  orgMembers: (organizationId: string) =>
    ["org", organizationId, "members"] as const,
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
  assessmentReports: (organizationId: string, assessmentId: string) =>
    ["org", organizationId, "assessment", assessmentId, "reports"] as const,
  report: (organizationId: string, reportId: string) =>
    ["org", organizationId, "report", reportId] as const,
  guidedCatalog: (version?: string | null) =>
    ["guided", "catalog", version ?? "default"] as const,
  guidedSession: (organizationId: string, assessmentId: string) =>
    ["org", organizationId, "assessment", assessmentId, "guided"] as const,
  auditPlan: (organizationId: string, assessmentId: string) =>
    ["org", organizationId, "assessment", assessmentId, "audit-plan"] as const,
  auditPlanSchedule: (organizationId: string, assessmentId: string) =>
    [
      "org",
      organizationId,
      "assessment",
      assessmentId,
      "audit-plan-schedule",
    ] as const,
  guidedAnswerEvidences: (
    organizationId: string,
    assessmentId: string,
    questionId: string,
  ) =>
    [
      "org",
      organizationId,
      "assessment",
      assessmentId,
      "guided",
      "answer",
      questionId,
      "evidences",
    ] as const,
  agendaBoard: (organizationId: string, selectedDate: string) =>
    ["org", organizationId, "agenda", selectedDate] as const,
  assessmentEvolutionMap: (organizationId: string, assessmentId: string) =>
    ["org", organizationId, "assessment", assessmentId, "evolution-map"] as const,
  orgProfile: (organizationId: string) =>
    ["org", organizationId, "profile"] as const,
  orgIntelligenceLatest: (organizationId: string) =>
    ["org", organizationId, "intelligence", "latest"] as const,
  health: ["health"] as const,
};

export function isOrgScopedKey(queryKey: readonly unknown[]): boolean {
  return queryKey[0] === "org";
}
