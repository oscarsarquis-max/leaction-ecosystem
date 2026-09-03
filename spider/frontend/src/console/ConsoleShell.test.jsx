import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import ConsoleShell from "../console/ConsoleShell.jsx";
import { JourneyMap, SecurityPosturePanel, TimelineView, OperationalTimelineView } from "../console/components.jsx";
import { isTerminalState, extractCanonicalExecutionId } from "../console/api.js";
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

  it("extracts nested canonical execution identity", () => {
    expect(extractCanonicalExecutionId({ execution: { executionId: "exec-nested" } })).toBe(
      "exec-nested",
    );
    expect(extractCanonicalExecutionId({ executionId: "exec-top" })).toBe("exec-top");
    expect(extractCanonicalExecutionId({ code: "UNAUTHENTICATED" }, "exec-fallback")).toBe(
      "exec-fallback",
    );
    expect(extractCanonicalExecutionId(null)).toBe(null);
  });
});

describe("scenarios", () => {
  it("builds canonical request without legacy fields", () => {
    const body = buildCanonicalRequest(MOCK_SCENARIOS[1], {
      idempotencyKey: "idem-x",
      traceparent: "00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01",
    });
    expect(body.target.operation).toBe("RETRY_THEN_SUCCESS");
    expect(body.execution.executionId).toMatch(/^exec-[0-9a-f-]{36}$/i);
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
        if (String(url).includes("/actuator/health")) {
          return { ok: true, status: 200, text: async () => JSON.stringify({ status: "UP" }) };
        }
        if (String(url).includes("/v1/console/implementation")) {
          return {
            ok: true,
            status: 200,
            text: async () =>
              JSON.stringify({
                productVersion: "0.20.0",
                currentPrompt: "SPIDER-PROMPT-020",
                mockRealBoundary: "MOCK_ONLY",
              }),
          };
        }
        if (String(url).includes("/v1/console/presentation/readiness")) {
          return {
            ok: true,
            status: 200,
            text: async () =>
              JSON.stringify({ ready: true, runtimeVersion: "spider@0.20.0", boundary: "MOCK_ONLY" }),
          };
        }
        if (String(url).includes("/v1/canonical/executions") && (!init || !init.method || init.method === "GET")) {
          return {
            ok: true,
            status: 200,
            text: async () =>
              JSON.stringify({
                items: [
                  {
                    executionId: "demo-retry-001",
                    state: "SUCCEEDED",
                    technicalStatus: "SUCCESS",
                    startedAt: "2026-08-21T18:00:00Z",
                    durationMs: 3000,
                  },
                ],
              }),
          };
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
    fireEvent.click(screen.getAllByRole("button", { name: "Execuções" })[0]);
    await waitFor(() => expect(screen.getByText(/RETRY_THEN_SUCCESS/)).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /ex-1|…/ }));
    await waitFor(() => expect(screen.getByText("Por onde passou?")).toBeInTheDocument());
    expect(screen.getByText("Quando aconteceu?")).toBeInTheDocument();
    expect(screen.getByText("O que tecnicamente ocorreu?")).toBeInTheDocument();
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

  it("opens on the operational home with platform status and recent executions", async () => {
    render(<ConsoleShell />);
    expect(screen.getByRole("heading", { name: "Home operacional" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "SPIDER" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Spider 0.20.0")).toBeInTheDocument());
    expect(screen.getByText("UP")).toBeInTheDocument();
    expect(screen.getByText("READY")).toBeInTheDocument();
    expect(screen.getByText("SIMULATED_INFRASTRUCTURE")).toBeInTheDocument();
    expect(screen.getByText("MOCK_ONLY")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Executar demonstração" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Abrir" })).toBeInTheDocument());
    expect(screen.queryByRole("heading", { name: "Observação do Data Plane" })).not.toBeInTheDocument();
    expect(screen.getByTestId("nav-group-operation")).toBeInTheDocument();
    expect(screen.getByTestId("nav-group-tests")).toBeInTheDocument();
    expect(screen.getByTestId("nav-group-platform")).toBeInTheDocument();
  });

  it("projects the visual journey on home after selecting a recent execution", async () => {
    render(<ConsoleShell />);
    fireEvent.click(await screen.findByRole("button", { name: "Abrir" }));
    await waitFor(() => expect(screen.getByTestId("execution-journey")).toBeInTheDocument());
    expect(screen.getByTestId("journey-stage-request")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Home operacional" })).toBeInTheDocument();
  });

  it("primary action submits the existing canonical execution flow", async () => {
    fetch.mockImplementation(async (url, init) => {
      if (String(url).includes("/v1/canonical/executions") && init?.method === "POST") {
        return {
          ok: true,
          status: 202,
          text: async () => JSON.stringify({ executionId: "ex-demo" }),
        };
      }
      if (String(url).includes("/v1/canonical/executions")) {
        return { ok: true, status: 200, text: async () => JSON.stringify({ items: [] }) };
      }
      if (String(url).includes("/actuator/health")) {
        return { ok: true, status: 200, text: async () => JSON.stringify({ status: "UP" }) };
      }
      if (String(url).includes("/v1/console/implementation")) {
        return { ok: true, status: 200, text: async () => JSON.stringify({ productVersion: "0.20.0" }) };
      }
      if (String(url).includes("/v1/console/presentation/readiness")) {
        return {
          ok: true,
          status: 200,
          text: async () => JSON.stringify({ ready: true, boundary: "MOCK_ONLY" }),
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
    fireEvent.click(screen.getByRole("button", { name: "Executar demonstração" }));
    await waitFor(() =>
      expect(
        fetch.mock.calls.some(
          (c) => String(c[0]).includes("/v1/canonical/executions") && c[1]?.method === "POST",
        ),
      ).toBe(true),
    );
    expect(fetch.mock.calls.some((c) => String(c[0]).includes("/v1/products/orchestrate"))).toBe(false);
  });

  it("follows a Home demo into the live journey without showing raw JSON", async () => {
    const detailHits = [];
    fetch.mockImplementation(async (url, init) => {
      const path = String(url);
      if (path.includes("/v1/products/orchestrate")) {
        throw new Error("legacy must not be called");
      }
      if (path.includes("/v1/canonical/executions") && init?.method === "POST") {
        const posted = JSON.parse(init.body);
        const id = posted.execution.executionId;
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              contract: { schemaVersion: "1.0" },
              execution: { executionId: id, state: "SUCCEEDED" },
            }),
        };
      }
      if (path.includes("/actuator/health")) {
        return { ok: true, status: 200, text: async () => JSON.stringify({ status: "UP" }) };
      }
      if (path.includes("/v1/console/implementation")) {
        return { ok: true, status: 200, text: async () => JSON.stringify({ productVersion: "0.20.0" }) };
      }
      if (path.includes("/v1/console/presentation/readiness")) {
        return {
          ok: true,
          status: 200,
          text: async () => JSON.stringify({ ready: true, boundary: "MOCK_ONLY" }),
        };
      }
      if (path.includes("/v1/canonical/executions")) {
        return { ok: true, status: 200, text: async () => JSON.stringify({ items: [] }) };
      }
      if (path.includes("/events")) {
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              items: [{ eventType: "EXECUTION_STARTED" }, { eventType: "EXECUTION_SUCCEEDED" }],
            }),
        };
      }
      if (path.includes("/v1/console/executions/")) {
        detailHits.push(path);
        const id = decodeURIComponent(path.split("/").pop());
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              summary: {
                executionId: id,
                state: "SUCCEEDED",
                technicalStatus: "SUCCESS",
                routeRef: "RETRY_THEN_SUCCESS@1",
                startedAt: "2026-09-03T12:00:00Z",
              },
              timeline: {
                available: true,
                data: [
                  { eventType: "STATE_TRANSITION", title: "Transição RECEIVED → RUNNING", source: "PERSISTED" },
                  { eventType: "ATTEMPT", attemptNumber: 1, state: "FAILED", title: "Attempt #1" },
                  { eventType: "ATTEMPT", attemptNumber: 2, state: "SUCCEEDED", title: "Attempt #2" },
                ],
              },
              steps: {
                available: true,
                data: [
                  {
                    stepRef: "step-1",
                    state: "SUCCEEDED",
                    attemptCount: 2,
                    attempts: [
                      { attemptNumber: 1, state: "FAILED" },
                      { attemptNumber: 2, state: "SUCCEEDED" },
                    ],
                  },
                ],
              },
              waitInfo: { available: false },
              callback: { available: false },
            }),
        };
      }
      if (path.includes("/v1/console/executions")) {
        return {
          ok: true,
          status: 200,
          text: async () => JSON.stringify({ items: [], nextCursorStartedAt: "", nextCursorExecutionId: "" }),
        };
      }
      return { ok: false, status: 404, text: async () => "{}" };
    });

    render(<ConsoleShell />);
    fireEvent.click(screen.getByRole("button", { name: "Executar demonstração" }));

    await waitFor(() => expect(screen.getByTestId("home-current-execution")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByTestId("execution-journey")).toBeInTheDocument());
    expect(screen.getByText(/Execução iniciada — acompanhando/)).toBeInTheDocument();
    expect(screen.queryByText(/Submetido\. Resposta:/)).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Home operacional" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Execução atual" })).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByTestId("journey-stage-interaction-step-1-1")).toHaveAttribute(
        "data-state",
        "FAILED",
      ),
    );
    expect(screen.getByTestId("journey-stage-retry-step-1-1")).toBeInTheDocument();
    expect(screen.getByTestId("journey-stage-interaction-step-1-2")).toHaveAttribute("data-state", "SUCCEEDED");
    expect(screen.getByTestId("journey-stage-completion")).toHaveAttribute("data-state", "SUCCEEDED");

    const posted = fetch.mock.calls.find(
      (c) => String(c[0]).includes("/v1/canonical/executions") && c[1]?.method === "POST",
    );
    const postedId = JSON.parse(posted[1].body).execution.executionId;
    expect(detailHits.some((u) => u.includes(postedId))).toBe(true);
    expect(screen.getByTestId("home-current-execution")).toHaveTextContent(postedId);

    const afterTerminal = detailHits.length;
    await new Promise((resolve) => setTimeout(resolve, 80));
    expect(detailHits.length).toBe(afterTerminal);
  });

  it("shows an error when canonical executions cannot be listed", async () => {
    fetch.mockImplementation(async (url) => {
      if (String(url).includes("/v1/canonical/executions")) {
        return {
          ok: false,
          status: 401,
          text: async () => JSON.stringify({ code: "UNAUTHENTICATED", title: "UNAUTHENTICATED" }),
        };
      }
      if (String(url).includes("/actuator/health")) {
        return { ok: true, status: 200, text: async () => JSON.stringify({ status: "UP" }) };
      }
      if (String(url).includes("/v1/console/implementation")) {
        return { ok: true, status: 200, text: async () => JSON.stringify({ productVersion: "0.20.0" }) };
      }
      if (String(url).includes("/v1/console/presentation/readiness")) {
        return {
          ok: true,
          status: 200,
          text: async () => JSON.stringify({ ready: true, boundary: "MOCK_ONLY" }),
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
    await waitFor(() =>
      expect(screen.getByText(/Falha ao listar execuções canônicas \(401\)/)).toBeInTheDocument(),
    );
  });

  it("keeps navigation to preserved operational surfaces", async () => {
    render(<ConsoleShell />);
    for (const name of [
      "Execuções",
      "Cockpit Operacional",
      "Failure Lab",
      "Runtime de Workers",
      "Capacidade & Resiliência",
      "Implementação",
      "Apresentação",
      "Laboratório Mock",
    ]) {
      expect(screen.getAllByRole("button", { name }).length).toBeGreaterThan(0);
    }
    expect(screen.getByTestId("nav-group-executions")).toHaveTextContent("Detalhe");
    fireEvent.click(screen.getAllByRole("button", { name: "Execuções" })[0]);
    expect(screen.getByRole("heading", { name: "Execuções" })).toBeInTheDocument();
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
    expect(screen.getAllByRole("button", { name: "Laboratório Mock" }).length).toBeGreaterThan(0);
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

  it("renders the capacity and resilience surface from the capacity API", async () => {
    fetch.mockImplementation(async (url) => {
      if (String(url).endsWith("/v1/console/capacity")) {
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              schemaVersion: 1,
              calculatedAt: new Date().toISOString(),
              boundary: "SIMULATED_INFRASTRUCTURE",
              integrationBoundary: "MOCK_ONLY",
              mode: "MONITOR_ONLY",
              policies: [],
              pressure: [
                {
                  schemaVersion: 1,
                  scopeKey: "GLOBAL:GLOBAL",
                  scopeType: "GLOBAL",
                  scopeRef: "GLOBAL",
                  policyRef: "capacity:global@1.0",
                  level: "NORMAL",
                  occupied: 0,
                  capacity: 8,
                  utilizationPercent: 0,
                  backlogCount: 0,
                  softBacklogLimit: 20,
                  hardBacklogLimit: 50,
                  quotaUsed: 0,
                  quotaLimit: 0,
                  circuitPhase: "CLOSED",
                  observedAt: new Date().toISOString(),
                  explanation: "Escopo dentro dos limites declarados.",
                },
              ],
              bulkheads: [],
              circuits: [],
              recentDecisions: [],
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
    fireEvent.click(screen.getByRole("button", { name: "Capacidade & Resiliência" }));
    await waitFor(() =>
      expect(screen.getByTestId("capacity-pressure-GLOBAL:GLOBAL")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("capacity-boundary-banner")).toHaveTextContent(
      "SEM CAPACIDADE PRODUTIVA AFERIDA",
    );
    expect(screen.getByTestId("capacity-mode")).toHaveTextContent("Somente observação");
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
    fireEvent.click(screen.getAllByRole("button", { name: "Laboratório Mock" })[0]);
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
