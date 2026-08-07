import { Link, useLocation } from "react-router-dom";
import { useOrganization } from "@/org/OrganizationProvider";
import { isGuidedTourActive, readGuidedTourStepIndex } from "@/lib/guidedTour";

/**
 * Ação discreta para retornar à apresentação guiada após “Abrir no produto”.
 */
export function GuidedTourReturnBanner() {
  const org = useOrganization();
  const location = useLocation();

  if (location.pathname.startsWith("/guided-tour")) return null;
  if (!isGuidedTourActive(org.currentOrganizationId)) return null;

  const step = readGuidedTourStepIndex() + 1;

  return (
    <div
      className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-md border border-[var(--qm-line)] bg-[var(--qm-surface-soft)] px-3 py-2 text-sm"
      data-testid="guided-tour-return-banner"
      role="status"
    >
      <span className="text-[var(--qm-muted)]">
        Apresentação guiada em andamento (etapa {step}).
      </span>
      <Link
        to="/guided-tour"
        className="font-medium text-[var(--qm-accent)] underline-offset-2 hover:underline"
      >
        Voltar à apresentação guiada
      </Link>
    </div>
  );
}
