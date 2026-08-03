import { describe, expect, it } from "vitest";
import {
  canCollectEvidence,
  canEditAssessmentSetup,
  canEditFieldExecution,
  canMutateAssessments,
  canReadAssessments,
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
});
