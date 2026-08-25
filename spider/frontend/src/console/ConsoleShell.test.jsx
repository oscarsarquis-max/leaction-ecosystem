import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import ConsoleShell from "../console/ConsoleShell.jsx";
import { JourneyMap, SecurityPosturePanel, TimelineView, OperationalTimelineView } from "../console/components.jsx";
import { isTerminalState } from "../console/api.js";
import { MOCK_SCENARIOS, buildCanonicalRequest } from "../console/scenarios.js";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("api helpers", () => {
  it("distinguishes terminal states", () => {
    expect(isTerminalState("SUCCEEDED")).toBe(true);
    expect(isTerminalState("RUNNING")).toBe(false);
    expect(isTerminalState("WAITING_EXTERNAL")).toBe(false);
  });
});

describe("scenarios", () => {
  it("builds canonical request without legacy fields", () => {
    const body = buildCanonicalRequest(MOCK_SCENARIOS[1], {
      idempotencyKey: "idem-x",
      traceparent: "00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01",
    });
    expect(body.target.operation).toBe("RETRY_THEN_SUCCESS");
    expect(JSON.stringify(body)).not.toContain("orchestrate");
  });
});

describe("SecurityPosturePanel", () => {
  it("does not render JWT or token", () => {
    render(
      <SecurityPosturePanel
        section={{
          available: true,
          data: {
            authentication: "ENFORCED",
            authorization: "ENFORCED",
            dataExposure: "REDACTED",
          },
        }}
      />,
    );
    expect(screen.getByText("REDACTED")).toBeInTheDocument();
    expect(screen.queryByText(/jwt/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Bearer/i)).not.toBeInTheDocument();
  });
});

describe("JourneyMap", () => {
  it("renders plan order and wait marker", () => {
    render(
      <JourneyMap
        plan={{ available: true, data: { orderedSteps: ["a", "b"] } }}
        steps={{
          available: true,
          data: [
            { stepRef: "a", state: "SUCCEEDED", attemptCount: 2 },
            { stepRef: "b", state: "WAITING_EXTERNAL", attemptCount: 1 },
          ],
        }}
      />,
    );
    expect(screen.getByText("a")).toBeInTheDocument();
    expect(screen.getByText(/espera assíncrona/)).toBeInTheDocument();
  });
});

describe("TimelineView", () => {
  it("shows persisted events only", () => {
    render(
      <TimelineView
        timeline={{
          available: true,
          data: [
            {
              eventId: "1",
              occurredAt: "2026-08-21T12:00:00Z",
              phase: "STEP_EXECUTION",
              eventType: "ATTEMPT",
              severity: "INFO",
              title: "Attempt #1",
              source: "PERSISTED",
            },
          ],
        }}
      />,
    );
    expect(screen.getByText("Attempt #1")).toBeInTheDocument();
    expect(screen.getByText("PERSISTED")).toBeInTheDocument();
  });
});

describe("OperationalTimelineView", () => {
  it("renders timestamp, category, type, source, outcome and duration", () => {
    render(
      <OperationalTimelineView
        events={[
          {
            eventId: "oev-1",
            occurredAt: "2026-08-25T12:00:00Z",
            category: "EXECUTION",
            eventType: "EXECUTION_SUCCEEDED",
            source: "canonical-engine",
            outcome: "SUCCESS",
            durationMs: 42,
          },
        ]}
      />,
    );
    expect(screen.getByLabelText("Operational Timeline")).toBeInTheDocument();
    expect(screen.getByText("EXECUTION")).toBeInTheDocument();
    expect(screen.getByText("EXECUTION_SUCCEEDED")).toBeInTheDocument();
    expect(screen.getByText("canonical-engine")).toBeInTheDocument();
    expect(screen.getByText("SUCCESS")).toBeInTheDocument();
    expect(screen.getByText("42 ms")).toBeInTheDocument();
  });
});

