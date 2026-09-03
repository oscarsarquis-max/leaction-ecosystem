import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ContextIntelligence from "./ContextIntelligence";

const contract = {
  schemaVersion: "1.0",
  intent: "INVESTIGATE_CREDIT_RELEASE",
  domain: "CREDIT",
  objective: "IDENTIFY_BLOCKING_CONDITION",
  entities: { proposalId: "DEMO-PROPOSAL-001" },
  constraints: {
    mutationAllowed: false,
    readOnly: true,
    confirmationRequired: true,
  },
  provenance: { source: "BUSINESS_CARD" },
  confidence: 1,
};

const catalog = {
  contextEnabled: true,
  uiEnabled: true,
  aiEnabled: false,
  items: [
    {
      domain: "CREDIT",
      domainLabel: "Crédito",
      intent: contract.intent,
      title: "Investigar liberação de proposta",
      description: "Entender por que uma proposta de crédito não foi liberada.",
      intentContract: contract,
    },
  ],
};

const executionPlan = {
  schemaVersion: "1.0",
  planId: "ctxp-credit",
  planType: "CREDIT_RELEASE_INVESTIGATION_PLAN_V1",
  intent: contract.intent,
  status: "READY",
  statusReasons: [],
  steps: [{ stepId: "credit-01", sequence: 1, capabilityId: "CREDIT_RELEASE_DIAGNOSTIC" }],
};

const capability = {
  stepId: "credit-01",
  capabilityId: "CREDIT_RELEASE_DIAGNOSTIC",
  description: "Investigar a condição que impede a liberação.",
  reason: "Identificar a condição bloqueadora.",
  inputContract: "spider-capability://input/credit/v1",
  outputContract: "spider-capability://output/credit/v1",
  availability: "AVAILABLE",
  status: "RESOLVED",
  selectedRoute: {
    routeRef: "CREDIT_RELEASE_DIAGNOSTIC_V1",
    adapterRef: "mock-universal",
    targetOperation: "RETRY_THEN_SUCCESS",
  },
};

