import { describe, it, expect } from "vitest";
import { projectExecutionJourney } from "./projectExecutionJourney";

const retryDetail = {
  summary: {
    executionId: "demo-retry-001",
    state: "SUCCEEDED",
    routeRef: "RETRY_THEN_SUCCESS@1",
    startedAt: "2026-08-21T18:00:00Z",
  },
  timeline: {
    available: true,
    data: [
      {
        eventId: "tr-1",
        eventType: "STATE_TRANSITION",
        title: "Transição RECEIVED → RUNNING",
        source: "PERSISTED",
      },
      {
        eventId: "att-1",
        eventType: "ATTEMPT",
        title: "Attempt #1",
        attemptNumber: 1,
        source: "PERSISTED",
      },
    ],
  },
  steps: {
    available: true,
    data: [
      {
        stepRef: "step-a",
        state: "SUCCEEDED",
        attemptCount: 2,
        attempts: [
          { attemptNumber: 1, state: "FAILED" },
          { attemptNumber: 2, state: "SUCCEEDED" },
        ],
      },
    ],
  },
  waitInfo: { available: false, reasonCode: "WAIT_NOT_PRESENT" },
  callback: { available: false },
  operationalEvents: [{ eventType: "EXECUTION_STARTED" }, { eventType: "EXECUTION_SUCCEEDED" }],
};

describe("projectExecutionJourney", () => {
  it("projects retry path from attempts without inventing wait or capacity", () => {
    const journey = projectExecutionJourney(retryDetail);
    const ids = journey.stages.map((s) => s.id);
    expect(ids).toContain("request");
    expect(ids).toContain("canonical");
    expect(ids).toContain("engine");
    expect(ids).toContain("interaction-step-a-1");
    expect(ids).toContain("retry-step-a-1");
    expect(ids).toContain("interaction-step-a-2");
    expect(ids).toContain("completion");
    expect(ids).not.toContain("wait");
    expect(ids).not.toContain("capacity");
    expect(journey.stages.find((s) => s.id === "interaction-step-a-1").state).toBe("FAILED");
    expect(journey.stages.find((s) => s.id === "retry-step-a-1").state).toBe("SUCCEEDED");
    expect(journey.stages.find((s) => s.id === "completion").state).toBe("SUCCEEDED");
  });

  it("marks later stages as not reached when execution failed", () => {
    const journey = projectExecutionJourney({
      summary: { executionId: "ex-fail", state: "FAILED", routeRef: "TECHNICAL_FAILURE@1" },
      timeline: {
        available: true,
        data: [{ eventType: "STATE_TRANSITION", title: "Transição RECEIVED → RUNNING" }],
      },
      steps: {
        available: true,
        data: [
          {
            stepRef: "step-1",
            state: "FAILED",
            attempts: [{ attemptNumber: 1, state: "FAILED" }],
          },
        ],
      },
      waitInfo: { available: false },
      callback: { available: false },
      operationalEvents: [{ eventType: "EXECUTION_FAILED" }],
    });
    expect(journey.stages.find((s) => s.id === "interaction-step-1-1").state).toBe("FAILED");
    expect(journey.stages.find((s) => s.id === "completion").state).toBe("FAILED");
    expect(journey.stages.some((s) => s.id === "wait")).toBe(false);
    expect(journey.stages.some((s) => s.id.startsWith("retry-"))).toBe(false);
  });

  it("shows wait as waiting and completion as not reached", () => {
    const journey = projectExecutionJourney({
      summary: { executionId: "ex-wait", state: "WAITING_EXTERNAL", routeRef: "WAIT_SIGNAL_RESUME@1" },
      timeline: {
        available: true,
        data: [{ eventType: "WAIT_WAITING", title: "Wait externo" }],
      },
      steps: { available: true, data: [] },
      waitInfo: { available: true, data: { waitState: "WAITING", waitType: "SIGNAL" } },
      callback: { available: false },
      operationalEvents: [{ eventType: "EXECUTION_WAITING", outcome: "WAITING" }],
    });
    expect(journey.stages.find((s) => s.id === "wait").state).toBe("WAITING");
    expect(journey.stages.find((s) => s.id === "completion").state).toBe("NOT_REACHED");
  });

  it("includes resume and signal only when operational events exist", () => {
    const journey = projectExecutionJourney({
      summary: { executionId: "ex-res", state: "SUCCEEDED", routeRef: "WAIT_SIGNAL_RESUME@1" },
      timeline: { available: true, data: [{ eventType: "STATE_TRANSITION", source: "PERSISTED" }] },
      steps: { available: true, data: [] },
      waitInfo: { available: true, data: { waitState: "RESUMED" } },
      callback: { available: false },
      operationalEvents: [
        { eventType: "EXECUTION_WAITING" },
        { eventType: "SIGNAL_ACCEPTED" },
        { eventType: "EXECUTION_RESUMED" },
        { eventType: "EXECUTION_SUCCEEDED" },
      ],
    });
    expect(journey.stages.find((s) => s.id === "resume").state).toBe("SUCCEEDED");
    expect(journey.stages.find((s) => s.id === "signal").state).toBe("SUCCEEDED");
  });

  it("omits capacity unless CAPACITY events are present", () => {
    const without = projectExecutionJourney(retryDetail);
    expect(without.stages.some((s) => s.id === "capacity")).toBe(false);
    const withCap = projectExecutionJourney({
      ...retryDetail,
      operationalEvents: [
        ...(retryDetail.operationalEvents || []),
        { eventType: "CAPACITY_ADMISSION_REJECTED" },
      ],
    });
    expect(withCap.stages.find((s) => s.id === "capacity").state).toBe("REJECTED");
  });

  it("orders evidenced stages along the real path", () => {
    const ids = projectExecutionJourney(retryDetail).stages.map((s) => s.id);
    expect(ids.indexOf("request")).toBeLessThan(ids.indexOf("engine"));
    expect(ids.indexOf("interaction-step-a-1")).toBeLessThan(ids.indexOf("retry-step-a-1"));
    expect(ids.indexOf("retry-step-a-1")).toBeLessThan(ids.indexOf("interaction-step-a-2"));
    expect(ids.indexOf("interaction-step-a-2")).toBeLessThan(ids.indexOf("completion"));
  });

  it("reconstructs retry from persisted timeline when attempts array is empty", () => {
    const journey = projectExecutionJourney({
      summary: {
        executionId: "ex-tl",
        state: "SUCCEEDED",
        routeRef: "RETRY_THEN_SUCCESS@1",
      },
      timeline: {
        available: true,
        data: [
          { eventType: "ATTEMPT", stepRef: "step-1", attemptNumber: 1, state: "FAILED" },
          { eventType: "ATTEMPT", stepRef: "step-1", attemptNumber: 2, state: "SUCCEEDED" },
        ],
      },
      steps: {
        available: true,
        data: [{ stepRef: "step-1", state: "SUCCEEDED", attemptCount: 2 }],
      },
      waitInfo: { available: false },
      callback: { available: false },
      operationalEvents: [],
    });
    expect(journey.stages.find((s) => s.id === "interaction-step-1-1").state).toBe("FAILED");
    expect(journey.stages.find((s) => s.id === "retry-step-1-1")).toBeTruthy();
    expect(journey.stages.find((s) => s.id === "interaction-step-1-2").state).toBe("SUCCEEDED");
  });

  it("returns empty stages without an execution", () => {
    expect(projectExecutionJourney({}).stages).toEqual([]);
  });
});
