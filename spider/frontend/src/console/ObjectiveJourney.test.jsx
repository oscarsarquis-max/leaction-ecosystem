import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
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

const catalog = {
  contextEnabled: true,
  uiEnabled: true,
  aiEnabled: true,
  aiState: "ACTIVE",
  items: [
    {
      domain: "CREDIT",
      domainLabel: "Crédito",
      intent: "INVESTIGATE_CREDIT_RELEASE",
      title: "Investigar liberação de proposta",
      description: "Entender por que uma proposta de crédito não foi liberada.",
    },
  ],
};

function workingPreview() {
  const steps = capabilityIds.map((capabilityId, index) => ({
    stepId: `working-${index + 1}`,
    sequence: index + 1,
    capabilityId,
    required: true,
  }));
  return {
    decisionId: "ctxd-working",
    decision: "ACCEPTED",
    policyRef: "context:read-only@1.0",
    createdAt: "2026-09-03T18:00:00Z",
    requestedObjective: "Preciso de R$ 50 mil para reforçar meu estoque.",
    intentContract: {
      intent: "SEEK_WORKING_CAPITAL",
      domain: "CREDIT",
      objective: "ASSESS_WORKING_CAPITAL_OPTIONS",
      entities: { purpose: "INVENTORY", amount: "50000", businessSituation: "SALES_GROWTH" },
      constraints: { mutationAllowed: false, readOnly: true, confirmationRequired: true },
      provenance: { source: "NATURAL_LANGUAGE", sourceRef: "context-ai:ctxi-working" },
      confidence: 0.94,
    },
    interpretation: {
      missingContext: [],
      candidateIntents: [],
      provider: "scripted-evidence",
      model: "scripted-working-capital",
    },
    executionPlan: {
      schemaVersion: "1.0",
      planId: "ctxp-working",
      planType: "WORKING_CAPITAL_DIAGNOSTIC_V1",
      intent: "SEEK_WORKING_CAPITAL",
      steps,
      status: "PARTIALLY_AVAILABLE",
      statusReasons: capabilityIds.slice(1).map((id) => `CAPABILITY_NOT_AVAILABLE:${id}`),
    },
    capabilities: steps.map((step, index) => ({
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
    })),
    route: null,
  };
}

function renderHome(preview, extra = {}) {
  return render(
    <ContextIntelligence
      catalog={catalog}
      preview={preview}
      onInterpret={vi.fn()}
      onInterpretText={vi.fn()}
      onExecute={vi.fn()}
      onRevealDataPlane={extra.onRevealDataPlane}
      executionEvidence={extra.executionEvidence}
      operationalEvents={extra.operationalEvents}
    />,
  );
}

