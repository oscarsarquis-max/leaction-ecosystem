import { describe, expect, it } from "vitest";
import {
  canEditAssessmentSetup,
  canMutateAssessments,
  canReadAssessments,
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
  });
});
