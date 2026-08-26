import { Link, useLocation } from "react-router-dom";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  chapterIdFromStepIndex,
  isGuidedTourActive,
  readGuidedTourStepIndex,
} from "@/lib/guidedTour";
import { guidedTourPathForChapter, JOURNEY_V2_CHAPTERS } from "@/journeyV2";

/**
 * Ação discreta para retornar à apresentação guiada após “Abrir no produto”.
 */
export function GuidedTourReturnBanner() {
  const org = useOrganization();
  const location = useLocation();

  if (location.pathname.startsWith("/guided-tour")) return null;
  if (!isGuidedTourActive(org.currentOrganizationId)) return null;

  const stepIndex = readGuidedTourStepIndex();
  const chapterId = chapterIdFromStepIndex(stepIndex);
  const chapter =
    JOURNEY_V2_CHAPTERS.find((c) => c.id === chapterId) ?? JOURNEY_V2_CHAPTERS[0]!;
  const returnTo = guidedTourPathForChapter(chapterId);

  return (
    <div
      className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-md border border-[var(--qm-line)] bg-[var(--qm-surface-soft)] px-3 py-2 text-sm"
      data-testid="guided-tour-return-banner"
      role="status"
    >
      <span className="text-[var(--qm-muted)]">
        Apresentação guiada em andamento — capítulo {stepIndex + 1}: {chapter.label}.
      </span>
      <Link
        to={returnTo}
        className="font-medium text-[var(--qm-accent)] underline-offset-2 hover:underline"
      >
        Voltar à apresentação guiada
      </Link>
    </div>
  );
}