describe("ObjectiveJourney on Home", () => {
  it("renders clickable phases for the principal working-capital objective", () => {
    renderHome(workingPreview());
    const journey = screen.getByTestId("objective-journey");
    expect(journey).toHaveTextContent("Jornada do objetivo");
    [
      "objective",
      "understanding",
      "policy",
      "plan",
      "capabilities",
      "resolution",
      "execution",
      "result",
    ].forEach((id) => {
      expect(screen.getByTestId(`objective-phase-${id}`)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("objective-phase-objective").querySelector("button"));
    expect(screen.getByTestId("objective-journey-detail")).toHaveTextContent(
      "Preciso de R$ 50 mil para reforçar meu estoque.",
    );
    expect(screen.getByTestId("objective-journey-detail")).toHaveTextContent("NATURAL_LANGUAGE");
    expect(screen.getByTestId("objective-journey-detail")).toHaveTextContent("R$ 50.000,00");

    fireEvent.click(screen.getByTestId("objective-phase-understanding").querySelector("button"));
    const understanding = screen.getByTestId("objective-journey-detail");
    expect(understanding).toHaveTextContent("SEEK_WORKING_CAPITAL");
    expect(understanding).toHaveTextContent("ESTOQUE");
    expect(understanding).toHaveTextContent("scripted-evidence");
    expect(understanding).not.toHaveTextContent("chain-of-thought");

    fireEvent.click(screen.getByTestId("objective-phase-policy").querySelector("button"));
    expect(screen.getByTestId("objective-journey-detail")).toHaveTextContent("ACCEPTED");
    expect(screen.getByTestId("objective-journey-detail")).toHaveTextContent("NOT_ALLOWED");

    fireEvent.click(screen.getByTestId("objective-phase-plan").querySelector("button"));
    expect(screen.getByTestId("context-execution-plan")).toHaveTextContent(
      "WORKING_CAPITAL_DIAGNOSTIC_V1",
    );
    expect(screen.getByTestId("objective-journey-detail")).toHaveTextContent("ctxp-working");
    expect(screen.getByTestId("objective-journey-detail")).toHaveTextContent("1.0");
  });

  it("separates necessary, available and executed capability states", () => {
    renderHome(workingPreview());
    const capabilities = screen.getByTestId("context-capabilities");
    expect(capabilities.querySelectorAll("li")).toHaveLength(7);
    expect(capabilities.querySelector('[data-visual="available"]')).toHaveTextContent(
      "IDENTIFY_CUSTOMER",
    );
    expect(capabilities.querySelector('[data-visual="available"]')).toHaveTextContent("◉");
    expect(capabilities.querySelector('[data-visual="executed"]')).toBeNull();
    expect(capabilities.querySelectorAll('[data-visual="required"]')).toHaveLength(6);
    expect(screen.queryByRole("button", { name: "Executar" })).not.toBeInTheDocument();
  });

  it("opens capability detail with real route or explicit unavailability", () => {
    renderHome(workingPreview());
    fireEvent.click(screen.getByRole("button", { name: /IDENTIFY_CUSTOMER/ }));
    const available = screen.getByTestId("context-capability-detail");
    expect(available).toHaveTextContent("AUTHENTICATED_CONTEXT_CUSTOMER_V1");
    expect(available).toHaveTextContent("context-principal");
    expect(available).toHaveTextContent("NOT_EXECUTED");
    expect(available).not.toHaveTextContent("IA interpretou");

    fireEvent.click(screen.getByRole("button", { name: /GET_CREDIT_PROFILE/ }));
    const unavailable = screen.getByTestId("context-capability-detail");
    expect(unavailable).toHaveTextContent("NO_ELIGIBLE_ROUTE");
    expect(unavailable).toHaveTextContent("NOT_AVAILABLE");
    expect(unavailable).toHaveTextContent("NECESSÁRIA");
  });

  it("derives the executor table and partial result from the resolver", () => {
    renderHome(workingPreview());
    fireEvent.click(screen.getByTestId("objective-phase-resolution").querySelector("button"));
    const table = screen.getByTestId("objective-resolution-table");
    expect(table).toHaveTextContent("IDENTIFY_CUSTOMER");
    expect(table).toHaveTextContent("context-principal");
    expect(table).toHaveTextContent("GET_CREDIT_PROFILE");
    expect(table).toHaveTextContent("Não disponível");
    expect(screen.getByTestId("objective-no-ai")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("objective-phase-result").querySelector("button"));
    const result = screen.getByTestId("objective-result");
    expect(result).toHaveTextContent("PLANO PARCIALMENTE DISPONÍVEL");
    expect(result).toHaveTextContent("compreender o objetivo");
    expect(result).toHaveTextContent("Consultar perfil de crédito");
    expect(result).not.toHaveTextContent("Response Composer");
  });

  it("navigates to Data Plane only for a capability that was actually executed", () => {
    const onRevealDataPlane = vi.fn();
    const preview = {
      decisionId: "ctxd-credit",
      decision: "ACCEPTED",
      policyRef: "context:read-only@1.0",
      intentContract: {
        intent: "INVESTIGATE_CREDIT_RELEASE",
        domain: "CREDIT",
        provenance: { source: "BUSINESS_CARD" },
        constraints: { mutationAllowed: false, readOnly: true },
        confidence: 1,
      },
      executionPlan: {
        schemaVersion: "1.0",
        planId: "ctxp-credit",
        planType: "CREDIT_RELEASE_INVESTIGATION_PLAN_V1",
        status: "READY",
        steps: [{ stepId: "credit-01", capabilityId: "CREDIT_RELEASE_DIAGNOSTIC", required: true }],
      },
      capabilities: [
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
      ],
      route: {
        capabilityRef: "CREDIT_RELEASE_DIAGNOSTIC",
        routeRef: "CREDIT_RELEASE_DIAGNOSTIC_V1",
        executable: true,
      },
      executionId: "exec-credit-1",
      executionState: "SUCCEEDED",
    };
    renderHome(preview, {
      onRevealDataPlane,
      executionEvidence: {
        executionId: "exec-credit-1",
        executionState: "SUCCEEDED",
        durationMs: 1500,
        outcome: "SUCCESS",
      },
    });
    expect(screen.getByTestId("context-capabilities").querySelector('[data-visual="executed"]'))
      .toHaveTextContent("CREDIT_RELEASE_DIAGNOSTIC");
    fireEvent.click(screen.getByTestId("objective-phase-understanding").querySelector("button"));
    expect(screen.getByTestId("objective-journey-detail")).not.toHaveTextContent(
      "A IA interpretou a linguagem natural",
    );
    fireEvent.click(screen.getByRole("button", { name: /CREDIT_RELEASE_DIAGNOSTIC/ }));
    fireEvent.click(screen.getByRole("button", { name: "Ver Data Plane Journey" }));
    expect(onRevealDataPlane).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByTestId("objective-phase-result").querySelector("button"));
    expect(screen.getByTestId("objective-result")).toHaveTextContent("SUCCEEDED");
    expect(screen.getByTestId("objective-result")).toHaveTextContent("executar 1 capability");
  });

  it("shows missing context and ambiguity interruptions", () => {
    const { rerender } = renderHome({
      decisionId: "ctxd-missing",
      decision: "MISSING_CONTEXT",
      policyRef: "context:read-only@1.0",
      requestedObjective: "Minha proposta ainda não foi liberada.",
      interpretationStatus: "MISSING_CONTEXT",
      interpretationMessage: "Falta uma informação para continuar com segurança.",
      intentContract: {
        intent: "INVESTIGATE_CREDIT_RELEASE",
        domain: "CREDIT",
        provenance: { source: "NATURAL_LANGUAGE" },
        constraints: { mutationAllowed: false },
        entities: {},
        confidence: 0.94,
      },
      interpretation: { missingContext: ["proposalId"], candidateIntents: [] },
    });
    expect(screen.getByTestId("objective-phase-policy")).toHaveAttribute(
      "data-state",
      "MISSING_CONTEXT",
    );
    expect(screen.getByTestId("objective-phase-plan")).toHaveAttribute("data-state", "NOT_STARTED");
    expect(screen.getByTestId("missing-context")).toHaveTextContent("Qual é o número da proposta?");
    fireEvent.click(screen.getByTestId("objective-phase-result").querySelector("button"));
    expect(screen.getByTestId("objective-result")).toHaveTextContent("PRECISA DE INFORMAÇÃO");

    rerender(
      <ContextIntelligence
        catalog={catalog}
        preview={{
          decision: "AMBIGUOUS",
          requestedObjective: "Quero saber o que aconteceu com o cliente João.",
          interpretationStatus: "AMBIGUOUS",
          interpretationMessage: "Preciso entender melhor o objetivo.",
          interpretation: {
            missingContext: [],
            candidateIntents: ["INVESTIGATE_CREDIT_RELEASE"],
          },
        }}
        onInterpret={vi.fn()}
        onInterpretText={vi.fn()}
        onExecute={vi.fn()}
      />,
    );
    expect(screen.getByTestId("objective-phase-understanding")).toHaveAttribute(
      "data-state",
      "AMBIGUOUS",
    );
    expect(screen.getByTestId("objective-phase-plan")).toHaveAttribute("data-state", "NOT_STARTED");
    expect(screen.getByTestId("interpretation-blocked")).toHaveTextContent(
      "Investigar liberação de proposta",
    );
    expect(screen.queryByTestId("context-capabilities")).not.toBeInTheDocument();
  });
});
