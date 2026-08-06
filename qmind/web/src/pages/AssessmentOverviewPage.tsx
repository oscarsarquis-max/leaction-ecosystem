import { useNavigate, useParams } from "react-router-dom";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { LoadingPanel } from "@/components/StatePanels";
import {
  GuidedChecklist,
  ProgressSummary,
} from "@/components/qm";
import { AssessmentSectionNav } from "@/components/navigation/AssessmentSectionNav";
import { AssessmentLobby } from "@/pages/AssessmentLobby";
import { useAuditDashboard } from "@/hooks/useAuditDashboard";
import { JOURNEY_PHASES, phaseForStatus } from "@/lib/auditJourney";
import { labelAssessmentType } from "@/lib/labels";

/**
 * Overview: dados reais via hooks existentes; visual via AssessmentLobby + cards.
 * Sem alteração de regras de negócio / API.
 */
export function AssessmentOverviewPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const navigate = useNavigate();
  const dash = useAuditDashboard(assessmentId);

  if (!assessmentId) {
    return (
      <ApiErrorBanner
        title="Avaliação não encontrada"
        error={new Error("Identificador ausente")}
      />
    );
  }

  if (dash.loading) {
    return <LoadingPanel title="Montando o mapa da avaliação…" />;
  }

  if (!dash.assessment) {
    return (
      <ApiErrorBanner
        title="Não foi possível abrir a avaliação"
        error={new Error("Avaliação não encontrada nesta organização")}
      />
    );
  }

  const a = dash.assessment;
  const phaseId = phaseForStatus(a.status, {
    preparationReady: dash.preparationReady,
  });
  const phase = JOURNEY_PHASES.find((p) => p.id === phaseId)!;

  const prepBlockers =
    a.status === "draft" && !dash.preparationReady ? dash.pending : [];
  const planningHints =
    a.status === "draft" && dash.preparationReady ? dash.pending : [];

  return (
    <div className="space-y-6">
      <AssessmentSectionNav assessmentId={assessmentId} />
      <AssessmentLobby
        status={a.status}
        preparationReady={dash.preparationReady}
        percent={dash.percent}
        pendingCount={dash.pending.length}
        pending={dash.pending}
        assessmentId={assessmentId}
        modalityLabel={labelAssessmentType(a.type)}
        assessmentName={labelAssessmentType(a.type)}
        organizationName={dash.organizationName}
        progressLabel={`${dash.percent}% do percurso · fase: ${phase.label}`}
        nextTitle={dash.nextBest.title}
        nextDescription={dash.nextBest.description}
        nextActionText={dash.continueAction.label || dash.nextBest.actionText}
        blockers={prepBlockers}
        onContinue={() => {
          void navigate(dash.continueAction.href);
        }}
        onResolveBlocker={() => {
          void navigate(
            dash.preparationReady
              ? dash.continueAction.href
              : `/assessments/${assessmentId}/guided`,
          );
        }}
      />

      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <ProgressSummary
          caption="Números reais desta organização."
          items={[
            { label: "Progresso geral", value: `${dash.percent}%` },
            { label: "Fase atual", value: phase.label },
            {
              label: "Roteiro",
              value: `${dash.counts.guidedAnswered}/${dash.counts.guidedTotal || "—"}`,
            },
            {
              label: "Evidências",
              value: String(dash.counts.evidences),
            },
          ]}
        />
        <GuidedChecklist
          title={
            a.status === "draft" && dash.preparationReady
              ? "Para confirmar o Planejamento"
              : "Nesta fase"
          }
          items={dash.checklist}
          pending={
            a.status === "draft" && dash.preparationReady
              ? planningHints
              : dash.pending
          }
          resolveHint={
            a.status === "draft" && dash.preparationReady
              ? planningHints.length > 0
                ? "Abra o Planejamento e resolva os itens listados — o botão de confirmar só libera quando estiverem ok."
                : "Escopo e equipe ok — confirme o planejamento na próxima tela."
              : "Use o botão de próxima etapa acima. Se algo faltar, o motivo aparece em destaque."
          }
        />
      </div>
    </div>
  );
}
