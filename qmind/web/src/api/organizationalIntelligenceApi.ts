import { getQmindClient, withTenantGeneration } from "@/api/qmindApi";

export type InsightExplanation = {
  reasons: string[];
  evidence_refs: { source_type: string; source_id: string }[];
  supporting_facts: string[];
  mechanism_version: string | null;
};

export type OrganizationalInsight = {
  insight_id: string;
  type: string;
  title: string;
  summary: string;
  confidence: number | null;
  evidence_refs: { source_type: string; source_id: string }[];
  explanation: InsightExplanation | null;
};

export type OrganizationalInsights = {
  schema_version: string;
  core_organization_id: string;
  request_id: string;
  correlation_id: string;
  generated_at: string;
  insights: OrganizationalInsight[];
  explanations: InsightExplanation[];
  metadata: {
    producer_version?: string | null;
    environment?: string | null;
    trace_id?: string | null;
  } | null;
};

export type OrganizationIntelligenceRun = {
  id: string;
  organization_id: string;
  schema_version: string;
  request_id: string;
  correlation_id: string;
  generated_at: string;
  insights: OrganizationalInsights;
  created_at: string;
};

/** Latest run first; use limit=1 for the most recent analysis. */
export async function listIntelligenceRuns(
  limit = 50,
): Promise<OrganizationIntelligenceRun[]> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.listCurrentOrganizationIntelligenceRuns({
      query: { limit },
    });
    return (res.data ?? []) as OrganizationIntelligenceRun[];
  });
}

export async function fetchLatestIntelligenceRun(): Promise<OrganizationIntelligenceRun | null> {
  const runs = await listIntelligenceRuns(1);
  return runs[0] ?? null;
}

export async function analyzeOrganizationIntelligence(): Promise<OrganizationalInsights> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.analyzeCurrentOrganizationIntelligence({});
    return res.data as OrganizationalInsights;
  });
}

/** Reads structured reason tokens from the OI contract (e.g. clause:4). */
export function insightReasonValue(
  insight: OrganizationalInsight,
  prefix: string,
): string | null {
  const reasons = insight.explanation?.reasons ?? [];
  const hit = reasons.find((r) => r.startsWith(`${prefix}:`));
  if (!hit) return null;
  return hit.slice(prefix.length + 1) || null;
}