describe("ContextIntelligence", () => {
  it("renders no Context surface when its UI flag is off", () => {
    const { container } = render(
      <ContextIntelligence
        catalog={{ ...catalog, uiEnabled: false }}
        onInterpret={vi.fn()}
        onExecute={vi.fn()}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("presents deterministic business cards and keeps natural language disabled", () => {
    const onInterpret = vi.fn();
    render(
      <ContextIntelligence
        catalog={catalog}
        onInterpret={onInterpret}
        onExecute={vi.fn()}
      />,
    );

    expect(screen.getByText("IA CONTEXTUAL — DESABILITADA")).toBeInTheDocument();
    expect(screen.getByLabelText("Interpretação em linguagem natural")).toBeDisabled();
    expect(screen.getByPlaceholderText("Descreva uma situação ou objetivo...")).toBeDisabled();
    expect(
      screen.getByText(/As situações frequentes continuam operacionais/),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Investigar" }));
    expect(onInterpret).toHaveBeenCalledWith(catalog.items[0]);
  });

  it("separates preview from execution and exposes no endpoint", () => {
    const onExecute = vi.fn();
    const preview = {
      decisionId: "ctxd-1",
      decision: "ACCEPTED",
      intentContract: contract,
      executionPlan,
      capabilities: [capability],
      route: {
        capabilityRef: "CREDIT_RELEASE_DIAGNOSTIC",
        routeRef: "CREDIT_RELEASE_DIAGNOSTIC_V1",
        executable: true,
      },
      policyRef: "context:read-only@1.0",
    };
    render(
      <ContextIntelligence
        catalog={catalog}
        preview={preview}
        onInterpret={vi.fn()}
        onExecute={onExecute}
      />,
    );

    const panel = screen.getByTestId("intent-preview");
    expect(panel).toHaveTextContent("SPIDER ENTENDEU");
    expect(panel).toHaveTextContent("Entender por que uma proposta de crédito não foi liberada.");
    expect(panel).toHaveTextContent("INVESTIGATE_CREDIT_RELEASE");
    expect(panel).toHaveTextContent("Crédito");
    expect(panel).toHaveTextContent("BUSINESS_CARD");
    expect(panel).toHaveTextContent("100%");
    expect(panel).toHaveTextContent("SOMENTE CONSULTA");
    expect(panel).toHaveTextContent("ACCEPTED · context:read-only@1.0");
    expect(panel).toHaveTextContent("CREDIT_RELEASE_INVESTIGATION_PLAN_V1");
    fireEvent.click(screen.getByRole("button", { name: /CREDIT_RELEASE_DIAGNOSTIC/ }));
    expect(panel).toHaveTextContent("CREDIT_RELEASE_DIAGNOSTIC_V1");
    expect(panel).toHaveTextContent("Intent válido");
    expect(panel).toHaveTextContent("Política aceita");
    expect(panel).toHaveTextContent("Plano determinado");
    expect(
      screen.getByLabelText("Fases da jornada do objetivo"),
    ).toBeInTheDocument();
    expect(panel).not.toHaveTextContent("/v1/");
    expect(onExecute).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Executar" }));
    expect(onExecute).toHaveBeenCalledWith(preview);
  });

  it("shows the same understanding pattern without pretending execution for preview-only cards", () => {
    render(
      <ContextIntelligence
        catalog={catalog}
        preview={{
          decisionId: "ctxd-preview",
          decision: "ACCEPTED",
          policyRef: "context:read-only@1.0",
          intentContract: {
            ...contract,
            intent: "INVESTIGATE_COLLECTION_PENDING",
            domain: "COLLECTION",
            objective: "IDENTIFY_PENDING_COLLECTION_CONDITION",
          },
          executionPlan: {
            ...executionPlan,
            planId: "ctxp-collection",
            planType: "COLLECTION_INVESTIGATION_PLAN_V1",
            intent: "INVESTIGATE_COLLECTION_PENDING",
            status: "NOT_EXECUTABLE",
            statusReasons: ["CAPABILITY_NOT_AVAILABLE:COLLECTION_DIAGNOSTIC"],
            steps: [
              {
                stepId: "collection-01",
                sequence: 1,
                capabilityId: "COLLECTION_DIAGNOSTIC",
              },
            ],
          },
          capabilities: [
            {
              ...capability,
              stepId: "collection-01",
              capabilityId: "COLLECTION_DIAGNOSTIC",
              availability: "NOT_AVAILABLE",
              status: "UNAVAILABLE",
              selectedRoute: {
                ...capability.selectedRoute,
                routeRef: "COLLECTION_DIAGNOSTIC_V1",
              },
            },
          ],
          route: {
            capabilityRef: "COLLECTION_DIAGNOSTIC",
            routeRef: "COLLECTION_DIAGNOSTIC_V1",
            executable: false,
          },
        }}
        onInterpret={vi.fn()}
        onExecute={vi.fn()}
      />,
    );

    const panel = screen.getByTestId("intent-preview");
    expect(panel).toHaveTextContent("INVESTIGATE_COLLECTION_PENDING");
    fireEvent.click(screen.getByRole("button", { name: /COLLECTION_DIAGNOSTIC/ }));
    expect(panel).toHaveTextContent("COLLECTION_DIAGNOSTIC_V1");
    expect(panel).toHaveTextContent("Plano não executável neste boundary");
    expect(screen.queryByRole("button", { name: "Executar" })).not.toBeInTheDocument();
  });

  it("enables the objective field only when contextual AI is active", () => {
    const onInterpretText = vi.fn();
    render(
      <ContextIntelligence
        catalog={{ ...catalog, aiEnabled: true, aiState: "ACTIVE" }}
        onInterpret={vi.fn()}
        onInterpretText={onInterpretText}
        onExecute={vi.fn()}
      />,
    );

    const field = screen.getByLabelText("Interpretação em linguagem natural");
    expect(field).toBeEnabled();
    fireEvent.change(field, {
      target: { value: "Verifique a proposta 12345 porque ainda não liberou." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Interpretar" }));
    expect(onInterpretText).toHaveBeenCalledWith(
      "Verifique a proposta 12345 porque ainda não liberou.",
    );
  });

  it("reuses Spider Entendeu for a valid natural-language contract", () => {
    const naturalContract = {
      ...contract,
      entities: { proposalId: "12345" },
      provenance: { source: "NATURAL_LANGUAGE", sourceRef: "context-ai:ctxi-1" },
      confidence: 0.94,
    };
    render(
      <ContextIntelligence
        catalog={{ ...catalog, aiEnabled: true, aiState: "ACTIVE" }}
        preview={{
          decisionId: "ctxd-ai",
          decision: "ACCEPTED",
          policyRef: "context:read-only@1.0",
          intentContract: naturalContract,
          requestedObjective: "Verifique a proposta 12345 porque ainda não liberou.",
          interpretationStatus: "SUCCEEDED",
          interpretationMessage: "Objetivo interpretado.",
          interpretation: {
            interpretationId: "ctxi-1",
            missingContext: [],
            candidateIntents: [],
          },
          executionPlan,
          capabilities: [capability],
          route: {
            capabilityRef: "CREDIT_RELEASE_DIAGNOSTIC",
            routeRef: "CREDIT_RELEASE_DIAGNOSTIC_V1",
            executable: true,
          },
        }}
        onInterpret={vi.fn()}
        onInterpretText={vi.fn()}
        onExecute={vi.fn()}
      />,
    );

    const panel = screen.getByTestId("intent-preview");
    expect(panel).toHaveTextContent("Você pediu");
    expect(panel).toHaveTextContent("NATURAL_LANGUAGE");
    expect(panel).toHaveTextContent("94%");
    expect(panel).toHaveTextContent("Contexto suficiente");
    expect(
      screen.getByLabelText("Fases da jornada do objetivo"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Executar" })).toBeEnabled();
  });

  it("shows missing context and ambiguity without exposing execution", () => {
    const { rerender } = render(
      <ContextIntelligence
        catalog={{ ...catalog, aiEnabled: true, aiState: "ACTIVE" }}
        preview={{
          decisionId: "ctxd-missing",
          decision: "MISSING_CONTEXT",
          policyRef: "context:read-only@1.0",
          intentContract: {
            ...contract,
            entities: {},
            provenance: { source: "NATURAL_LANGUAGE" },
            confidence: 0.94,
          },
          requestedObjective: "Minha proposta ainda não foi liberada.",
          interpretationStatus: "MISSING_CONTEXT",
          interpretationMessage: "Falta uma informação para continuar com segurança.",
          interpretation: { missingContext: ["proposalId"], candidateIntents: [] },
          route: null,
        }}
        onInterpret={vi.fn()}
        onInterpretText={vi.fn()}
        onExecute={vi.fn()}
      />,
    );

    expect(screen.getByTestId("missing-context")).toHaveTextContent(
      "Qual é o número da proposta?",
    );
    expect(screen.queryByRole("button", { name: "Executar" })).not.toBeInTheDocument();

    rerender(
      <ContextIntelligence
        catalog={{ ...catalog, aiEnabled: true, aiState: "ACTIVE" }}
        preview={{
          decisionId: "ctxi-ambiguous",
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
    expect(screen.getByTestId("interpretation-blocked")).toHaveTextContent(
      "Preciso entender melhor o objetivo",
    );
    expect(screen.getByTestId("interpretation-blocked")).toHaveTextContent(
      "Investigar liberação de proposta",
    );
    expect(screen.queryByRole("button", { name: "Executar" })).not.toBeInTheDocument();
  });
});
