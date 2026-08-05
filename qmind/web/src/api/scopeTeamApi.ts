import { getQmindClient, withTenantGeneration } from "@/api/qmindApi";

export type ScopeOption = {
  kind: "requirement" | "process" | string;
  target_id: string;
  label: string;
  already_in_scope: boolean;
};

export type OrgMemberOption = {
  membership_id: string;
  email: string;
  display_name: string | null;
  roles: string[];
  status: string;
};

export type ScopeRow = {
  id: string;
  assessment_id: string;
  org_process_id: string | null;
  requirement_id: string | null;
  created_at: string;
  label?: string | null;
};

export async function ensureAssessmentScopes(
  assessmentId: string,
): Promise<ScopeRow[]> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.post({
      url: `/api/v1/assessments/${assessmentId}/scopes/ensure`,
      security: [{ scheme: "bearer", type: "http" }],
    });
    return (res.data as ScopeRow[]) ?? [];
  });
}

export async function listScopeOptions(
  assessmentId: string,
): Promise<ScopeOption[]> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.get({
      url: `/api/v1/assessments/${assessmentId}/scope-options`,
      security: [{ scheme: "bearer", type: "http" }],
    });
    return (res.data as ScopeOption[]) ?? [];
  });
}

export async function listOrgMembers(): Promise<OrgMemberOption[]> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.get({
      url: "/api/v1/organizations/current/members",
      security: [{ scheme: "bearer", type: "http" }],
    });
    return (res.data as OrgMemberOption[]) ?? [];
  });
}
