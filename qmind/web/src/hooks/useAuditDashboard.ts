import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import { getQmindClient, withTenantGeneration } from "@/api/qmindApi";
import { queryKeys } from "@/api/queryKeys";
import { useAssessment, useAssessmentScopes } from "@/hooks/useAssessmentDetail";
import { useGuidedSession } from "@/hooks/useGuidedAssessment";
import { useAuditPlan } from "@/hooks/useAuditPlan";
import { useAuditPlanSchedule } from "@/hooks/useAuditPlanSchedule";
import {
  consistencyScore,
  continueHref,
  isPreparationReady,
  overallPercent,
  preparationChecklist,
  statusIndex,
} from "@/lib/auditJourney";
import {
  auditPlanDiscoveryAction,
  auditPlanDiscoveryLabel,
  auditPlanDiscoveryState,
} from "@/lib/auditPlanDiscovery";

export function useAuditDashboard(assessmentId: string | undefined) {
  const { currentOrganizationId, currentOrganization } = useOrganization();
  const assessment = useAssessment(assessmentId);
  const scopes = useAssessmentScopes(assessmentId);
  // Lê sessão guided quando existir (get_or_create só cria em draft/planned).
  const guided = useGuidedSession(assessmentId);
  const auditPlan = useAuditPlan(assessmentId);
  const schedule = useAuditPlanSchedule(assessmentId);

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
        (x.evidence_links?.length ?? x.evidence_ids?.length ?? 0) > 0 ||
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
    const planReady =
      auditPlan.data?.plan_status === "ready" ||
      auditPlan.data?.plan_status === "amended";
    const planPercent = auditPlan.data?.readiness?.percent ?? 0;

    const scheduleNext = schedule.data?.next_action;
    const hasOverlap = (schedule.data?.overlaps?.length ?? 0) > 0;
    const hasOpening = !!schedule.data?.has_opening_meeting;
    const plannedInterviews = interviews.filter(
      (i) => i.status === "planned" || i.status === "confirmed",
    ).length;

    const continueAction = aid
      ? continueHref(aid, status, { preparationReady })
      : { href: "/assessments", label: "Voltar" };

    const pending: string[] = [];
    if (status === "draft" && !preparationReady) {
      checklist.filter((c) => !c.done).forEach((c) => pending.push(c.label));
    }
    if (
      (status === "draft" && preparationReady) ||
      status === "planned"
    ) {
      if (!planReady) {
        const next = auditPlan.data?.readiness?.next_action;
        pending.push(
          next
            ? `Plano da Auditoria: ${next}`
            : "Elaborar o Plano da Auditoria no Planejamento",
        );
      }
      if (!hasOpening) {
        pending.push("Confirmar reunião de abertura");
      }
      if (hasOverlap) {
        pending.push("Resolver conflito de horário");
      }
      if (planReady && plannedInterviews === 0) {
        pending.push("Agendar entrevista");
      } else if (scheduleNext && planReady) {
        pending.push(scheduleNext);
      } else if (!planReady && scheduleNext) {
        pending.push(`Programação: ${scheduleNext}`);
      }
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
      if (plannedInterviews > 0) {
        pending.push("Iniciar primeira entrevista");
      } else {
        pending.push("Nenhuma entrevista concluída");
      }
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

    const planDiscovery = aid
      ? auditPlanDiscoveryAction(aid, auditPlan.data, status)
      : null;
    const planState = auditPlanDiscoveryState(auditPlan.data);

    const continueActionResolved = (() => {
      if (!aid) return continueAction;
      if (hasOverlap) {
        return {
          href: `/assessments/${aid}/audit-plan`,
          label: "Resolver conflito de horário",
        };
      }
      if (
        (status === "draft" && preparationReady) ||
        status === "planned"
      ) {
        if (planDiscovery) return planDiscovery;
      }
      if (
        status === "in_progress" &&
        plannedInterviews > 0 &&
        interviewsDone === 0
      ) {
        return {
          href: `/assessments/${aid}/audit-plan`,
          label: "Iniciar primeira entrevista",
        };
      }
      return continueAction;
    })();

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
              title:
                planState === "not_started"
                  ? "Criar o Plano da Auditoria"
                  : planState === "in_progress"
                    ? "Continuar o Plano da Auditoria"
                    : "Revisar a programação",
              description:
                planState === "ready" || planState === "amended"
                  ? "Plano pronto. Revise a programação ou confirme o planejamento para liberar a execução em campo."
                  : "Monte o plano operacional (propósito, processos, pessoas, período e programação) antes de ir a campo.",
              actionText: continueActionResolved.label,
            }
          : status === "planned"
            ? {
                title:
                  planState === "amended"
                    ? "Revisar emenda do plano"
                    : planReady
                      ? "Iniciar execução em campo"
                      : "Continuar o Plano da Auditoria",
                description:
                  planState === "amended"
                    ? "Há emenda pendente: revise, reconfirme o plano e só então inicie o campo."
                    : planReady
                      ? "Com o plano pronto, registre a abertura (ou dispensa) e inicie a execução em campo."
                      : "Ainda há pendências no Plano da Auditoria antes de iniciar o campo.",
                actionText: continueActionResolved.label,
              }
            : {
                title: "Continuar a avaliação",
                description:
                  "Siga na etapa atual do mapa. Se algo estiver bloqueado, o motivo aparece na tela.",
                actionText: continueActionResolved.label,
              };

    return {
      loading:
        assessment.isLoading ||
        extras.some((q) => q.isLoading) ||
        (guided.isLoading && !guided.isError && !guided.isUnavailableInPhase) ||
        (auditPlan.isLoading && !auditPlan.isError) ||
        (schedule.isLoading && !schedule.isError),
      assessment: a,
      organizationName:
        currentOrganization?.organizationName ?? currentOrganizationId ?? "—",
      scopes: scopes.data ?? [],
      status,
      statusIndex: statusIndex(status),
      percent,
      continueAction: continueActionResolved,
      preparationReady,
      auditPlanReady: planReady,
      auditPlanPercent: planPercent,
      auditPlanDiscoveryLabel: auditPlanDiscoveryLabel(auditPlan.data),
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
    guided.isError,
    guided.isUnavailableInPhase,
    auditPlan.data,
    auditPlan.isLoading,
    auditPlan.isError,
    schedule.data,
    schedule.isLoading,
    schedule.isError,
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