describe("ConsoleShell", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url, init) => {
        if (String(url).includes("/v1/products/orchestrate")) {
          throw new Error("legacy must not be called");
        }
        if (String(url).includes("/v1/console/operational-health")) {
          return {
            ok: true,
            status: 200,
            text: async () =>
              JSON.stringify({
                schemaVersion: 1,
                integrationLevel: "MOCK_ONLY",
                provisional: true,
                overallStatus: "HEALTHY",
                window: { duration: "PT24H" },
                slis: [
                  {
                    code: "EXECUTION_TECHNICAL_RELIABILITY",
                    status: "AVAILABLE",
                    value: 0.99,
                    unit: "ratio",
                    sampleSize: 100,
                  },
                ],
                dataQuality: { complete: true, missingSources: [] },
              }),
          };
        }
        if (String(url).includes("/v1/console/executions") && (!init || init.method !== "POST")) {
          if (String(url).includes("/events")) {
            return {
              ok: true,
              status: 200,
              text: async () =>
                JSON.stringify({
                  executionId: "ex-1",
                  items: [
                    {
                      eventId: "oev-1",
                      category: "EXECUTION",
                      eventType: "EXECUTION_STARTED",
                      source: "canonical-engine",
                      outcome: "INFO",
                      occurredAt: "2026-08-25T12:00:00Z",
                    },
                  ],
                }),
            };
          }
          if (String(url).match(/\/executions\/[^?/]+$/)) {
            return {
              ok: true,
              status: 200,
              text: async () =>
                JSON.stringify({
                  summary: {
                    executionId: "ex-1",
                    state: "RUNNING",
                    technicalStatus: "PENDING",
                    routeRef: "RETRY_THEN_SUCCESS@1",
                  },
                  plan: { available: true, data: { orderedSteps: ["s1"] } },
                  steps: {
                    available: true,
                    data: [{ stepRef: "s1", state: "RUNNING", attemptCount: 1 }],
                  },
                  timeline: {
                    available: true,
                    data: [
                      {
                        eventId: "e1",
                        occurredAt: "2026-08-21T12:00:00Z",
                        phase: "STEP_EXECUTION",
                        eventType: "STEP_RUNNING",
                        severity: "INFO",
                        title: "Step s1",
                        source: "PERSISTED",
                      },
                    ],
                  },
                  waitInfo: { available: false, reasonCode: "WAIT_NOT_PRESENT" },
                  signal: { available: false },
                  callback: { available: false },
                  reconciliation: { available: false },
                  governance: { available: false },
                  securityPosture: {
                    available: true,
                    data: { dataExposure: "REDACTED", authentication: "ENFORCED" },
                  },
                  safeRequestProjection: { available: true, redacted: false, data: {} },
                  safeResultProjection: { available: false, redacted: true },
                }),
            };
          }
          return {
            ok: true,
            status: 200,
            text: async () =>
              JSON.stringify({
                items: [
                  {
                    executionId: "ex-1",
                    state: "RUNNING",
                    technicalStatus: "PENDING",
                    routeRef: "RETRY_THEN_SUCCESS@1",
                    startedAt: "2026-08-21T12:00:00Z",
                    durationMs: 1200,
                  },
                ],
                nextCursorStartedAt: "",
                nextCursorExecutionId: "",
              }),
          };
        }
        return {
          ok: false,
          status: 404,
          text: async () => JSON.stringify({ title: "Not Found", status: 404 }),
        };
      }),
    );
  });

  it("shows list and opens detail without legacy calls", async () => {
    render(<ConsoleShell />);
    fireEvent.click(screen.getByRole("button", { name: "Execuções" }));
    await waitFor(() => expect(screen.getByText(/RETRY_THEN_SUCCESS/)).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /ex-1|…/ }));
    await waitFor(() => expect(screen.getByText("Journey map")).toBeInTheDocument());
    const calls = fetch.mock.calls.map((c) => String(c[0]));
    expect(calls.some((u) => u.includes("/v1/products/orchestrate"))).toBe(false);
    expect(calls.some((u) => u.includes("/v1/console/executions"))).toBe(true);
  });

  it("shows unavailable banner when console API is off", async () => {
    fetch.mockImplementation(async () => ({
      ok: false,
      status: 404,
      text: async () => JSON.stringify({ title: "Not Found", status: 404 }),
    }));
    render(<ConsoleShell />);
    await waitFor(() => expect(screen.getByText(/Console indisponível/i)).toBeInTheDocument());
  });

  it("renders operational cockpit from canonical health API", async () => {
    render(<ConsoleShell />);
    fireEvent.click(screen.getByRole("button", { name: "Cockpit Operacional" }));
    await waitFor(() =>
      expect(screen.getByText("Confiabilidade técnica")).toBeInTheDocument(),
    );
    expect(screen.getByText(/MOCK_ONLY/)).toBeInTheDocument();
    expect(screen.getByText(/PROVISÓRIOS/)).toBeInTheDocument();
    expect(screen.getByText(/99.0%/)).toBeInTheDocument();
    expect(fetch.mock.calls.some((call) => String(call[0]).includes("window=PT24H"))).toBe(true);
  });

  it("renders failure lab surface from the catalog API", async () => {
    fetch.mockImplementation(async (url) => {
      if (String(url).includes("/v1/console/failure-lab/scenarios")) {
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              schemaVersion: 1,
              boundary: "MOCK_ONLY",
              scenarios: [
                {
                  schemaVersion: 1,
                  code: "RETRY_THEN_SUCCESS",
                  version: "1.0",
                  title: "Falha transitória seguida de sucesso",
                  functionalDescription: "Retentativa absorve a indisponibilidade momentânea.",
                  category: "RETRY",
                  targetBoundary: "MOCK_ONLY",
                  expectedObservations: [],
                  maximumDuration: "PT2M",
                  maximumExecutions: 1,
                  runbookRef: "runbook:failure-lab:retry@1.0",
                },
              ],
              runbooks: [],
            }),
        };
      }
      return {
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({ items: [], nextCursorStartedAt: "", nextCursorExecutionId: "" }),
      };
    });
    render(<ConsoleShell />);
    fireEvent.click(screen.getByRole("button", { name: "Failure Lab" }));
    await waitFor(() =>
      expect(screen.getByTestId("failure-lab-scenario-RETRY_THEN_SUCCESS")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("failure-lab-boundary-banner")).toHaveTextContent(
      "FALHAS SIMULADAS",
    );
    expect(screen.getByRole("button", { name: "Laboratório Mock" })).toBeInTheDocument();
  });

  it("renders the worker runtime surface from the runtime API", async () => {
    fetch.mockImplementation(async (url) => {
      if (String(url).endsWith("/v1/console/runtime")) {
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              schemaVersion: 1,
              calculatedAt: "2026-08-25T12:00:00Z",
              boundary: "SIMULATED_INFRASTRUCTURE",
              integrationBoundary: "MOCK_ONLY",
              runtimeStatus: "HEALTHY",
              workers: [
                {
                  workerId: "wrk-inst-1:wait_expiry",
                  runtimeInstanceId: "wrk-inst-1",
                  workerType: "WAIT_EXPIRY",
                  status: "RUNNING",
                  lastHeartbeatAt: "2026-08-25T11:59:58Z",
                  currentClaims: 0,
                  processedCount: 4,
                  failureCount: 0,
                  version: 3,
                },
              ],
              schedules: [
                {
                  scheduleCode: "schedule:wait-expiry",
                  version: 2,
                  scheduleVersion: "1.0",
                  workerType: "WAIT_EXPIRY",
                  enabled: true,
                  interval: "PT10S",
                  nextEligibleAt: "2026-08-25T12:00:10Z",
                  lastOutcome: "SUCCESS",
                  ownerWorkerId: null,
                  leaseUntil: null,
                  fencingToken: 5,
                },
              ],
              backlogs: [
                {
                  schemaVersion: 1,
                  workerType: "WAIT_EXPIRY",
                  status: "EMPTY",
                  eligibleCount: 0,
                  oldestEligibleAgeMs: null,
                  approximate: false,
                  explanation: "",
                },
              ],
              staleWorkers: 0,
              expiredLeases: 0,
              oldestPendingAgeMs: null,
              dataQuality: { complete: true, missingSources: [], warnings: [] },
            }),
        };
      }
      return {
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({ items: [], nextCursorStartedAt: "", nextCursorExecutionId: "" }),
      };
    });
    render(<ConsoleShell />);
    fireEvent.click(screen.getByRole("button", { name: "Runtime de Workers" }));
    await waitFor(() =>
      expect(screen.getByTestId("worker-runtime-worker-wrk-inst-1:wait_expiry")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("worker-runtime-boundary-banner")).toHaveTextContent(
      "INFRAESTRUTURA SIMULADA",
    );
    expect(screen.getByTestId("worker-runtime-schedule-schedule:wait-expiry")).toHaveTextContent(
      "schedule:wait-expiry",
    );
  });

  it("lab submits to canonical endpoint", async () => {
    const spy = fetch;
    spy.mockImplementation(async (url, init) => {
      if (String(url).includes("/v1/canonical/executions") && init?.method === "POST") {
        return {
          ok: true,
          status: 202,
          text: async () => JSON.stringify({ executionId: "ex-new" }),
        };
      }
      if (String(url).includes("/v1/console/executions")) {
        return {
          ok: true,
          status: 200,
          text: async () => JSON.stringify({ items: [], nextCursorStartedAt: "", nextCursorExecutionId: "" }),
        };
      }
      return { ok: false, status: 404, text: async () => "{}" };
    });
    render(<ConsoleShell />);
    fireEvent.click(screen.getByRole("button", { name: "Laboratório Mock" }));
    fireEvent.click(screen.getAllByRole("button", { name: "Executar" })[1]);
    await waitFor(() =>
      expect(spy.mock.calls.some((c) => String(c[0]).includes("/v1/canonical/executions"))).toBe(
        true,
      ),
    );
    expect(spy.mock.calls.some((c) => String(c[0]).includes("/v1/products/orchestrate"))).toBe(
      false,
    );
  });
});

