import { describe, expect, it } from "vitest";
import type { GuidedQuestion, GuidedSession } from "@/api/guidedTypes";
import { emptyGuidedContext } from "@/api/guidedTypes";
import {
  CONSULTIVE_OPENINGS,
  buildClauseNarrative,
  buildFinalReview,
  narrativeAvoidsJudgment,
} from "@/lib/guidedNarrative";

const q = (
  id: string,
  clause_ref: string,
): GuidedQuestion => ({
  id,
  version: "1",
  theme: "Tema",
  clause_ref,
  question: `Pergunta ${id}`,
  explanation: "e",
  practice_examples: ["p"],
  evidence_examples: ["e"],
  answer_type: "choice_with_description",
  required: true,
  show_when: null,
});

describe("guidedNarrative consultive", () => {
  it("has openings for clauses 4–10", () => {
    for (const major of ["4", "5", "6", "7", "8", "9", "10"]) {
      const o = CONSULTIVE_OPENINGS[major];
      expect(o).toBeTruthy();
      expect(o!.businessName.length).toBeGreaterThan(3);
      expect(o!.objective.length).toBeGreaterThan(10);
      expect(narrativeAvoidsJudgment(o!.objective)).toBe(true);
      expect(narrativeAvoidsJudgment(o!.whatIsEvaluated)).toBe(true);
    }
  });

  it("builds clause summary from real answers without judgment words", () => {
    const questions = [q("a", "6.1"), q("b", "6.2")];
    const answers = [
      {
        question_id: "a",
        question_version: "1",
        answer_value: "yes" as const,
        description: "Fazemos mapa de riscos",
        na_justification: "",
        evidence_mode: "none" as const,
        evidence_ids: [],
        evidence_note: "",
        provide_later: true,
      },
      {
        question_id: "b",
        question_version: "1",
        answer_value: "partial" as const,
        description: "Metas ainda genéricas",
        na_justification: "",
        evidence_mode: "none" as const,
        evidence_ids: [],
        evidence_note: "",
        provide_later: false,
      },
    ];
    const n = buildClauseNarrative("6", questions, answers);
    expect(n.informedPractices).toHaveLength(1);
    expect(n.partialAnswers).toHaveLength(1);
    expect(n.promisedEvidence).toHaveLength(1);
    expect(n.stats.applicable).toBe(2);
    expect(n.stats.answered).toBe(2);
    for (const line of [
      ...n.strengtheningOpportunities,
      ...n.possibleBusinessImpacts,
      n.whatCompanyInformed,
    ]) {
      expect(narrativeAvoidsJudgment(line)).toBe(true);
    }
  });

  it("final review consolidates business journey 4–10", () => {
    const questions = [
      q("a", "4.1"),
      q("b", "5.1"),
      q("c", "10.2"),
    ];
    const session: GuidedSession = {
      id: "s",
      assessment_id: "a",
      organization_id: "o",
      catalog_version: "iso9001-2015-c4c10-v1",
      status: "review",
      current_step: "review",
      current_question_id: null,
      context: emptyGuidedContext(),
      answers: [
        {
          question_id: "a",
          question_version: "1",
          answer_value: "yes",
          description: "",
          na_justification: "",
          evidence_mode: "none",
          evidence_ids: [],
          evidence_note: "nota",
          provide_later: false,
        },
      ],
      answered_count: 1,
      question_count: 3,
      updated_at: new Date().toISOString(),
    };
    const review = buildFinalReview(session, questions);
    expect(review.businessJourney).toHaveLength(7);
    expect(review.applicableCount).toBe(3);
    expect(review.answeredCount).toBe(1);
    expect(review.evidenceAvailableCount).toBe(1);
    for (const step of review.nextSteps) {
      expect(narrativeAvoidsJudgment(step)).toBe(true);
    }
  });
});
