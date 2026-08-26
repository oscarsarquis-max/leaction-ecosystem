import { describe, expect, it, beforeEach } from "vitest";
import {
  GUIDED_TOUR_STEPS,
  chapterIdFromStepIndex,
  clearGuidedTour,
  isGuidedTourActive,
  readGuidedTourStepIndex,
  stepIndexFromChapterParam,
  writeGuidedTourActive,
} from "@/lib/guidedTour";
import {
  EMPTY_TOUR_DEMO_FACTS,
  JOURNEY_CHAPTER_IDS,
  deriveTourDemoFacts,
  parseChapterParam,
  preferCaseIdFromCockpit,
  resolveTourStepAvailability,
  selectFocusImprovementCase,
  type GuidedTourStepDef,
  type TourDemoContext,
  type TourDemoFacts,
} from "@/journeyV2";
import type { CockpitCaseItemOut, ImprovementCaseEvolutionOut } from "@qmind/api-client";

const ORG = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const ORG_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

function baseCtx(partial: Partial<TourDemoContext> = {}): TourDemoContext {
  return {
    organizationId: ORG,
    roles: ["org_admin"],
    assessmentId: null,
    caseId: null,
    actionItemId: null,
    assessmentsLoading: false,
    casesLoading: false,
    actionsLoading: false,
    evolutionLoading: false,
    assessmentsError: false,
    casesError: false,
    actionsError: false,
    evolutionError: false,
    facts: EMPTY_TOUR_DEMO_FACTS,
    ...partial,
  };
}

