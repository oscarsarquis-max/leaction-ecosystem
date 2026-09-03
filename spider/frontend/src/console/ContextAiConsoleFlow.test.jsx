import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import ConsoleShell from "./ConsoleShell";

const contract = {
  schemaVersion: "1.0",
  intent: "INVESTIGATE_CREDIT_RELEASE",
  domain: "CREDIT",
  objective: "IDENTIFY_BLOCKING_CONDITION",
  entities: { proposalId: "12345" },
  constraints: { mutationAllowed: false, readOnly: true, confirmationRequired: true },
  provenance: { source: "NATURAL_LANGUAGE", sourceRef: "context-ai:ctxi-1" },
  confidence: 0.94,
};

const executionPlan = {
  schemaVersion: "1.0",
  planId: "ctxp-credit",
  planType: "CREDIT_RELEASE_INVESTIGATION_PLAN_V1",
  intent: contract.intent,
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

const journey = [
  {
    id: "objective-received",
    title: "Objetivo recebido",
    state: "SUCCEEDED",
    summary: "Objetivo seguro recebido.",
    technicalDetails: { requestedObjective: "Verifique a proposta 12345." },
  },
  {
    id: "ai-interpreted",
    title: "IA interpretou contexto",
    state: "SUCCEEDED",
    summary: "A IA produziu somente uma decisão estruturada de intenção.",
    technicalDetails: {
      intent: contract.intent,
      domain: contract.domain,
      provider: "aws-bedrock-anthropic",
      model: "anthropic.test",
      promptVersion: "CTX-INTERPRETER-1.0",
    },
  },
  {
    id: "intent-created",
    title: "Intent construído",
    state: "SUCCEEDED",
    summary: "Intent Contract V1 materializado.",
    technicalDetails: { intent: contract.intent },
  },
  {
    id: "policy-validated",
    title: "Política validada",
    state: "SUCCEEDED",
    summary: "Guard aceitou.",
    technicalDetails: { policyRef: "context:read-only@1.0" },
  },
  {
    id: "execution-plan-resolved",
    title: "Plano determinado",
    state: "SUCCEEDED",
    summary: "Plano determinístico composto.",
    technicalDetails: { planType: executionPlan.planType, planId: executionPlan.planId },
  },
  {
    id: "capabilities-resolved",
    title: "Capabilities resolvidas",
    state: "SUCCEEDED",
    summary: "Capabilities avaliadas.",
    technicalDetails: { resolvedCapabilities: "1", unavailableCapabilities: "0" },
  },
  {
    id: "plan-capability-credit-01",
    title: "CREDIT_RELEASE_DIAGNOSTIC",
    layer: "PLAN",
    state: "SUCCEEDED",
    summary: "Capability resolvida, ainda não executada.",
    technicalDetails: {
      capabilityRef: "CREDIT_RELEASE_DIAGNOSTIC",
      routeRef: "CREDIT_RELEASE_DIAGNOSTIC_V1",
    },
  },
  {
    id: "route-resolved",
    title: "Rota determinada",
    layer: "PLAN",
    state: "SUCCEEDED",
    summary: "Router determinístico resolveu a rota.",
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

it("converges natural language into the existing preview, confirmation and journey", async () => {
  const calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url, init = {}) => {
      const path = String(url);
      calls.push([path, init]);
      if (path === "/actuator/health") return response({ status: "UP" });
      if (path === "/v1/console/implementation") return response({ productVersion: "0.20.0" });
      if (path === "/v1/console/presentation/readiness") {
        return response({ ready: true, boundary: "MOCK_ONLY" });
      }
      if (path === "/v1/context/intents") {
        return response({
          contextEnabled: true,
          uiEnabled: true,
          aiEnabled: true,
          aiState: "ACTIVE",
          aiProvider: "aws-bedrock-anthropic",
          items: [
            {
              domain: "CREDIT",
              domainLabel: "Crédito",
              intent: contract.intent,
              title: "Investigar liberação de proposta",
              description: "Entender por que uma proposta de crédito não foi liberada.",
              intentContract: { ...contract, provenance: { source: "BUSINESS_CARD" }, confidence: 1 },
            },
          ],
        });
      }
      if (path === "/v1/context/interpretations") {
        return response({
          status: "SUCCEEDED",
          aiState: "ACTIVE",
          message: "Objetivo interpretado.",
          requestedObjective: "Verifique a proposta 12345.",
          interpretation: {
            interpretationId: "ctxi-1",
            missingContext: [],
            candidateIntents: [],
          },
          decision: {
            decisionId: "ctxd-ai",
            decision: "ACCEPTED",
            policyRef: "context:read-only@1.0",
            intentContract: contract,
            executionPlan,
            capabilities,
            route: {
              capabilityRef: "CREDIT_RELEASE_DIAGNOSTIC",
              routeRef: "CREDIT_RELEASE_DIAGNOSTIC_V1",
              executable: true,
            },
            contextJourney: journey,
          },
        });
      }
      if (path === "/v1/context/executions") {
        return response({
          executionId: "exec-ai-1",
          state: "SUCCEEDED",
          context: {
            decisionId: "ctxd-ai",
            executionId: "exec-ai-1",
            intentContract: contract,
            contextJourney: journey,
          },
        });
      }
      if (path === "/v1/context/executions/exec-ai-1") {
        return response({
          decisionId: "ctxd-ai",
          executionId: "exec-ai-1",
          intentContract: contract,
          contextJourney: journey,
        });
      }
      if (path === "/v1/console/executions/exec-ai-1/events") {
        return response({
          items: [
            { eventType: "AI_INTERPRETATION_SUCCEEDED", category: "CONTEXT" },
            { eventType: "EXECUTION_SUCCEEDED", category: "EXECUTION" },
          ],
        });
      }
      if (path === "/v1/console/executions/exec-ai-1") {
        return response({
          summary: { executionId: "exec-ai-1", state: "SUCCEEDED" },
          timeline: { available: true, data: [] },
          steps: { available: true, data: [] },
          waitInfo: { available: false },
          callback: { available: false },
        });
      }
      if (path === "/v1/console/executions" || path === "/v1/canonical/executions") {
        return response({ items: [] });
      }
      throw new Error(`Unexpected request: ${path}`);
    }),
  );

  render(<ConsoleShell />);
  const field = await screen.findByLabelText("Interpretação em linguagem natural");
  fireEvent.change(field, { target: { value: "Verifique a proposta 12345." } });
  fireEvent.click(screen.getByRole("button", { name: "Interpretar" }));

  const preview = await screen.findByTestId("intent-preview");
  expect(preview).toHaveTextContent("NATURAL_LANGUAGE");
  expect(preview).toHaveTextContent("94%");
  expect(calls.filter(([path]) => path === "/v1/context/executions")).toHaveLength(0);

  fireEvent.click(screen.getByRole("button", { name: "Executar" }));
  await waitFor(() =>
    expect(screen.getByTestId("journey-stage-context-ai-interpreted")).toBeInTheDocument(),
  );
  fireEvent.click(screen.getByRole("button", { name: /IA interpretou contexto/ }));
  expect(screen.getByTestId("journey-step-detail")).toHaveTextContent("aws-bedrock-anthropic");
  expect(screen.getByText("DATA PLANE")).toBeInTheDocument();
});
