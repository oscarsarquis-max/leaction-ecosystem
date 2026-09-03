import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ConsoleShell from "./ConsoleShell";

const intentContract = {
  schemaVersion: "1.0",
  intent: "INVESTIGATE_CREDIT_RELEASE",
  domain: "CREDIT",
  objective: "IDENTIFY_BLOCKING_CONDITION",
  entities: { proposalId: "DEMO-PROPOSAL-001" },
  constraints: { mutationAllowed: false, readOnly: true, confirmationRequired: true },
  provenance: { source: "BUSINESS_CARD", sourceRef: "context-catalog:credit" },
  confidence: 1,
};

const executionPlan = {
  schemaVersion: "1.0",
  planId: "ctxp-credit",
  planType: "CREDIT_RELEASE_INVESTIGATION_PLAN_V1",
  intent: intentContract.intent,
  status: "READY",
  statusReasons: [],
  steps: [{ stepId: "credit-01", capabilityId: "CREDIT_RELEASE_DIAGNOSTIC" }],
};

const capabilities = [
  {
    stepId: "credit-01",
    capabilityId: "CREDIT_RELEASE_DIAGNOSTIC",
    description: "Investigar bloqueio.",
    reason: "Identificar condição bloqueadora.",
    inputContract: "spider-capability://input/credit/v1",
    outputContract: "spider-capability://output/credit/v1",
    availability: "AVAILABLE",
    status: "RESOLVED",
    selectedRoute: {
      routeRef: "CREDIT_RELEASE_DIAGNOSTIC_V1",
      adapterRef: "mock-universal",
      targetOperation: "RETRY_THEN_SUCCESS",
    },
  },
];

const contextJourney = [
  {
    id: "objective-selected",
    title: "Objetivo selecionado",
    state: "SUCCEEDED",
    summary: "Situação selecionada.",
    technicalDetails: { domain: "CREDIT" },
  },
  {
    id: "intent-created",
    title: "Intent construído",
    state: "SUCCEEDED",
    summary: "Intent Contract materializado.",
    technicalDetails: { intent: intentContract.intent, provenance: "BUSINESS_CARD" },
  },
  {
    id: "policy-validated",
    title: "Política validada",
    state: "SUCCEEDED",
    summary: "Policy aceita.",
    technicalDetails: { policyRef: "context:read-only@1.0" },
  },
  {
    id: "execution-plan-resolved",
    title: "Plano determinado",
    state: "SUCCEEDED",
    summary: "Plano determinístico composto.",
    technicalDetails: { planType: executionPlan.planType },
  },
  {
    id: "capabilities-resolved",
    title: "Capabilities resolvidas",
    state: "SUCCEEDED",
    summary: "Capabilities avaliadas.",
    technicalDetails: { resolvedCapabilities: "1" },
  },
  {
    id: "plan-capability-credit-01",
    title: "CREDIT_RELEASE_DIAGNOSTIC",
    layer: "PLAN",
    state: "SUCCEEDED",
    summary: "Capability resolvida.",
    technicalDetails: { capabilityRef: "CREDIT_RELEASE_DIAGNOSTIC" },
  },
  {
    id: "route-resolved",
    title: "Rota determinada",
    layer: "PLAN",
    state: "SUCCEEDED",
    summary: "Rota resolvida.",
    technicalDetails: { routeRef: "CREDIT_RELEASE_DIAGNOSTIC_V1" },
  },
];