describe("guidedTour V2", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("expõe 9 capítulos canônicos na ordem da Jornada V2", () => {
    expect(GUIDED_TOUR_STEPS).toHaveLength(9);
    expect(GUIDED_TOUR_STEPS.map((s) => s.id)).toEqual([...JOURNEY_CHAPTER_IDS]);
  });

  it("ativa por organização e limpa ao trocar", () => {
    writeGuidedTourActive(ORG, 3);
    expect(isGuidedTourActive(ORG)).toBe(true);
    expect(readGuidedTourStepIndex()).toBe(3);
    expect(isGuidedTourActive(ORG_B)).toBe(false);
    clearGuidedTour();
    expect(isGuidedTourActive(ORG)).toBe(false);
  });

  it("reinicia estado antigo (versão ≠ 2)", () => {
    sessionStorage.setItem("qmind.guidedTour.step", "10");
    sessionStorage.setItem("qmind.guidedTour.version", "1");
    sessionStorage.setItem("qmind.guidedTour.active", "1");
    sessionStorage.setItem("qmind.guidedTour.orgId", ORG);
    expect(readGuidedTourStepIndex()).toBe(0);
    expect(chapterIdFromStepIndex(0)).toBe("understand");
  });

  it("normaliza capítulo inválido para o início", () => {
    expect(parseChapterParam("javascript:alert(1)")).toBeNull();
    expect(parseChapterParam("https://evil.com")).toBeNull();
    expect(parseChapterParam("/cockpit")).toBeNull();
    expect(stepIndexFromChapterParam("control")).toBe(
      JOURNEY_CHAPTER_IDS.indexOf("control"),
    );
    expect(stepIndexFromChapterParam("nope")).toBe(0);
  });

  it("seleção de caso é determinística (acting primeiro)", () => {
    const picked = selectFocusImprovementCase([
      {
        id: "1",
        organization_id: ORG,
        problem_statement: "A",
        impact_statement: "i",
        related_process: "p",
        status: "open",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-08-01T00:00:00Z",
        created_by: "u",
      },
      {
        id: "2",
        organization_id: ORG,
        problem_statement: "B",
        impact_statement: "i",
        related_process: "p",
        status: "acting",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-07-01T00:00:00Z",
        created_by: "u",
      },
    ]);
    expect(picked?.id).toBe("2");
  });

  it("matriz ready/unavailable/forbidden básica", () => {
    const assess = GUIDED_TOUR_STEPS.find((s) => s.id === "assess")!;
    const control = GUIDED_TOUR_STEPS.find((s) => s.id === "control")!;

    expect(resolveTourStepAvailability(assess, baseCtx()).status).toBe(
      "unavailable",
    );
    expect(
      resolveTourStepAvailability(assess, baseCtx({ assessmentId: "a1" })).status,
    ).toBe("ready");
    expect(
      resolveTourStepAvailability(assess, baseCtx({ assessmentId: "a1" })).href,
    ).toBe("/assessments/a1/guided");

    expect(
      resolveTourStepAvailability(control, baseCtx({ roles: ["guest"] })).status,
    ).toBe("forbidden");
    expect(resolveTourStepAvailability(control, baseCtx()).href).toBe("/cockpit");

    expect(
      resolveTourStepAvailability(assess, baseCtx({ assessmentsLoading: true }))
        .status,
    ).toBe("loading");

    expect(
      resolveTourStepAvailability(assess as GuidedTourStepDef, baseCtx({
        assessmentsError: true,
      })).status,
    ).toBe("error");
  });

  it("ready exige conteúdo demonstrável (analyze/execute/measure/interpret)", () => {
    const analyze = GUIDED_TOUR_STEPS.find((s) => s.id === "analyze")!;
    const execute = GUIDED_TOUR_STEPS.find((s) => s.id === "execute")!;
    const measure = GUIDED_TOUR_STEPS.find((s) => s.id === "evidence_measure")!;
    const interpret = GUIDED_TOUR_STEPS.find((s) => s.id === "interpret")!;
    const withCase = baseCtx({ caseId: "case-1" });

    expect(resolveTourStepAvailability(analyze, withCase).status).toBe(
      "unavailable",
    );
    expect(resolveTourStepAvailability(analyze, withCase).reason).toMatch(
      /análise OI persistida/i,
    );
    expect(
      resolveTourStepAvailability(
        analyze,
        baseCtx({
          caseId: "case-1",
          facts: { ...EMPTY_TOUR_DEMO_FACTS, hasAnalysisRun: true },
        }),
      ).status,
    ).toBe("ready");

    expect(resolveTourStepAvailability(execute, withCase).status).toBe(
      "unavailable",
    );
    expect(resolveTourStepAvailability(execute, withCase).reason).toMatch(
      /board vazio|ação\/card/i,
    );
    expect(
      resolveTourStepAvailability(
        execute,
        baseCtx({
          caseId: "case-1",
          actionItemId: "act-1",
          facts: { ...EMPTY_TOUR_DEMO_FACTS, hasActionItem: true },
        }),
      ).href,
    ).toBe("/execution/cards/act-1");

    expect(resolveTourStepAvailability(measure, withCase).status).toBe(
      "unavailable",
    );
    expect(
      resolveTourStepAvailability(
        measure,
        baseCtx({
          caseId: "case-1",
          facts: { ...EMPTY_TOUR_DEMO_FACTS, hasMeasurement: true },
        }),
      ).status,
    ).toBe("ready");

    expect(resolveTourStepAvailability(interpret, withCase).status).toBe(
      "unavailable",
    );
    expect(resolveTourStepAvailability(interpret, withCase).reason).toMatch(
      /ainda não foi interpretada/i,
    );
    expect(
      resolveTourStepAvailability(
        interpret,
        baseCtx({
          caseId: "case-1",
          facts: { ...EMPTY_TOUR_DEMO_FACTS, hasExecutionIntelligence: true },
        }),
      ).status,
    ).toBe("ready");
  });

  it("deriveTourDemoFacts lê Evolution sem inventar conteúdo", () => {
    const empty = deriveTourDemoFacts({ evolution: null, actionItems: [] });
    expect(empty).toEqual(EMPTY_TOUR_DEMO_FACTS);

    const evo = {
      analysis_summary: {
        total_runs: 1,
        latest_run: { id: "run-1" },
      },
      action_summary: { total: 0, completed: 0, overdue: 0, items: [] },
      measurement_summary: {
        measurement_posture: "on_time",
        indicator_count: 2,
        substantiation: "none",
        target_posture: "no_target",
      },
      execution_intelligence: {
        run_id: "ei-1",
        generated_at: "2026-08-26T00:00:00Z",
        execution_posture: "progressing",
        interpretability_status: "interpretable",
        interpretation_summary: "ok",
        is_stale: false,
        signal_count: 1,
      },
      case: {
        id: "c1",
        organization_id: ORG,
        problem_statement: "p",
        impact_statement: "i",
        related_process: "r",
        status: "acting",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-08-01T00:00:00Z",
        created_by: "u",
      },
      closure_readiness: "insufficient_information",
    } as ImprovementCaseEvolutionOut;

    const facts: TourDemoFacts = deriveTourDemoFacts({
      evolution: evo,
      actionItems: [],
    });
    expect(facts.hasAnalysisRun).toBe(true);
    expect(facts.hasMeasurement).toBe(true);
    expect(facts.hasExecutionIntelligence).toBe(true);
    expect(facts.hasActionItem).toBe(false);
  });

  it("Cockpit preferência escolhe caso com EI para interpret", () => {
    const items = [
      {
        case_id: "never",
        intelligence_freshness: "never_analyzed",
        action_count: 0,
        measurement_posture: "not_planned",
        case_status: "open",
      },
      {
        case_id: "with-ei",
        intelligence_freshness: "current",
        action_count: 1,
        measurement_posture: "on_time",
        case_status: "acting",
      },
    ] as CockpitCaseItemOut[];
    expect(preferCaseIdFromCockpit("interpret", items)).toBe("with-ei");
    expect(preferCaseIdFromCockpit("execute", items)).toBe("with-ei");
  });

  it("não expõe UUID como rótulo de capítulo", () => {
    for (const step of GUIDED_TOUR_STEPS) {
      expect(step.title).not.toMatch(
        /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i,
      );
      expect(step.id).not.toMatch(/^[0-9a-f-]{36}$/i);
    }
  });
});
