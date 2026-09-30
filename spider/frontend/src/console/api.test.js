import { describe, expect, it } from "vitest";
import { describeRequestFailure, operationLabel } from "./api";

describe("describeRequestFailure", () => {
  it("names the failed operation in Portuguese", () => {
    expect(operationLabel("/v1/context/executions/exec-1")).toBe("Consulta de contexto da execução");
    expect(
      describeRequestFailure("/v1/console/executions/exec-1/events", 500, {
        title: "Unexpected orchestration error",
        detail: "store unavailable",
      }),
    ).toBe("Consulta de eventos relacionados falhou (500): store unavailable");
    expect(describeRequestFailure("/v1/context/executions/exec-1", 404, { title: "Resource not found" })).toBe(
      "Consulta de contexto da execução não está disponível neste ambiente.",
    );
  });
});
