import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import ContextIntelligence from "./ContextIntelligence";

const capabilityIds = [
  "IDENTIFY_CUSTOMER",
  "GET_CUSTOMER_PROFILE",
  "CHECK_CUSTOMER_REGISTRATION",
  "GET_CREDIT_PROFILE",
  "FIND_ELIGIBLE_PRODUCTS",
  "SIMULATE_WORKING_CAPITAL",
  "PRESENT_OPTIONS",
];

it("shows working-capital context, partial plan and explainable capabilities", () => {
  const intentContract = {
    schemaVersion: "1.0",
    intent: "SEEK_WORKING_CAPITAL",
    domain: "CREDIT",
    objective: "ASSESS_WORKING_CAPITAL_OPTIONS",
    entities: {
      purpose: "INVENTORY",
      amount: "50000",
      businessSituation: "SALES_GROWTH",
    },
    constraints: { mutationAllowed: false, readOnly: true, confirmationRequired: true },
    provenance: { source: "NATURAL_LANGUAGE", sourceRef: "context-ai:ctxi-working" },
    confidence: 0.94,
  };
  const steps = capabilityIds.map((capabilityId, index) => ({
    stepId: `working-${index + 1}`,
    sequence: index + 1,
    capabilityId,
    required: true,
  }));
  const capabilities = steps.map((step, index) => ({
    stepId: step.stepId,
    capabilityId: step.capabilityId,
    description: `Descrição de ${step.capabilityId}`,
    reason: `Necessária no passo ${index + 1}`,
    inputContract: `spider-capability://input/${step.capabilityId}/v1`,
    outputContract: `spider-capability://output/${step.capabilityId}/v1`,
    availability: index === 0 ? "AVAILABLE" : "NOT_AVAILABLE",
    status: index === 0 ? "RESOLVED" : "UNAVAILABLE",
    selectedRoute:
      index === 0
        ? {
            routeRef: "AUTHENTICATED_CONTEXT_CUSTOMER_V1",
            adapterRef: "context-principal",
            targetOperation: "IDENTIFY_CUSTOMER",
          }
        : null,
  }));

  render(
    <ContextIntelligence
      catalog={{
        contextEnabled: true,
        uiEnabled: true,
        aiEnabled: true,
        aiState: "ACTIVE",
        items: [],
      }}
      preview={{
        decisionId: "ctxd-working",
        decision: "ACCEPTED",
        policyRef: "context:read-only@1.0",
        requestedObjective: "Preciso de R$ 50 mil para reforçar meu estoque.",
        intentContract,
        interpretation: { missingContext: [], candidateIntents: [] },
        executionPlan: {
          schemaVersion: "1.0",
          planId: "ctxp-working",
          planType: "WORKING_CAPITAL_DIAGNOSTIC_V1",
          intent: "SEEK_WORKING_CAPITAL",
          steps,
          status: "PARTIALLY_AVAILABLE",
          statusReasons: capabilityIds
            .slice(1)
            .map((id) => `CAPABILITY_NOT_AVAILABLE:${id}`),
        },
        capabilities,
        route: null,
      }}
      onInterpret={vi.fn()}
      onInterpretText={vi.fn()}
      onExecute={vi.fn()}
    />,
  );

  const panel = screen.getByTestId("intent-preview");
  expect(panel).toHaveTextContent("SEEK_WORKING_CAPITAL");
  expect(panel).toHaveTextContent("ESTOQUE");
  expect(panel).toHaveTextContent("R$ 50.000,00");
  expect(panel).toHaveTextContent("CONSULTA / SIMULAÇÃO");
  expect(panel).toHaveTextContent("WORKING_CAPITAL_DIAGNOSTIC_V1");
  expect(panel).toHaveTextContent("PARCIALMENTE DISPONÍVEL");
  expect(screen.getByTestId("context-capabilities").querySelectorAll("li")).toHaveLength(7);
  expect(screen.queryByRole("button", { name: "Executar" })).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /IDENTIFY_CUSTOMER/ }));
  const detail = screen.getByTestId("context-capability-detail");
  expect(detail).toHaveTextContent("Necessária no passo 1");
  expect(detail).toHaveTextContent("AUTHENTICATED_CONTEXT_CUSTOMER_V1");
  expect(detail).toHaveTextContent("context-principal");
});
