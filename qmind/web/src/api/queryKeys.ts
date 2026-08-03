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
  health: ["health"] as const,
};

export function isOrgScopedKey(queryKey: readonly unknown[]): boolean {
  return queryKey[0] === "org";
}
