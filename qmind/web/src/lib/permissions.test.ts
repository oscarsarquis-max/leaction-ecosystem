import { describe, expect, it } from "vitest";
import {
  canApproveFinding,
  canCollectEvidence,
  canCreateFindings,
  canEditAssessmentSetup,
  canEditFieldExecution,
  canMutateAssessments,
  canReadAssessments,
  canReviewFindings,
  canStartAssessment,
} from "@/lib/permissions";

describe("assessment permissions", () => {
  it("allows mutate roles to edit draft setup", () => {
    expect(canMutateAssessments(["org_admin"])).toBe(true);
    expect(canEditAssessmentSetup(["quality_manager"], "draft")).toBe(true);
    expect(canEditAssessmentSetup(["consultant_auditor"], "planned")).toBe(false);
  });

  it("reader can read but not mutate", () => {
    expect(canReadAssessments(["reader"])).toBe(true);
    expect(canMutateAssessments(["reader"])).toBe(false);
    expect(canEditAssessmentSetup(["reader"], "draft")).toBe(false);
    expect(canStartAssessment(["reader"], "planned")).toBe(false);
    expect(canEditFieldExecution(["reader"], "in_progress")).toBe(false);
  });

  it("gates start and field execution by status", () => {
    expect(canStartAssessment(["org_admin"], "planned")).toBe(true);
    expect(canStartAssessment(["org_admin"], "draft")).toBe(false);
    expect(canEditFieldExecution(["consultant_auditor"], "in_progress")).toBe(true);
    expect(canCollectEvidence(["quality_manager"], "analysis")).toBe(true);
    expect(canCollectEvidence(["quality_manager"], "planned")).toBe(false);
  });

  it("enforces finding SoD and create/review roles", () => {
    expect(canCreateFindings(["consultant_auditor"], "in_progress")).toBe(true);
    expect(canCreateFindings(["reader"], "in_progress")).toBe(false);
    expect(canReviewFindings(["quality_manager"])).toBe(true);
    expect(canReviewFindings(["consultant_auditor"])).toBe(false);
    const author = "mem-author";
    expect(canApproveFinding(["quality_manager"], author, author)).toBe(false);
    expect(canApproveFinding(["quality_manager"], "mem-other", author)).toBe(true);
  });
});
