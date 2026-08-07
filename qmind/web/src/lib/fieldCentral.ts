import type { AuditPlan } from "@/api/auditPlanTypes";
import type { AuditPlanSchedule, ScheduleItem } from "@/api/auditPlanScheduleTypes";
import { planStatusLabel } from "@/api/auditPlanTypes";
import { labelAssessmentType, labelWorkflowStatus } from "@/lib/labels";
import type {
  EvidenceBucket,
  EvidenceBucketKey,
  FieldAssistantContext,
  FieldCentralModel,
  FieldClosingPrep,
  FieldNextAction,
  FieldPendency,
  FieldPhaseMode,
  FieldProgress,
  FieldTodayItem,
} from "@/lib/fieldCentralTypes";

type InterviewLike = {
  id: string;
  title?: string | null;
  status: string;
  process_name?: string | null;
  objective?: string | null;
  scheduled_at?: string | null;
  location?: string | null;
  remote_link?: string | null;
  preparation?: string | null;
  org_contact_name?: string | null;
};

type EvidenceLike = {
  id: string;
  status: string;
  created_at?: string | null;
  interview_id?: string | null;
  question_id?: string | null;
  collected_phase?: string | null;
  collection_origin?: string | null;
};

type AssessmentLike = {
  id: string;
  organization_id: string;
  status: string;
  type: string;
  started_at?: string | null;
};

export type BuildFieldCentralInput = {
  organizationId: string;
  organizationName: string;
  assessment: AssessmentLike;
  plan: AuditPlan | null | undefined;
  schedule: AuditPlanSchedule | null | undefined;
  interviews: InterviewLike[];
  evidences: EvidenceLike[];
  scopeLabels: string[];
  roles: string[];
  canMutate: boolean;
  now?: Date;
};

