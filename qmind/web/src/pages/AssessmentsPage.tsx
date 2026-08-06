import { Link } from "react-router-dom";
import { useAssessments } from "@/hooks/useAssessments";
import { useOrganization } from "@/org/OrganizationProvider";
import { useAssessmentPermissions } from "@/hooks/useAssessmentPermissions";
import { AccessDeniedPanel, LoadingPanel } from "@/components/StatePanels";
import {
  ContextualHelp,
  GuidedEmptyState,
  PageHeader,
  StatusBadge,
  toneForAssessmentStatus,
} from "@/components/qm";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { QmindApiError } from "@/api/qmindApi";
import { labelAssessmentStatus, labelAssessmentType } from "@/lib/labels";
import {
  JOURNEY_PHASES,
  continueHref,
  phaseForStatus,
} from "@/lib/auditJourney";
import { OrgAgenda } from "@/components/OrgAgenda";
import { OrgJourneyOverview } from "@/components/orgJourney/OrgJourneyOverview";

export function AssessmentsPage() {
  const org = useOrganization();
  const perms = useAssessmentPermissions();
  const query = useAssessments();

  if (!org.currentOrganizationId) {
    return (
      <GuidedEmptyState
        title="Escolha uma organização para começar"
        why="Cada organização tem suas próprias avaliações. O progresso não se mistura entre elas."
        example="Se você participa de duas empresas, selecione no topo a que deseja trabalhar agora."
        howToStart="Use o seletor “Organização” no cabeçalho."
      />
    );
  }

  if (query.isLoading) {
    return <LoadingPanel title="Carregando suas avaliações…" />;
  }

  if (query.isError) {
    const err = query.error;
    if (err instanceof QmindApiError && (err.status === 401 || err.status === 403)) {
      return <AccessDeniedPanel message={err.message} />;
    }
    return (
      <ApiErrorBanner
        title="Não foi possível carregar as avaliações"
        error={err}
        onRetry={() => void query.refetch()}
      />
    );
  }

  const items = query.data ?? [];
  const orgName =
    org.currentOrganization?.organizationName ?? "organização selecionada";

  return (
    <section className="space-y-6">
      <PageHeader
        title="Minhas avaliações"
        explanation={`Você está em ${orgName}. Aqui ficam os trabalhos em andamento e concluídos. Abra um item para ver o mapa do percurso, ou inicie um novo.`}
        expectedResult="Uma avaliação aberta com fase clara e próxima ação evidente."
        nextStep={
          items.length === 0
            ? "Criar a primeira avaliação"
            : "Abrir a avaliação em que deseja continuar"
        }
        actions={
          perms.canMutate ? (
            <Link
              to="/assessments/new"
              className="qm-btn-primary shrink-0"
              data-testid="new-assessment"
            >
              Nova avaliação
            </Link>
          ) : undefined
        }
      />

      <ContextualHelp
        term="avaliação"
        example="“Diagnóstico inicial — Em preparação” significa: ainda estamos conhecendo a organização."
      >
        É o ciclo guiado de trabalho da qualidade — da preparação ao relatório. Não
        precisa conhecer ISO 9001 para começar: o QMind explica cada etapa.
      </ContextualHelp>

      <OrgJourneyOverview assessments={items} />

      <OrgAgenda />

      {items.length === 0 ? (
        <GuidedEmptyState
          title="Nenhuma avaliação ainda"
          why="Este é o ponto de partida do trabalho nesta organização."
          example="Uma avaliação nova começa pela preparação: conhecer a organização e responder a um roteiro em linguagem de negócio."
          howToStart="Toque em “Criar primeira avaliação”. Em seguida o mapa mostra o percurso completo."
          action={
            perms.canMutate
              ? { label: "Criar primeira avaliação", to: "/assessments/new" }
              : undefined
          }
        />
      ) : (
        <ul className="audit-list" data-testid="assessments-list">
          {items.map((a) => {
            const phase = JOURNEY_PHASES.find(
              (p) => p.id === phaseForStatus(a.status),
            );
            const next = continueHref(a.id, a.status);
            return (
              <li key={a.id}>
                <Link to={`/assessments/${a.id}`} className="audit-list__row">
                  <div className="min-w-0">
                    <p className="font-semibold text-[var(--qm-ink)]">
                      {labelAssessmentType(a.type)}
                    </p>
                    <p className="mt-1 flex flex-wrap items-center gap-2 text-sm">
                      <StatusBadge
                        label={labelAssessmentStatus(a.status)}
                        tone={toneForAssessmentStatus(a.status)}
                      />
                      <span className="text-[var(--qm-muted)]">
                        Fase: {phase?.label ?? "—"}
                      </span>
                    </p>
                    <p className="mt-1 text-sm font-semibold text-[var(--qm-accent)]">
                      Próxima etapa: {next.label}
                    </p>
                  </div>
                  <span className="audit-list__phase">{phase?.label ?? "—"}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
