import { describe, expect, it, beforeEach } from "vitest";
import {
  GUIDED_TOUR_STEPS,
  clearGuidedTour,
  isGuidedTourActive,
  readGuidedTourStepIndex,
  writeGuidedTourActive,
} from "@/lib/guidedTour";

const ORG = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const ORG_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

describe("guidedTour", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("expõe as 11 etapas da apresentação", () => {
    expect(GUIDED_TOUR_STEPS).toHaveLength(11);
  });

  it("ativa por organização e limpa ao trocar", () => {
    writeGuidedTourActive(ORG, 3);
    expect(isGuidedTourActive(ORG)).toBe(true);
    expect(readGuidedTourStepIndex()).toBe(3);
    expect(isGuidedTourActive(ORG_B)).toBe(false);
    clearGuidedTour();
    expect(isGuidedTourActive(ORG)).toBe(false);
  });

  it("não gera href quebrado sem assessment quando necessário", () => {
    const wizard = GUIDED_TOUR_STEPS.find((s) => s.id === "wizard")!;
    expect(wizard.resolveHref(null)).toBeNull();
    expect(wizard.resolveHref(ORG)).toBe(`/assessments/${ORG}/guided`);
  });
});
