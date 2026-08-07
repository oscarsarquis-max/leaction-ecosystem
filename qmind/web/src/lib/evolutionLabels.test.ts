import { describe, expect, it } from "vitest";
import {
  labelEvolutionConfidence,
  labelEvolutionPriority,
  labelEvolutionStatus,
} from "@/lib/evolutionLabels";

describe("evolutionLabels", () => {
  it("humanizes priority confidence and status", () => {
    expect(labelEvolutionPriority("now")).toBe("Agora");
    expect(labelEvolutionPriority("investigate")).toBe("Aprofundar");
    expect(labelEvolutionConfidence("high")).toBe("Fundamentação forte");
    expect(labelEvolutionConfidence("low")).toBe("Precisa de mais informações");
    expect(labelEvolutionStatus("proposed")).toBe("Sugerida");
    expect(labelEvolutionStatus("converted_to_action")).toBe("Convertida em ação");
  });
});
