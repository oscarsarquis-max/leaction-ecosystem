import { useEffect, useState } from "react";
import { useOrganization } from "@/org/OrganizationProvider";
import { OrgOrganizationContext } from "@/components/OrgOrganizationContext";
import { OrgOrganizationalIntelligence } from "@/components/OrgOrganizationalIntelligence";

/**
 * Home composition: organization context + OI, with stale-analysis cue after edits.
 */
export function OrgIntelligenceContextLoop() {
  const { currentOrganizationId } = useOrganization();
  const [analysisMayBeStale, setAnalysisMayBeStale] = useState(false);

  useEffect(() => {
    setAnalysisMayBeStale(false);
  }, [currentOrganizationId]);

  return (
    <div className="space-y-4" data-testid="org-intelligence-context-loop">
      <OrgOrganizationContext
        onProfileSaved={() => setAnalysisMayBeStale(true)}
      />
      <OrgOrganizationalIntelligence
        analysisMayBeStale={analysisMayBeStale}
        onAnalyzeSuccess={() => setAnalysisMayBeStale(false)}
      />
    </div>
  );
}