function response(data, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(data),
  };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Context Home to Journey", () => {
  it("keeps preview separate, confirms through Context Plane and follows the real journey", async () => {
    const calls = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url, init = {}) => {
        const path = String(url);
        calls.push([path, init]);
        if (path === "/actuator/health") return response({ status: "UP" });
        if (path === "/v1/console/implementation") {
          return response({ productVersion: "0.20.0" });
        }
        if (path === "/v1/console/presentation/readiness") {
          return response({ ready: true, boundary: "MOCK_ONLY" });
        }
        if (path === "/v1/context/intents" && (!init.method || init.method === "GET")) {
          return response({
            contextEnabled: true,
            uiEnabled: true,
            aiEnabled: false,
            items: [
              {
                domain: "CREDIT",
                domainLabel: "Crédito",
                intent: intentContract.intent,
                title: "Investigar liberação de proposta",
                description: "Entender por que uma proposta de crédito não foi liberada.",
                intentContract,
              },
            ],
          });
        }
        if (path === "/v1/context/intents/resolve") {
          return response({
            decisionId: "ctxd-1",
            decision: "ACCEPTED",
            policyRef: "context:read-only@1.0",
            intentContract,
            executionPlan,
            capabilities,
            route: {
              capabilityRef: "CREDIT_RELEASE_DIAGNOSTIC",
              routeRef: "CREDIT_RELEASE_DIAGNOSTIC_V1",
              executable: true,
            },
            contextJourney,
          });
        }
        if (path === "/v1/context/executions" && init.method === "POST") {
          return response({
            executionId: "exec-context-1",
            state: "SUCCEEDED",
            context: {
              decisionId: "ctxd-1",
              decision: "ACCEPTED",
              intentContract,
              contextJourney,
            },
          });
        }
        if (path === "/v1/context/executions/exec-context-1") {
          return response({
            decisionId: "ctxd-1",
            executionId: "exec-context-1",
            intentContract,
            contextJourney,
          });
        }
        if (path === "/v1/console/executions/exec-context-1/events") {
          return response({
            items: [
              { eventType: "INTENT_CREATED", category: "CONTEXT", outcome: "SUCCESS" },
              { eventType: "INTENT_VALIDATED", category: "CONTEXT", outcome: "SUCCESS" },
              { eventType: "ROUTE_RESOLVED", category: "CONTEXT", outcome: "SUCCESS" },
              { eventType: "EXECUTION_SUCCEEDED", category: "EXECUTION", outcome: "SUCCESS" },
            ],
          });
        }
        if (path === "/v1/console/executions/exec-context-1") {
          return response({
            summary: {
              executionId: "exec-context-1",
              state: "SUCCEEDED",
              technicalStatus: "SUCCESS",
              routeRef: "RETRY_THEN_SUCCESS@1",
              startedAt: "2026-09-03T12:00:00Z",
            },
            timeline: {
              available: true,
              data: [{ eventType: "STATE_TRANSITION", title: "RECEIVED → RUNNING" }],
            },
            steps: {
              available: true,
              data: [{ stepRef: "step-1", state: "SUCCEEDED", attemptCount: 1 }],
            },
            waitInfo: { available: false },
            callback: { available: false },
          });
        }
        if (path === "/v1/console/executions") return response({ items: [] });
        if (path === "/v1/canonical/executions") return response({ items: [] });
        throw new Error(`Unexpected request: ${path}`);
      }),
    );

    render(<ConsoleShell />);
    await screen.findByRole("button", { name: "Investigar" });
    fireEvent.click(screen.getByRole("button", { name: "Investigar" }));

    const preview = await screen.findByTestId("intent-preview");
    expect(preview).toHaveTextContent("SPIDER ENTENDEU");
    expect(preview).toHaveTextContent("BUSINESS_CARD");
    expect(preview).toHaveTextContent("100%");
    expect(preview).toHaveTextContent("SOMENTE CONSULTA");
    expect(preview).toHaveTextContent("ACCEPTED · context:read-only@1.0");
    expect(preview).toHaveTextContent("CREDIT_RELEASE_INVESTIGATION_PLAN_V1");
    fireEvent.click(screen.getByRole("button", { name: /CREDIT_RELEASE_DIAGNOSTIC/ }));
    expect(preview).toHaveTextContent("CREDIT_RELEASE_DIAGNOSTIC_V1");
    expect(calls.filter(([path]) => path === "/v1/context/executions")).toHaveLength(0);

    fireEvent.click(screen.getByRole("button", { name: "Executar" }));
    await waitFor(() =>
      expect(screen.getByTestId("home-current-execution")).toHaveTextContent("exec-context-1"),
    );
    await waitFor(() =>
      expect(screen.getByTestId("journey-stage-context-route-resolved")).toHaveAttribute(
        "data-state",
        "SUCCEEDED",
      ),
    );
    expect(screen.getByText("CONTEXTO")).toBeInTheDocument();
    expect(screen.getByTestId("journey-zone-plan")).toHaveTextContent("PLANO");
    expect(screen.getByText("DATA PLANE")).toBeInTheDocument();
    expect(screen.getByTestId("objective-journey")).toBeInTheDocument();
    expect(screen.getByTestId("objective-phase-execution")).toHaveAttribute(
      "data-state",
      "SUCCEEDED",
    );
    expect(screen.getByTestId("journey-stage-request")).toBeInTheDocument();
    expect(calls.some(([path]) => path === "/v1/console/executions/exec-context-1")).toBe(true);
    expect(
      calls.some(([path]) => /openai|anthropic|bedrock|ollama|\/llm|\/ai\//i.test(path)),
    ).toBe(false);
  });
});
