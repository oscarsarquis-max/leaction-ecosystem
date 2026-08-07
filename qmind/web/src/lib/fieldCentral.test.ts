import { describe, expect, it } from "vitest";
import { buildFieldCentralModel } from "@/lib/fieldCentral";
import type { AuditPlan } from "@/api/auditPlanTypes";
import type { AuditPlanSchedule, ScheduleItem } from "@/api/auditPlanScheduleTypes";

const ORG = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const AID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

const baseAssessment = {
  id: AID,
  organization_id: ORG,
  type: "diagnosis",
  status: "in_progress",
  started_at: "2026-07-01T12:00:00.000Z",
};

const readyPlan = {
  plan_status: "ready",
  modality: "diagnosis",
  scope_text: "Escopo de teste",
  processes: [
    {
      name: "Compras",
      owner: "",
      notes: "",
      from_preparation: false,
      interview_justification: "",
    },
  ],
} as AuditPlan;

function item(partial: Partial<ScheduleItem> & Pick<ScheduleItem, "id" | "kind" | "title" | "status">): ScheduleItem {
  return {
    timezone: "America/Sao_Paulo",
    location_or_link: "",
    preparation: "",
    objective: "",
    process_name: "",
    participant_membership_ids: [],
    primary_action_label: "",
    next_action: "",
    starts_at: null,
    interview_id: null,
    plan_activity_kind: null,
    ...partial,
  };
}

function scheduleWith(items: ScheduleItem[]): AuditPlanSchedule {
  return {
    assessment_id: AID,
    organization_id: ORG,
    timezone: "America/Sao_Paulo",
    agenda_href: "/agenda",
    items,
    overlaps: [],
    pendings: [],
    next_action: "",
    has_opening_meeting: items.some(
      (i) => i.plan_activity_kind === "opening_meeting",
    ),
    has_closing_meeting: items.some(
      (i) => i.plan_activity_kind === "closing_meeting",
    ),
  };
}

describe("buildFieldCentralModel", () => {
  it("draft aponta ao Plano da Auditoria", () => {
    const model = buildFieldCentralModel({
      organizationId: ORG,
      organizationName: "Org A",
      assessment: { ...baseAssessment, status: "draft" },
      plan: null,
      schedule: null,
      interviews: [],
      evidences: [],
      scopeLabels: [],
      roles: ["auditor"],
      canMutate: true,
    });
    expect(model.mode).toBe("draft_redirect");
    expect(model.nextAction.kind).toBe("open_audit_plan");
    expect(model.nextAction.href).toContain("/audit-plan");
  });

  it("planned sem abertura prioriza reunião de abertura", () => {
    const model = buildFieldCentralModel({
      organizationId: ORG,
      organizationName: "Org A",
      assessment: { ...baseAssessment, status: "planned" },
      plan: readyPlan,
      schedule: scheduleWith([
        item({
          id: "ev-open",
          kind: "meeting",
          plan_activity_kind: "opening_meeting",
          title: "Abertura",
          status: "scheduled",
          starts_at: "2026-07-21T10:00:00.000Z",
        }),
      ]),
      interviews: [],
      evidences: [],
      scopeLabels: ["TI"],
      roles: ["auditor"],
      canMutate: true,
    });
    expect(model.mode).toBe("planned_handoff");
    expect(model.nextAction.kind).toBe("opening_meeting");
    expect(model.nextAction.label).toMatch(/abertura/i);
  });

  it("in_progress continua entrevista em andamento", () => {
    const model = buildFieldCentralModel({
      organizationId: ORG,
      organizationName: "Org A",
      assessment: baseAssessment,
      plan: readyPlan,
      schedule: scheduleWith([]),
      interviews: [
        {
          id: "iv-1",
          title: "Entrevista Compras",
          status: "in_progress",
          process_name: "Compras",
          scheduled_at: "2026-07-21T14:00:00.000Z",
        },
        {
          id: "iv-2",
          title: "Próxima",
          status: "confirmed",
          process_name: "Vendas",
        },
      ],
      evidences: [],
      scopeLabels: [],
      roles: ["auditor"],
      canMutate: true,
      now: new Date("2026-07-21T15:00:00.000Z"),
    });
    expect(model.mode).toBe("field_active");
    expect(model.nextAction.kind).toBe("continue_interview");
    expect(model.nextAction.interviewId).toBe("iv-1");
    expect(model.assistantContext.page).toBe("field_central");
    expect(model.assistantContext.organization_id).toBe(ORG);
  });

  it("in_progress sem entrevista ativa inicia a próxima confirmada", () => {
    const model = buildFieldCentralModel({
      organizationId: ORG,
      organizationName: "Org A",
      assessment: baseAssessment,
      plan: readyPlan,
      schedule: scheduleWith([]),
      interviews: [
        {
          id: "iv-2",
          title: "Vendas",
          status: "confirmed",
          process_name: "Vendas",
          scheduled_at: "2026-07-21T16:00:00.000Z",
        },
      ],
      evidences: [],
      scopeLabels: [],
      roles: ["auditor"],
      canMutate: true,
      now: new Date("2026-07-21T15:00:00.000Z"),
    });
    expect(model.nextAction.kind).toBe("start_interview");
    expect(model.nextAction.interviewId).toBe("iv-2");
  });

  it("analysis abre resumo somente leitura", () => {
    const model = buildFieldCentralModel({
      organizationId: ORG,
      organizationName: "Org A",
      assessment: { ...baseAssessment, status: "analysis" },
      plan: readyPlan,
      schedule: null,
      interviews: [
        { id: "iv-1", title: "Feita", status: "completed", process_name: "Compras" },
      ],
      evidences: [{ id: "e1", status: "approved", created_at: "2026-07-02T00:00:00Z" }],
      scopeLabels: [],
      roles: ["auditor"],
      canMutate: true,
    });
    expect(model.mode).toBe("field_readonly");
    expect(model.nextAction.kind).toBe("go_analysis");
  });

  it("classifica evidência antecipada por fase de coleta", () => {
    const model = buildFieldCentralModel({
      organizationId: ORG,
      organizationName: "Org A",
      assessment: baseAssessment,
      plan: readyPlan,
      schedule: null,
      interviews: [],
      evidences: [
        {
          id: "early-1",
          status: "approved",
          created_at: "2026-07-10T00:00:00Z",
          collected_phase: "guided_prep",
        },
        {
          id: "field-1",
          status: "approved",
          created_at: "2026-07-10T00:00:00Z",
          collected_phase: "field",
        },
        { id: "rej-1", status: "rejected", created_at: "2026-07-10T00:00:00Z" },
      ],
      scopeLabels: [],
      roles: ["auditor"],
      canMutate: true,
    });
    const early = model.evidenceBuckets.find((b) => b.key === "early");
    const field = model.evidenceBuckets.find((b) => b.key === "field");
    const rejected = model.evidenceBuckets.find((b) => b.key === "rejected");
    expect(early?.evidenceIds).toContain("early-1");
    expect(field?.evidenceIds).toContain("field-1");
    expect(rejected?.count).toBe(1);
  });

  it("reader não recebe CTA de mutação no campo ativo vazio", () => {
    const model = buildFieldCentralModel({
      organizationId: ORG,
      organizationName: "Org A",
      assessment: baseAssessment,
      plan: readyPlan,
      schedule: scheduleWith([]),
      interviews: [],
      evidences: [],
      scopeLabels: [],
      roles: ["reader"],
      canMutate: false,
    });
    expect(model.nextAction.kind).toBe("none");
    expect(model.nextAction.label).toMatch(/somente leitura|acompanhar/i);
  });
});
