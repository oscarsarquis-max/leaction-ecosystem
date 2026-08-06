import { describe, expect, it } from "vitest";
import type { AssessmentOut } from "@qmind/api-client";
import { selectFocusAssessment } from "@/lib/selectFocusAssessment";

function row(
  partial: Partial<AssessmentOut> & Pick<AssessmentOut, "id" | "status">,
): AssessmentOut {
  return {
    organization_id: "org-a",
    type: "diagnosis",
    assessment_model_id: "m1",
    standard_version_id: "sv1",
    lead_membership_id: null,
    maturity_model_id: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...partial,
  } as AssessmentOut;
}

describe("selectFocusAssessment", () => {
  it("prefers most recently updated in-flight assessment", () => {
    const focus = selectFocusAssessment([
      row({
        id: "draft-1",
        status: "draft",
        updated_at: "2026-08-06T12:00:00Z",
      }),
      row({
        id: "old-progress",
        status: "in_progress",
        updated_at: "2026-08-01T00:00:00Z",
      }),
      row({
        id: "new-progress",
        status: "analysis",
        updated_at: "2026-08-06T10:00:00Z",
      }),
    ]);
    expect(focus?.id).toBe("new-progress");
  });

  it("falls back planned → draft → closed", () => {
    expect(
      selectFocusAssessment([
        row({ id: "c", status: "closed", updated_at: "2026-08-06T00:00:00Z" }),
        row({ id: "p", status: "planned", updated_at: "2026-08-05T00:00:00Z" }),
      ])?.id,
    ).toBe("p");

    expect(
      selectFocusAssessment([
        row({ id: "c", status: "closed" }),
        row({ id: "d", status: "draft" }),
      ])?.id,
    ).toBe("d");

    expect(selectFocusAssessment([row({ id: "c", status: "closed" })])?.id).toBe(
      "c",
    );
  });

  it("ignores cancelled", () => {
    expect(
      selectFocusAssessment([row({ id: "x", status: "cancelled" })]),
    ).toBeNull();
  });
});
