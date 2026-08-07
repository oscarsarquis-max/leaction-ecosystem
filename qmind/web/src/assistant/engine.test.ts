import { describe, expect, it } from "vitest";
import { DeterministicAssistantEngine } from "@/assistant/engine";
import type { AssistantContext } from "@/assistant/types";

const ORG = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const AID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

function base(partial: Partial<AssistantContext>): AssistantContext {
  return {
    organization_id: ORG,
    organization_name: "Org Demo",
    assessment_id: AID,
    assessment_label: "Diagnóstico inicial",
    route: `/assessments/${AID}`,
    page: "assessment_map",
    phase_label: "Preparação",
    assessment_status: "draft",
    user_roles: ["auditor"],
    can_mutate: true,
    next_action: {
      label: "Continuar preparação",
      hint: "Complete o roteiro orientado.",
      href: `/assessments/${AID}/guided`,
    },
    pendencies: [],
    blockers: [],
    progress_summary: "10% do percurso",
    allowed_links: [
      "/assessments",
      `/assessments/${AID}`,
      `/assessments/${AID}/guided`,
      `/assessments/${AID}/audit-plan`,
      `/assessments/${AID}/work`,
    ],
    stage_title: "Mapa",
    stage_explanation: "Visão geral do percurso.",
    ...partial,
  };
}

describe("DeterministicAssistantEngine", () => {
  const engine = new DeterministicAssistantEngine();

  it("home sem avaliação orienta criação", () => {
    const ctx = base({
      assessment_id: null,
      assessment_label: null,
      page: "org_home",
      route: "/assessments",
      next_action: {
        label: "Criar a primeira avaliação",
        hint: "Comece pela preparação.",
        href: "/assessments/new",
        mutates: true,
      },
      pendencies: [
        {
          key: "no-assessment",
          problem: "Nenhuma avaliação",
          impact: "Sem percurso",
          actionLabel: "Criar",
          href: "/assessments/new",
        },
      ],
      allowed_links: ["/assessments", "/assessments/new"],
    });
    const now = engine.answer("what_now", ctx);
    expect(now.blocks.some((b) => b.type === "link" && b.href === "/assessments/new")).toBe(
      true,
    );
    const go = engine.answer("go_next", ctx);
    expect(go.navigateHref).toBe("/assessments/new");
  });

  it("wizard explica pergunta sem escolher resposta", () => {
    const ctx = base({
      page: "wizard",
      route: `/assessments/${AID}/guided`,
      wizard: {
        questionTheme: "Contexto da organização",
        questionText: "A organização define seu contexto?",
        explanation: "Entender o contexto evita escopo errado.",
        practiceExamples: ["Reunião anual de contexto"],
        evidenceExamples: ["Ata de reunião"],
        whyNeeded: "Alimenta o plano e o campo.",
      },
    });
    const reply = engine.answer("explain_stage", ctx);
    const text = JSON.stringify(reply);
    expect(text).toMatch(/não escolhe a resposta/i);
    expect(text).not.toMatch(/marque Sim|responda Sim|escolha Sim/i);
    expect(text).toMatch(/Parcialmente/);
  });

  it("plano explica ready versus planned", () => {
    const ctx = base({
      page: "audit_plan",
      assessment_status: "draft",
      plan: {
        planStatus: "ready",
        planReady: true,
        assessmentPlanned: false,
        needsAmendment: false,
        readinessNext: "Concluir planejamento",
        freezeNote: "Congela após planejamento concluído.",
      },
    });
    const reply = engine.answer("explain_stage", ctx);
    const text = JSON.stringify(reply);
    expect(text).toMatch(/Plano pronto/);
    expect(text).toMatch(/Planejamento concluído/);
  });

  it("campo usa próxima ação real", () => {
    const ctx = base({
      page: "field_central",
      assessment_status: "in_progress",
      phase_label: "Execução em campo",
      next_action: {
        label: "Continuar entrevista",
        hint: "Retome a entrevista de Compras.",
        href: `/assessments/${AID}/work`,
      },
      field: {
        currentActivityTitle: "Entrevista Compras",
        earlyEvidenceCount: 2,
        pendingEvidenceCount: 1,
        closingPrepShow: false,
      },
    });
    const now = engine.answer("what_now", ctx);
    expect(JSON.stringify(now)).toMatch(/Continuar entrevista/);
    const explain = engine.answer("explain_stage", ctx);
    expect(JSON.stringify(explain)).toMatch(/Entrevista Compras/);
  });

  it("reader não recebe CTA de mutação", () => {
    const ctx = base({
      can_mutate: false,
      user_roles: ["reader"],
      next_action: {
        label: "Iniciar execução",
        hint: "Só editores iniciam.",
        href: `/assessments/${AID}/audit-plan`,
        mutates: true,
      },
    });
    const now = engine.answer("what_now", ctx);
    expect(now.blocks.some((b) => b.type === "link")).toBe(false);
    expect(JSON.stringify(now)).toMatch(/somente leitura|não permite/i);
    const go = engine.answer("go_next", ctx);
    expect(go.navigateHref).toBeUndefined();
  });

  it("pendências com links permitidos", () => {
    const href = `/assessments/${AID}/audit-plan`;
    const ctx = base({
      pendencies: [
        {
          key: "p1",
          problem: "Falta reunião de abertura",
          impact: "Não inicia o campo",
          actionLabel: "Abrir plano",
          href,
        },
      ],
    });
    const reply = engine.answer("what_pending", ctx);
    expect(reply.blocks.some((b) => b.type === "link" && b.href === href)).toBe(
      true,
    );
  });

  it("go_next rejeita link externo", () => {
    const ctx = base({
      next_action: {
        label: "Sair",
        hint: "x",
        href: "https://evil.example",
      },
      allowed_links: ["https://evil.example"],
    });
    const go = engine.answer("go_next", ctx);
    expect(go.navigateHref).toBeUndefined();
  });
});
