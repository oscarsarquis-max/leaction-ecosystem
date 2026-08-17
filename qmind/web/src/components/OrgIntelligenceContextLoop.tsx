import { useEffect, useState } from "react";
import { useOrganization } from "@/org/OrganizationProvider";
import { OrgOrganizationContext } from "@/components/OrgOrganizationContext";
import { OrgOrganizationalIntelligence } from "@/components/OrgOrganizationalIntelligence";
import { canEditOrganizationProfile } from "@/lib/permissions";
import type { OrgProfileFieldKey } from "@/lib/orgProfileLabels";

/**
 * Home composition: organization context + OI, with stale-analysis cue after edits
 * and Completar → focus field wiring (callback only, no global store).
 */
export function OrgIntelligenceContextLoop() {
  const { currentOrganizationId, currentOrganization } = useOrganization();
  const [analysisMayBeStale, setAnalysisMayBeStale] = useState(false);
  const [completeField, setCompleteField] = useState<OrgProfileFieldKey | null>(
    null,
  );
  const canComplete = canEditOrganizationProfile(currentOrganization?.roles);

  useEffect(() => {
    setAnalysisMayBeStale(false);
    setCompleteField(null);
  }, [currentOrganizationId]);

  return (
    <div className="space-y-4" data-testid="org-intelligence-context-loop">
      <OrgOrganizationContext
        onProfileSaved={() => setAnalysisMayBeStale(true)}
        completeField={completeField}
        onCompleteFieldHandled={() => setCompleteField(null)}
      />
      <OrgOrganizationalIntelligence
        analysisMayBeStale={analysisMayBeStale}
        onAnalyzeSuccess={() => setAnalysisMayBeStale(false)}
        canCompleteFields={canComplete}
        onCompleteField={(field) => setCompleteField(field)}
      />
    </div>
  );
}