describe("Implementation & Presentation", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        text: async () => JSON.stringify({ items: [] }),
      })),
    );
  });

  it("renders cockpit from API response", async () => {
    fetch.mockImplementation(async (url) => {
      if (String(url).includes("/v1/console/implementation")) {
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              currentPrompt: "SPIDER-PROMPT-015",
              currentGroup: "GROUP_A_VISIBILITY_OBSERVABILITY",
              productVersion: "0.15.0",
              lastVerifiedAt: "2026-08-21T20:00:00Z",
              mockRealBoundary: "MOCK_ONLY",
              governanceMode: "STATIC",
              baseline: { backendTests: 186, frontendTests: 10, failures: 0, errors: 0, skipped: 0 },
              groups: [
                {
                  groupCode: "GROUP_A_VISIBILITY_OBSERVABILITY",
                  verified: 1,
                  planned: 3,
                  denominator: 4,
                  journey: true,
                },
              ],
              capabilities: [
                {
                  capabilityCode: "CAP-015",
                  groupCode: "GROUP_A_VISIBILITY_OBSERVABILITY",
                  promptRef: "SPIDER-PROMPT-015",
                  title: "Console Operacional Canônico e Visualização da Execução",
                  objective: "Console, cockpit e apresentação dinâmica",
                  status: "VERIFIED",
                  runtimeAvailability: "OFF_BY_DEFAULT",
                  integrationLevel: "MOCK_ONLY",
                  dependencies: ["CAP-014"],
                },
                {
                  capabilityCode: "CAP-016",
                  groupCode: "GROUP_A_VISIBILITY_OBSERVABILITY",
                  promptRef: "SPIDER-PROMPT-016",
                  title: "Telemetria Canônica e Operational Events",
                  objective: "Logs, métricas, traces e eventos correlacionados",
                  status: "PLANNED",
                  runtimeAvailability: "NOT_IMPLEMENTED",
                  integrationLevel: "MOCK_ONLY",
                  dependencies: ["CAP-015"],
                },
              ],
              effectiveFlags: { "spider.console.enabled": true },
            }),
        };
      }
      return {
        ok: true,
        status: 200,
        text: async () => JSON.stringify({ items: [] }),
      };
    });
    render(<ConsoleShell />);
    fireEvent.click(screen.getByRole("button", { name: "Implementação" }));
    await waitFor(() => expect(screen.getByText(/Cockpit da implementação/i)).toBeInTheDocument());
    expect(screen.getAllByText(/MOCK_ONLY/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText("SPIDER-PROMPT-015").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Verificado/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Telemetria Canônica/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Legacy Endpoint Migration/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Production Cutover/i)).not.toBeInTheDocument();
  });

  it("blocks presentation journey when not ready", async () => {
    fetch.mockImplementation(async (url) => {
      if (String(url).includes("/presentation/readiness")) {
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              ready: false,
              boundary: "MOCK_ONLY",
              manifestStatus: "VALID",
              checks: [
                { code: "console_api_enabled", passed: false, message: "Console HTTP disabled" },
              ],
              availableScenarios: [],
              failingChecks: ["console_api_enabled"],
            }),
        };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify({ items: [] }) };
    });
    render(<ConsoleShell />);
    fireEvent.click(screen.getByRole("button", { name: "Apresentação" }));
    await waitFor(() => expect(screen.getByText(/NOT READY/i)).toBeInTheDocument());
    expect(screen.getByText(/Demonstração bloqueada/i)).toBeInTheDocument();
  });
});
