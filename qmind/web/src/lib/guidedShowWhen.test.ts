import { describe, expect, it } from "vitest";
import type { GuidedQuestion } from "@/api/guidedTypes";
import {
  clauseProgressList,
  matchesShowWhen,
  visibleGuidedQuestions,
} from "@/lib/guidedShowWhen";

const q = (
  id: string,
  clause_ref: string,
  show_when: GuidedQuestion["show_when"] = null,
): GuidedQuestion => ({
  id,
  version: "1",
  theme: "t",
  clause_ref,
  question: id,
  explanation: "e",
  practice_examples: ["p"],
  evidence_examples: ["e"],
  answer_type: "choice_with_description",
  required: true,
  show_when,
});

describe("guidedShowWhen", () => {
  it("supports context not_empty and answer in", () => {
    expect(
      matchesShowWhen(
        { context: "qms_scope.exclusions", not_empty: true },
        [],
        { qms_scope: { exclusions: "", exclusion_justification: "", description: "" } },
      ),
    ).toBe(false);
    expect(
      matchesShowWhen(
        { context: "qms_scope.exclusions", not_empty: true },
        [],
        {
          qms_scope: {
            exclusions: "Dev",
            exclusion_justification: "",
            description: "",
          },
        },
      ),
    ).toBe(true);
    expect(
      matchesShowWhen(
        { answer: "gate", in: ["yes", "partial"] },
        [{ question_id: "gate", answer_value: "yes", description: "", na_justification: "", evidence_mode: "none", evidence_ids: [], evidence_note: "", provide_later: false, question_version: "1" }],
      ),
    ).toBe(true);
  });

  it("excludes hidden from applicable progress", () => {
    const questions = [
      q("a", "4.1"),
      q("b", "4.3", { context: "qms_scope.exclusions", not_empty: true }),
      q("c", "8.3", { answer: "gate", in: ["yes"] }),
    ];
    const visible = visibleGuidedQuestions(
      questions,
      [],
      {
        organization_profile: { trade_name: "", summary: "", size_band: "" },
        qms_scope: { description: "", exclusions: "", exclusion_justification: "" },
        products_services: [],
        sites: [],
        processes: [],
        stakeholders: [],
      },
    );
    expect(visible.map((x) => x.id)).toEqual(["a"]);
    const progress = clauseProgressList(visible, []);
    const c4 = progress.find((p) => p.major === "4")!;
    expect(c4.applicable).toBe(1);
    expect(c4.pending).toBe(1);
  });

  it("supports equals not_equals all any", () => {
    expect(
      matchesShowWhen(
        { all: [{ answer: "a", equals: "yes" }, { answer: "b", not_equals: "no" }] },
        [
          { question_id: "a", answer_value: "yes", description: "", na_justification: "", evidence_mode: "none", evidence_ids: [], evidence_note: "", provide_later: false, question_version: "1" },
          { question_id: "b", answer_value: "partial", description: "", na_justification: "", evidence_mode: "none", evidence_ids: [], evidence_note: "", provide_later: false, question_version: "1" },
        ],
      ),
    ).toBe(true);
  });
});
