import { getQmindClient, withTenantGeneration } from "@/api/qmindApi";

export type BusinessModel =
  | ""
  | "b2b"
  | "b2c"
  | "b2b2c"
  | "services"
  | "manufacturing"
  | "mixed"
  | "other";

export type EmployeeRange =
  | ""
  | "1-10"
  | "11-50"
  | "51-200"
  | "201-500"
  | "501-1000"
  | "1000+";

export type CertificationStatus =
  | "unknown"
  | "none"
  | "in_progress"
  | "certified"
  | "expired"
  | "not_applicable";

export type QualityStructure =
  | "unknown"
  | "none"
  | "informal"
  | "formal_partial"
  | "formal";

export type OrganizationProfile = {
  organization_id: string;
  trade_name: string;
  legal_name: string;
  summary: string;
  industry: string;
  business_model: BusinessModel;
  employee_range: EmployeeRange;
  unit_count: number | null;
  certification_status: CertificationStatus;
  quality_structure: QualityStructure;
  created_at: string;
  updated_at: string;
};

export type OrganizationProfilePatch = {
  trade_name?: string;
  legal_name?: string;
  summary?: string;
  industry?: string;
  business_model?: BusinessModel;
  employee_range?: EmployeeRange;
  unit_count?: number | null;
  certification_status?: CertificationStatus;
  quality_structure?: QualityStructure;
};

export async function fetchOrganizationProfile(): Promise<OrganizationProfile> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.get({
      url: "/api/v1/organizations/current/profile",
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as OrganizationProfile;
  });
}

export async function patchOrganizationProfile(
  payload: OrganizationProfilePatch,
): Promise<OrganizationProfile> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.patch({
      url: "/api/v1/organizations/current/profile",
      body: payload,
      headers: { "Content-Type": "application/json" },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as OrganizationProfile;
  });
}
