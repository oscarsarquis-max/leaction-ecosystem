import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { AssessmentOut } from "@qmind/api-client";
import { useOrganization } from "@/org/OrganizationProvider";
import { useAuditDashboard } from "@/hooks/useAuditDashboard";
import { useAssessmentPermissions } from "@/hooks/useAssessmentPermissions";
import { labelAssessmentStatus, labelAssessmentType } from "@/lib/labels";
import { selectFocusAssessment } from "@/lib/selectFocusAssessment";
import {
  buildOrgPhaseCards,
  homeNextAction,
} from "@/lib/orgJourneyPhases";
import { JOURNEY_PHASES, type JourneyPhaseId } from "@/lib/auditJourney";
import { PhaseDetails } from "@/components/qm/PhaseDetails";
import { LoadingPanel } from "@/components/StatePanels";
import { AssessmentFocusSelector } from "@/components/orgJourney/AssessmentFocusSelector";
import { JourneyMap } from "@/components/orgJourney/JourneyMap";
import { JourneyNextAction } from "@/components/orgJourney/JourneyNextAction";

type Props = {
  assessments: AssessmentOut[];
};

function focusStorageKey(orgId: string) {
  return `qmind.focusAssessment.${orgId}`;
}

export function OrgJourneyOverview({ assessments }: Props) {
  const org = useOrganization();
  const orgId = org.currentOrganizationId;
  const perms = useAssessmentPermissions();

  const autoFocus = useMemo(
    () => selectFocusAssessment(assessments),
    [assessments],
  );

  const [focusId, setFocusId] = useState<string | null>(null);

  // Troca de organização limpa foco; restaura preferência só da org ativa.
  useEffect(() => {
    if (!orgId) {
      setFocusId(null);
      return;
    }
    const stored = sessionStorage.getItem(focusStorageKey(orgId));
    const valid = stored && assessments.some((a) => a.id === stored);
    setFocusId(valid ? stored : autoFocus?.id ?? null);
  }, [orgId, assessments, autoFocus?.id]);

  const focused =
    assessments.find((a) => a.id === focusId) ?? autoFocus ?? null;

  const dash = useAuditDashboard(focused?.id);

  const cards = useMemo(
    () =>
      buildOrgPhaseCards(
        focused
          ? {
              status: dash.status,
              preparationReady: dash.preparationReady,
              pending: dash.pending,
              checklist: dash.checklist,
              counts: dash.counts,
              hasLead: !!dash.assessment?.lead_membership_id,
            }
          : null,
      ),
    [focused, dash],
  );

  const next = useMemo(() => {
    if (!focused) {
      return homeNextAction({
        assessmentId: "",
        status: null,
        preparationReady: false,
        continueHref: "/assessments/new",
        continueLabel: "Iniciar primeira avaliação",
        guidedAnswered: 0,
        guidedTotal: 0,
        pending: [],
      });
    }
    return homeNextAction({
      assessmentId: focused.id,
      status: dash.status,
      preparationReady: dash.preparationReady,
      continueHref: dash.continueAction.href,
      continueLabel: dash.continueAction.label,
      guidedAnswered: dash.counts.guidedAnswered,
      guidedTotal: dash.counts.guidedTotal,
      pending: dash.pending,
    });
  }, [focused, dash]);

  const [openPhaseId, setOpenPhaseId] = useState<JourneyPhaseId | null>(null);
  const openPhase = JOURNEY_PHASES.find((p) => p.id === openPhaseId) ?? null;

  function chooseFocus(id: string) {
    setFocusId(id);
    if (orgId) sessionStorage.setItem(focusStorageKey(orgId), id);
  }

  const orgName =
    org.currentOrganization?.organizationName ?? "organização selecionada";

  return (
    <section
      className="org-journey"
      data-testid="org-journey-overview"
      aria-labelledby="org-journey-heading"
    >
      <header className="org-journey__header">
        <div>
          <p className="org-journey__eyebrow">Percurso da avaliação</p>
          <h2 id="org-journey-heading" className="org-journey__title">
            Onde você está neste trabalho
          </h2>
          <p className="org-journey__lead">
            Em {orgName}, o QMind conduz a avaliação da preparação ao
            relatório. Os estados abaixo refletem dados reais — não um desenho
            estático.
          </p>
        </div>
        {focused ? (
          <div className="org-journey__focus-meta" data-testid="journey-focus-meta">
            <p className="font-semibold text-[var(--qm-ink)]">
              {labelAssessmentType(focused.type)}
            </p>
            <p className="text-sm text-[var(--qm-muted)]">
              Situação: {labelAssessmentStatus(focused.status)}
              {dash.scopes.length > 0
                ? ` · Escopo: ${dash.scopes.length} item(ns)`
                : " · Escopo formal ainda não detalhado"}
            </p>
            <AssessmentFocusSelector
              assessments={assessments.filter((a) => a.status !== "cancelled")}
              focusId={focused.id}
              onChange={chooseFocus}
            />
          </div>
        ) : null}
      </header>

      {!focused ? (
        <JourneyNextAction
          title={next.title}
          description={next.description}
          reason={next.reason}
          actionText={
            perms.canMutate ? next.actionText : "Sem permissão para criar"
          }
          href={perms.canMutate ? next.href : "/assessments"}
        />
      ) : dash.loading ? (
        <LoadingPanel title="Atualizando o percurso desta avaliação…" />
      ) : (
        <JourneyNextAction {...next} />
      )}

      <JourneyMap
        cards={cards}
        emptyMode={!focused}
        onSelectPhase={(id) => setOpenPhaseId(id as JourneyPhaseId)}
      />

      {!focused ? (
        <p className="org-journey__empty-hint">
          Nenhuma avaliação ativa. O mapa mostra o caminho completo em estado
          “Não iniciado”.{" "}
          {perms.canMutate ? (
            <Link to="/assessments/new" className="font-semibold text-[var(--qm-accent)]">
              Iniciar primeira avaliação
            </Link>
          ) : null}
        </p>
      ) : (
        <p className="org-journey__empty-hint">
          Toque em uma fase para ver o que já foi feito, o que falta e para onde
          ir.{" "}
          <Link
            to={`/assessments/${focused.id}`}
            className="font-semibold text-[var(--qm-accent)]"
          >
            Abrir mapa detalhado da avaliação
          </Link>
        </p>
      )}

      {openPhase && focused ? (
        <PhaseDetails
          phase={openPhase}
          status={dash.status}
          assessmentId={focused.id}
          realPending={
            cards.find((c) => c.phase.id === openPhase.id)?.pendingHints ??
            dash.pending
          }
          preparationReady={dash.preparationReady}
          onClose={() => setOpenPhaseId(null)}
        />
      ) : null}

      {openPhase && !focused ? (
        <PhaseDetails
          phase={openPhase}
          status={null}
          realPending={[]}
          preparationReady={false}
          onClose={() => setOpenPhaseId(null)}
        />
      ) : null}
    </section>
  );
}