function dayKey(iso: string | null | undefined, tz: string, now: Date): string | null {
  if (!iso) return null;
  try {
    return new Intl.DateTimeFormat("en-CA", {
      timeZone: tz || "America/Sao_Paulo",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso.slice(0, 10);
  }
}

function todayKey(tz: string, now: Date): string {
  try {
    return new Intl.DateTimeFormat("en-CA", {
      timeZone: tz || "America/Sao_Paulo",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(now);
  } catch {
    return now.toISOString().slice(0, 10);
  }
}

function formatTodayLabel(tz: string, now: Date): string {
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      timeZone: tz || "America/Sao_Paulo",
      weekday: "long",
      day: "numeric",
      month: "long",
    }).format(now);
  } catch {
    return now.toLocaleDateString("pt-BR");
  }
}

function modeForStatus(status: string): FieldPhaseMode {
  if (status === "draft") return "draft_redirect";
  if (status === "planned") return "planned_handoff";
  if (status === "in_progress") return "field_active";
  return "field_readonly";
}

function openingState(schedule: AuditPlanSchedule | null | undefined): {
  present: boolean;
  satisfied: boolean;
  status: string | null;
  eventId: string | null;
} {
  const opening = (schedule?.items ?? []).find(
    (i) =>
      i.plan_activity_kind === "opening_meeting" && i.status !== "cancelled",
  );
  if (!opening) {
    return { present: false, satisfied: false, status: null, eventId: null };
  }
  return {
    present: true,
    satisfied: opening.status === "completed" || opening.status === "waived",
    status: opening.status,
    eventId: opening.id,
  };
}

function openingStatusLabel(status: string | null): string | null {
  if (!status) return null;
  if (status === "completed") return "Realizada";
  if (status === "waived") return "Dispensada";
  if (status === "scheduled") return "Programada";
  return labelWorkflowStatus(status);
}

function toTodayItem(item: ScheduleItem): FieldTodayItem {
  const done =
    item.status === "completed" ||
    item.status === "waived" ||
    item.status === "cancelled";
  let primaryLabel = item.primary_action_label || item.next_action || "Abrir";
  if (item.kind === "interview") {
    if (item.status === "in_progress") primaryLabel = "Continuar entrevista";
    else if (item.status === "planned" || item.status === "confirmed")
      primaryLabel = "Iniciar entrevista";
    else if (item.status === "completed") primaryLabel = "Ver entrevista";
  }
  if (item.plan_activity_kind === "opening_meeting" && !done) {
    primaryLabel = "Registrar reunião de abertura";
  }
  return {
    id: item.id,
    kind: item.kind,
    title: item.title || "Atividade",
    status: item.status,
    statusLabel: labelWorkflowStatus(item.status),
    startsAt: item.starts_at ?? null,
    processName: item.process_name || "",
    locationOrLink: item.location_or_link || "",
    preparation: item.preparation || "",
    objective: item.objective || "",
    interviewId: item.interview_id ?? null,
    planActivityKind: item.plan_activity_kind ?? null,
    done,
    primaryLabel,
  };
}

function buildTodayItems(
  schedule: AuditPlanSchedule | null | undefined,
  interviews: InterviewLike[],
  now: Date,
): FieldTodayItem[] {
  const tz = schedule?.timezone || "America/Sao_Paulo";
  const today = todayKey(tz, now);
  const fromSchedule = (schedule?.items ?? [])
    .filter((i) => i.status !== "cancelled")
    .filter((i) => {
      const d = dayKey(i.starts_at, tz, now);
      return d === today || (!i.starts_at && i.kind === "interview" && !["completed"].includes(i.status));
    })
    .map(toTodayItem);

  const scheduledIvIds = new Set(
    fromSchedule.map((i) => i.interviewId).filter(Boolean),
  );
  const orphanToday = interviews
    .filter((iv) => {
      if (scheduledIvIds.has(iv.id)) return false;
      if (iv.status === "cancelled") return false;
      const d = dayKey(iv.scheduled_at, tz, now);
      return (
        d === today ||
        iv.status === "in_progress" ||
        (!iv.scheduled_at && iv.status !== "completed")
      );
    })
    .map((iv): FieldTodayItem => {
      const done = iv.status === "completed";
      return {
        id: iv.id,
        kind: "interview",
        title: iv.title || iv.process_name || "Entrevista",
        status: iv.status,
        statusLabel: labelWorkflowStatus(iv.status),
        startsAt: iv.scheduled_at ?? null,
        processName: iv.process_name || "",
        locationOrLink: iv.location || iv.remote_link || "",
        preparation: iv.preparation || "",
        objective: iv.objective || "",
        interviewId: iv.id,
        planActivityKind: null,
        done,
        primaryLabel:
          iv.status === "in_progress"
            ? "Continuar entrevista"
            : iv.status === "completed"
              ? "Ver entrevista"
              : "Iniciar entrevista",
      };
    });

  return [...fromSchedule, ...orphanToday].sort((a, b) => {
    if (a.done !== b.done) return a.done ? 1 : -1;
    return (a.startsAt || "").localeCompare(b.startsAt || "");
  });
}

function classifyEvidence(
  evidences: EvidenceLike[],
  startedAt: string | null | undefined,
): EvidenceBucket[] {
  const buckets: Record<EvidenceBucketKey, string[]> = {
    early: [],
    field: [],
    verifying: [],
    pending_review: [],
    pending: [],
    rejected: [],
  };
  const startMs = startedAt ? Date.parse(startedAt) : NaN;

  for (const e of evidences) {
    if (e.status === "rejected" || e.status === "disposed") {
      buckets.rejected.push(e.id);
      continue;
    }
    if (e.status === "upload_pending") {
      buckets.pending.push(e.id);
      continue;
    }
    if (e.status === "quarantined" || e.status === "pending_disposal") {
      buckets.verifying.push(e.id);
      buckets.pending_review.push(e.id);
      continue;
    }
    if (e.status === "approved") {
      const created = e.created_at ? Date.parse(e.created_at) : NaN;
      const phase = (e.collected_phase || e.collection_origin || "").toLowerCase();
      const earlyByPhase =
        phase.includes("prep") ||
        phase.includes("guided") ||
        phase.includes("early") ||
        phase.includes("advance");
      const earlyByTime =
        !e.interview_id &&
        (Number.isNaN(startMs) || Number.isNaN(created) || created < startMs);
      if (earlyByPhase || earlyByTime) buckets.early.push(e.id);
      else buckets.field.push(e.id);
      continue;
    }
    buckets.pending.push(e.id);
  }

  const meta: Record<
    EvidenceBucketKey,
    { label: string; explanation: string }
  > = {
    early: {
      label: "Disponíveis antecipadamente",
      explanation:
        "Já aprovadas antes do campo — podem ser vinculadas sem novo upload.",
    },
    field: {
      label: "Coletadas em campo",
      explanation: "Recebidas ou vinculadas durante a execução.",
    },
    verifying: {
      label: "Em verificação",
      explanation: "Em quarentena — arquivo ainda não é conformidade.",
    },
    pending_review: {
      label: "Aguardando revisão",
      explanation: "Precisam de verificação de segurança antes do uso.",
    },
    pending: {
      label: "Pendentes",
      explanation: "Envio incompleto ou aguardando confirmação.",
    },
    rejected: {
      label: "Rejeitadas",
      explanation: "Não utilizáveis — corrija ou substitua.",
    },
  };

  return (Object.keys(meta) as EvidenceBucketKey[]).map((key) => ({
    key,
    label: meta[key].label,
    explanation: meta[key].explanation,
    count: buckets[key].length,
    evidenceIds: buckets[key],
  }));
}

function buildPendencies(input: {
  mode: FieldPhaseMode;
  plan: AuditPlan | null | undefined;
  schedule: AuditPlanSchedule | null | undefined;
  interviews: InterviewLike[];
  evidences: EvidenceLike[];
  opening: ReturnType<typeof openingState>;
  assessmentId: string;
  now: Date;
}): FieldPendency[] {
  const { mode, plan, schedule, interviews, evidences, opening, assessmentId, now } =
    input;
  const out: FieldPendency[] = [];
  const tz = schedule?.timezone || "America/Sao_Paulo";
  const today = todayKey(tz, now);

  if (mode === "draft_redirect") {
    out.push({
      key: "go_plan",
      problem: "A avaliação ainda está em preparação",
      impact: "Não há execução em campo nesta fase",
      actionLabel: "Abrir Plano da Auditoria",
      href: `/assessments/${assessmentId}/audit-plan`,
    });
    return out;
  }

  if (mode === "planned_handoff") {
    if (plan?.plan_status === "amended") {
      out.push({
        key: "plan_amended",
        problem: "Há emenda pendente no plano",
        impact: "O início do campo fica bloqueado até reconfirmação",
        actionLabel: "Revisar emenda",
        href: `/assessments/${assessmentId}/audit-plan`,
      });
    } else if (!plan || plan.plan_status !== "ready") {
      out.push({
        key: "plan_not_ready",
        problem: "Plano da Auditoria ainda não está pronto",
        impact: "Não é possível iniciar a execução com segurança",
        actionLabel: "Continuar Plano da Auditoria",
        href: `/assessments/${assessmentId}/audit-plan`,
      });
    }
    if (!opening.satisfied) {
      out.push({
        key: "opening",
        problem: opening.present
          ? "Reunião de abertura ainda não registrada"
          : "Reunião de abertura não programada",
        impact: "É pré-requisito para iniciar o campo",
        actionLabel: opening.present
          ? "Registrar reunião de abertura"
          : "Programar abertura no Plano",
        href: `/assessments/${assessmentId}/audit-plan`,
        localAction: "focus_opening",
      });
    }
    return out;
  }

  if (mode === "field_active") {
    for (const iv of interviews) {
      if (iv.status === "cancelled") {
        out.push({
          key: `cancelled-${iv.id}`,
          problem: `Entrevista cancelada: ${iv.title || iv.process_name || "sem título"}`,
          impact: "Pode deixar processo sem cobertura se não for reagendada",
          actionLabel: "Registrar atividade ou reagendar",
          localAction: "focus_unplanned",
          interviewId: iv.id,
        });
      }
      const d = dayKey(iv.scheduled_at, tz, now);
      if (
        (iv.status === "planned" || iv.status === "confirmed") &&
        d &&
        d < today
      ) {
        out.push({
          key: `late-${iv.id}`,
          problem: `Entrevista atrasada: ${iv.title || iv.process_name || "atividade"}`,
          impact: "O dia ficou sem o registro planejado",
          actionLabel: "Iniciar ou reagendar",
          localAction: "focus_interview",
          interviewId: iv.id,
        });
      }
    }

    const plannedProcesses = new Set(
      (plan?.processes ?? [])
        .map((p) => (p.name || "").trim())
        .filter(Boolean),
    );
    const covered = new Set(
      interviews
        .filter((i) => i.status === "completed" || i.status === "in_progress")
        .map((i) => (i.process_name || "").trim())
        .filter(Boolean),
    );
    for (const name of plannedProcesses) {
      const justified = (plan?.processes ?? []).find(
        (p) => p.name === name && (p.interview_justification || "").trim(),
      );
      if (!covered.has(name) && !justified) {
        out.push({
          key: `process-${name}`,
          problem: `Processo sem entrevista: ${name}`,
          impact: "Cobertura do plano fica incompleta",
          actionLabel: "Iniciar entrevista ou justificar",
          localAction: "focus_unplanned",
        });
      }
    }

    for (const e of evidences) {
      if (e.status === "rejected") {
        out.push({
          key: `ev-rej-${e.id}`,
          problem: "Evidência rejeitada na verificação",
          impact: "Não pode fundamentar constatações",
          actionLabel: "Substituir evidência",
          localAction: "focus_evidence",
        });
      }
      if (e.status === "quarantined" || e.status === "upload_pending") {
        out.push({
          key: `ev-pend-${e.id}`,
          problem: "Evidência ainda em verificação ou envio",
          impact: "Não conte como comprovação até aprovação",
          actionLabel: "Revisar evidências",
          localAction: "focus_evidence",
        });
      }
    }

    const hasClosing = !!schedule?.has_closing_meeting;
    const closingDone = (schedule?.items ?? []).some(
      (i) =>
        i.plan_activity_kind === "closing_meeting" &&
        (i.status === "completed" || i.status === "scheduled"),
    );
    const interviewsLeft = interviews.filter(
      (i) =>
        i.status === "planned" ||
        i.status === "confirmed" ||
        i.status === "in_progress",
    ).length;
    if (interviewsLeft === 0 && interviews.some((i) => i.status === "completed")) {
      if (!hasClosing || !closingDone) {
        out.push({
          key: "closing_prep",
          problem: "Reunião de encerramento ainda não preparada",
          impact: "O fechamento do campo fica improvisado",
          actionLabel: "Preparar encerramento",
          localAction: "focus_closing",
          href: `/assessments/${assessmentId}/audit-plan`,
        });
      }
    }
  }

  return out;
}

function buildNextAction(input: {
  mode: FieldPhaseMode;
  assessmentId: string;
  plan: AuditPlan | null | undefined;
  opening: ReturnType<typeof openingState>;
  interviews: InterviewLike[];
  evidences: EvidenceLike[];
  pendencies: FieldPendency[];
  canMutate: boolean;
}): FieldNextAction {
  const { mode, assessmentId, plan, opening, interviews, evidences, pendencies, canMutate } =
    input;

  if (mode === "draft_redirect") {
    return {
      kind: "open_audit_plan",
      label: "Abrir Plano da Auditoria",
      hint: "A Central de Campo só faz sentido depois do planejamento.",
      href: `/assessments/${assessmentId}/audit-plan`,
    };
  }

  if (mode === "planned_handoff") {
    if (plan?.plan_status === "amended") {
      return {
        kind: "resolve_blocker",
        label: "Revisar emenda do plano",
        hint: "Há mudança pendente — reconfirme o plano antes de iniciar o campo.",
        href: `/assessments/${assessmentId}/audit-plan`,
      };
    }
    if (!plan || plan.plan_status !== "ready") {
      return {
        kind: "open_audit_plan",
        label: "Concluir Plano da Auditoria",
        hint: "Finalize o checklist do plano para liberar o início.",
        href: `/assessments/${assessmentId}/audit-plan`,
      };
    }
    if (!opening.satisfied) {
      return {
        kind: "opening_meeting",
        label: "Realizar reunião de abertura",
        hint: "Registre a realização ou dispense com justificativa no Plano.",
        href: `/assessments/${assessmentId}/audit-plan`,
        eventId: opening.eventId ?? undefined,
        localAction: "focus_opening",
      };
    }
    return {
      kind: "open_audit_plan",
      label: "Iniciar execução em campo",
      hint: "Tudo pronto — inicie pelo Plano da Auditoria (handoff oficial).",
      href: `/assessments/${assessmentId}/audit-plan`,
    };
  }

  if (mode === "field_readonly") {
    return {
      kind: "go_analysis",
      label: "Ir à fase atual",
      hint: "A execução em campo foi encerrada. Continue no mapa da avaliação.",
      href: `/assessments/${assessmentId}`,
    };
  }

  // field_active
  const blocker = pendencies.find((p) =>
    ["plan_amended", "opening"].includes(p.key),
  );
  if (blocker) {
    return {
      kind: "resolve_blocker",
      label: blocker.actionLabel,
      hint: blocker.impact,
      href: blocker.href,
      localAction: blocker.localAction,
      interviewId: blocker.interviewId,
    };
  }

  const inProgress = interviews.find((i) => i.status === "in_progress");
  if (inProgress) {
    return {
      kind: "continue_interview",
      label: "Continuar entrevista",
      hint: `Retome: ${inProgress.title || inProgress.process_name || "entrevista em andamento"}.`,
      interviewId: inProgress.id,
      localAction: "focus_interview",
    };
  }

  const nextIv = interviews.find(
    (i) => i.status === "planned" || i.status === "confirmed",
  );
  if (nextIv && canMutate) {
    return {
      kind: "start_interview",
      label: "Iniciar entrevista",
      hint: `Próxima: ${nextIv.title || nextIv.process_name || "entrevista confirmada"}.`,
      interviewId: nextIv.id,
      localAction: "focus_interview",
    };
  }

  const needsEv = evidences.some(
    (e) =>
      e.status === "quarantined" ||
      e.status === "upload_pending" ||
      e.status === "rejected",
  );
  if (needsEv) {
    return {
      kind: "review_evidence",
      label: "Revisar evidências",
      hint: "Há evidências pendentes, em verificação ou rejeitadas.",
      localAction: "focus_evidence",
    };
  }

  if (canMutate && interviews.every((i) => i.status === "completed" || i.status === "cancelled")) {
    return {
      kind: "prepare_closing",
      label: "Preparar encerramento do campo",
      hint: "Atividades previstas concluídas — revise cobertura e a reunião de encerramento.",
      localAction: "focus_closing",
      href: `/assessments/${assessmentId}/audit-plan`,
    };
  }

  if (canMutate) {
    return {
      kind: "register_unplanned",
      label: "Registrar atividade não planejada",
      hint: "Se surgir algo no campo, registre com motivo para manter o rastro.",
      localAction: "focus_unplanned",
    };
  }

  return {
    kind: "none",
    label: "Acompanhar o campo",
    hint: "Seu papel é somente leitura nesta organização.",
  };
}

function buildProgress(
  interviews: InterviewLike[],
  plan: AuditPlan | null | undefined,
  schedule: AuditPlanSchedule | null | undefined,
  evidences: EvidenceLike[],
): FieldProgress {
  const interviewsPlanned = interviews.filter((i) => i.status !== "cancelled").length;
  const interviewsDone = interviews.filter((i) => i.status === "completed").length;
  const processesPlanned = (plan?.processes ?? []).filter((p) => p.name.trim()).length;
  const covered = new Set(
    interviews
      .filter((i) => i.status === "completed")
      .map((i) => (i.process_name || "").trim())
      .filter(Boolean),
  );
  const processesCovered = covered.size;
  const evidencesReady = evidences.filter((e) => e.status === "approved").length;
  const evidencesPending = evidences.filter((e) =>
    ["upload_pending", "quarantined", "rejected"].includes(e.status),
  ).length;
  const schedItems = (schedule?.items ?? []).filter((i) => i.status !== "cancelled");
  const activitiesPlanned = schedItems.length;
  const activitiesDone = schedItems.filter(
    (i) => i.status === "completed" || i.status === "waived",
  ).length;

  const parts: string[] = [];
  if (interviewsPlanned > 0) {
    parts.push(`${interviewsDone} de ${interviewsPlanned} entrevistas concluídas`);
  } else {
    parts.push("Nenhuma entrevista prevista ainda");
  }
  if (processesPlanned > 0) {
    parts.push(`${processesCovered} de ${processesPlanned} processos cobertos`);
  }
  if (evidencesReady + evidencesPending > 0) {
    parts.push(
      `${evidencesReady} evidências disponíveis` +
        (evidencesPending ? `, ${evidencesPending} pendentes/em verificação` : ""),
    );
  }

  return {
    interviewsDone,
    interviewsPlanned,
    processesCovered,
    processesPlanned,
    evidencesReady,
    evidencesPending,
    activitiesDone,
    activitiesPlanned,
    summary: parts.join(" · "),
  };
}

function buildClosingPrep(input: {
  mode: FieldPhaseMode;
  interviews: InterviewLike[];
  plan: AuditPlan | null | undefined;
  evidences: EvidenceLike[];
  schedule: AuditPlanSchedule | null | undefined;
}): FieldClosingPrep {
  const { mode, interviews, plan, evidences, schedule } = input;
  const activeLeft = interviews.filter((i) =>
    ["planned", "confirmed", "in_progress"].includes(i.status),
  );
  const completed = interviews.filter((i) => i.status === "completed");
  const show =
    mode === "field_active" &&
    activeLeft.length === 0 &&
    completed.length > 0;

  const covered = completed.map(
    (i) => i.title || i.process_name || "Entrevista concluída",
  );
  const interviewsSkipped = interviews
    .filter((i) => i.status === "cancelled")
    .map((i) => i.title || i.process_name || "Entrevista cancelada");
  const pending = (plan?.processes ?? [])
    .filter((p) => {
      const name = p.name.trim();
      if (!name) return false;
      const has = completed.some((i) => (i.process_name || "").trim() === name);
      return !has && !(p.interview_justification || "").trim();
    })
    .map((p) => p.name);
  const evidencesWaiting = evidences
    .filter((e) =>
      ["quarantined", "upload_pending", "rejected"].includes(e.status),
    )
    .map((e) =>
      e.status === "rejected"
        ? "Evidência rejeitada"
        : "Evidência aguardando verificação",
    );
  const closingMeetingReady = (schedule?.items ?? []).some(
    (i) =>
      i.plan_activity_kind === "closing_meeting" && i.status !== "cancelled",
  );

  return {
    show,
    covered,
    pending,
    evidencesWaiting,
    interviewsSkipped,
    deepen: pending.slice(0, 3).map((p) => `Aprofundar ${p} na análise`),
    closingMeetingReady,
  };
}

export function buildFieldCentralModel(
  input: BuildFieldCentralInput,
): FieldCentralModel {
  const now = input.now ?? new Date();
  const mode = modeForStatus(input.assessment.status);
  const opening = openingState(input.schedule);
  const todayItems = buildTodayItems(input.schedule, input.interviews, now);
  const evidenceBuckets = classifyEvidence(
    input.evidences,
    input.assessment.started_at,
  );
  const pendencies = buildPendencies({
    mode,
    plan: input.plan,
    schedule: input.schedule,
    interviews: input.interviews,
    evidences: input.evidences,
    opening,
    assessmentId: input.assessment.id,
    now,
  });
  const nextAction = buildNextAction({
    mode,
    assessmentId: input.assessment.id,
    plan: input.plan,
    opening,
    interviews: input.interviews,
    evidences: input.evidences,
    pendencies,
    canMutate: input.canMutate,
  });
  const progress = buildProgress(
    input.interviews,
    input.plan,
    input.schedule,
    input.evidences,
  );
  const closingPrep = buildClosingPrep({
    mode,
    interviews: input.interviews,
    plan: input.plan,
    evidences: input.evidences,
    schedule: input.schedule,
  });

  const phaseLabel =
    mode === "field_active"
      ? "Execução em campo"
      : mode === "planned_handoff"
        ? "Planejada — início pendente"
        : mode === "draft_redirect"
          ? "Preparação"
          : "Campo encerrado";

  const current =
    todayItems.find((t) => !t.done) ||
    input.interviews.find((i) => i.status === "in_progress");

  const allowed_links = [
    `/assessments/${input.assessment.id}`,
    `/assessments/${input.assessment.id}/audit-plan`,
    `/assessments/${input.assessment.id}/work`,
  ];

  const assistantContext: FieldAssistantContext = {
    organization_id: input.organizationId,
    assessment_id: input.assessment.id,
    phase: input.assessment.status,
    page: "field_central",
    user_role_summary: input.roles,
    next_action: nextAction,
    current_activity_id:
      (current && "interviewId" in current
        ? current.interviewId
        : null) ||
      (current && "id" in current ? current.id : null) ||
      null,
    current_activity_title: (() => {
      if (!current) return null;
      if ("title" in current && current.title) return String(current.title);
      if ("process_name" in current) {
        const name = (current as InterviewLike).process_name;
        return name ? String(name) : null;
      }
      return null;
    })(),
    pendency_keys: pendencies.map((p) => p.key),
    blockers: pendencies
      .filter((p) =>
        ["plan_amended", "plan_not_ready", "opening"].includes(p.key),
      )
      .map((p) => p.problem),
    allowed_links,
  };

  return {
    mode,
    organizationName: input.organizationName,
    assessmentLabel: labelAssessmentType(input.assessment.type),
    modalityLabel: labelAssessmentType(
      input.plan?.modality || input.assessment.type,
    ),
    scopeSummary:
      input.scopeLabels.slice(0, 3).join(" · ") ||
      (input.plan?.scope_text || "").slice(0, 120) ||
      "Escopo conforme Plano da Auditoria",
    phaseLabel,
    todayLabel: formatTodayLabel(
      input.schedule?.timezone || "America/Sao_Paulo",
      now,
    ),
    planStatusLabel: input.plan
      ? planStatusLabel(input.plan.plan_status)
      : "Não iniciado",
    planReady: input.plan?.plan_status === "ready",
    openingSatisfied: opening.satisfied,
    openingStatusLabel: openingStatusLabel(opening.status),
    nextAction,
    todayItems,
    pendencies,
    evidenceBuckets,
    progress,
    closingPrep,
    canMutate: input.canMutate,
    assistantContext,
  };
}

/** Exposto para testes e futuro assistente. */
export function getFieldAssistantContext(
  model: FieldCentralModel,
): FieldAssistantContext {
  return model.assistantContext;
}
