import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import { getQmindClient, withTenantGeneration } from "@/api/qmindApi";
import { queryKeys } from "@/api/queryKeys";
import { useAssessment, useAssessmentScopes } from "@/hooks/useAssessmentDetail";
import { useGuidedSession } from "@/hooks/useGuidedAssessment";
import {
  consistencyScore,
  continueHref,
  isPreparationReady,
  overallPercent,
  preparationChecklist,
  statusIndex,
} from "@/lib/auditJourney";

export function useAuditDashboard(assessmentId: string | undefined) {
  const { currentOrganizationId, currentOrganization } = useOrganization();
  const assessment = useAssessment(assessmentId);
  const scopes = useAssessmentScopes(assessmentId);
  // Lê sessão guided quando existir (get_or_create só cria em draft/planned).
  const guided = useGuidedSession(assessmentId);

  const orgId = currentOrganizationId;
  const aid = assessmentId;

  const extras = useQueries({
    queries: [
      {
        queryKey:
          orgId && aid
            ? queryKeys.assessmentInterviews(orgId, aid)
            : ["org", "none", "interviews"],
        enabled: !!orgId && !!aid,
        queryFn: async () => {
          const client = getQmindClient();
          return withTenantGeneration(async () => {
            const res = await client.api.listAssessmentInterviews({
              path: { assessment_id: aid! },
            });
            return res.data ?? [];
          });
        },
      },
      {
        queryKey:
          orgId && aid
            ? queryKeys.assessmentEvidences(orgId, aid)
            : ["org", "none", "evidences"],
        enabled: !!orgId && !!aid,
        queryFn: async () => {
          const client = getQmindClient();
          return withTenantGeneration(async () => {
            const res = await client.api.listAssessmentEvidences({
              path: { assessment_id: aid! },
            });
            return res.data ?? [];
          });
        },
      },
      {
        queryKey:
          orgId && aid
            ? queryKeys.assessmentFindings(orgId, aid)
            : ["org", "none", "findings"],
        enabled: !!orgId && !!aid,
        queryFn: async () => {
          const client = getQmindClient();
          return withTenantGeneration(async () => {
            const res = await client.api.listFindings({
              query: { assessment_id: aid! },
            });
            return res.data ?? [];
          });
        },
      },
      {
        queryKey:
          orgId && aid
            ? queryKeys.assessmentActionPlans(orgId, aid)
            : ["org", "none", "plans"],
        enabled: !!orgId && !!aid,
        queryFn: async () => {
          const client = getQmindClient();
          return withTenantGeneration(async () => {
            const res = await client.api.listActionPlans({
              query: { assessment_id: aid! },
            });
            return res.data ?? [];
          });
        },
      },
      {
        queryKey:
          orgId && aid
            ? queryKeys.assessmentReports(orgId, aid)
            : ["org", "none", "reports"],
        enabled: !!orgId && !!aid,
        queryFn: async () => {
          const client = getQmindClient();
          return withTenantGeneration(async () => {
            const res = await client.api.listReports({
              query: { assessment_id: aid! },
            });
            return res.data ?? [];
          });
        },
      },
    ],
  });

  const [interviewsQ, evidencesQ, findingsQ, plansQ, reportsQ] = extras;

  return useMemo(() => {
    const a = assessment.data;
    const status = a?.status;
    const ctx = guided.data?.context;
    const answers = guided.data?.answers ?? [];
    const answered = guided.data?.answered_count ?? 0;
    const qTotal = guided.data?.question_count ?? 0;
    const withEvidenceOrLater = answers.filter(
      (x) =>
        x.provide_later ||
        (x.evidence_ids?.length ?? 0) > 0 ||
        !!x.evidence_note?.trim() ||
        x.evidence_mode === "describe" ||
        x.evidence_mode === "attach" ||
        x.evidence_mode === "link_existing",
    ).length;
    const withDescription = answers.filter((x) => !!x.description?.trim()).length;

    const prepSub =
      qTotal > 0 ? answered / qTotal : status === "draft" ? 0.15 : 0;
    const percent = overallPercent(status, prepSub);

    const interviews = interviewsQ.data ?? [];
    const evidences = evidencesQ.data ?? [];
    const findings = findingsQ.data ?? [];
    const plans = plansQ.data ?? [];
    const reports = reportsQ.data ?? [];

    const interviewsDone = interviews.filter((i) => i.status === "completed").length;
    const findingsOpen = findings.filter(
      (f) => f.status === "draft" || f.status === "in_review",
    ).length;
    const reportPublished = reports.some((r) => r.status === "published");

    const checklist = preparationChecklist({
      hasOrgProfile: !!ctx?.organization_profile?.trade_name?.trim(),
      hasScope: !!ctx?.qms_scope?.description?.trim(),
      hasProcesses: (ctx?.processes?.length ?? 0) > 0,
      answered,
      totalQuestions: qTotal,
      withEvidenceOrLater,
    });

    const preparationReady = isPreparationReady({
      currentStep: guided.data?.current_step,
      guidedStatus: guided.data?.status,
      checklistDone: checklist.every((c) => c.done),
    });

    const scopeItems = (scopes.data ?? []).length;
    const hasLead = !!a?.lead_membership_id;

    const continueAction = aid
      ? continueHref(aid, status, { preparationReady })
      : { href: "/assessments", label: "Voltar" };

    const pending: string[] = [];
    if (status === "draft" && !preparationReady) {
      checklist.filter((c) => !c.done).forEach((c) => pending.push(c.label));
    }
    if (status === "draft" && preparationReady) {
      if (scopeItems < 1) {
        pending.push(
          "Escopo formal: inclua pelo menos um item (requisito ou processo) no Planejamento",
        );
      }
      if (!hasLead) {
        pending.push("Equipe: confirme o líder da avaliação no Planejamento");
      }
    }
    if (status === "in_progress" && interviewsDone === 0) {
      pending.push("Nenhuma entrevista concluída");
    }
    if (status === "analysis" && findings.length === 0) {
      pending.push("Nenhuma constatação registrada");
    }
    if (status === "actions" && plans.length === 0) {
      pending.push("Nenhum plano de ação criado");
    }
    if (status === "report" && !reportPublished) {
      pending.push("Relatório ainda não publicado");
    }

    const nextBest =
      status === "draft" && !preparationReady
        ? {
            title: "Continuar a preparação",
            description:
              "Ainda faltam itens da preparação. Conclua o roteiro e a checagem final antes de ir ao Planejamento.",
            actionText: "Continuar preparação",
          }
        : status === "draft" && preparationReady
          ? {
              title: "Ir para o Planejamento",
              description:
                scopeItems < 1 || !hasLead
                  ? "Preparação concluída. No Planejamento, confirme escopo formal e equipe — o que faltar aparece marcado na tela."
                  : "Preparação concluída. Confirme o plano e marque a avaliação como planejada para liberar a execução em campo.",
              actionText: "Ir para o Planejamento",
            }
          : {
              title: "Continuar a avaliação",
              description:
                "Siga na etapa atual do mapa. Se algo estiver bloqueado, o motivo aparece na tela.",
              actionText: continueAction.label,
            };

    return {
      loading:
        assessment.isLoading ||
        extras.some((q) => q.isLoading) ||
        (guided.isLoading && !guided.isError),
      assessment: a,
      organizationName:
        currentOrganization?.organizationName ?? currentOrganizationId ?? "—",
      scopes: scopes.data ?? [],
      status,
      statusIndex: statusIndex(status),
      percent,
      continueAction,
      preparationReady,
      nextBest,
      checklist,
      consistency: consistencyScore({
        answered,
        withEvidenceOrLater,
        withDescription,
      }),
      counts: {
        interviewsTotal: interviews.length,
        interviewsDone,
        evidences: evidences.length,
        findings: findings.length,
        findingsOpen,
        plans: plans.length,
        reports: reports.length,
        reportPublished,
        guidedAnswered: answered,
        guidedTotal: qTotal,
        scopeItems,
      },
      pending,
      guided,
    };
  }, [
    assessment.data,
    assessment.isLoading,
    guided.data,
    guided.isLoading,
    interviewsQ.data,
    evidencesQ.data,
    findingsQ.data,
    plansQ.data,
    reportsQ.data,
    extras,
    scopes.data,
    currentOrganization,
    currentOrganizationId,
    aid,
  ]);
}
