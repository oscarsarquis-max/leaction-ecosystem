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

    expect(screen.getByText("IA — próxima etapa")).toBeInTheDocument();
    expect(screen.getByLabelText("Interpretação em linguagem natural")).toBeDisabled();
    expect(screen.getByPlaceholderText("Descreva uma situação ou objetivo...")).toBeDisabled();
    expect(screen.getByText(/O Spider transforma o objetivo em uma intenção estruturada/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Investigar" }));
    expect(onInterpret).toHaveBeenCalledWith(catalog.items[0]);
  });

  it("separates preview from execution and exposes no endpoint", () => {
    const onExecute = vi.fn();
    const preview = {
      decisionId: "ctxd-1",
      decision: "ACCEPTED",
      intentContract: contract,
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
    expect(panel).toHaveTextContent("CREDIT_RELEASE_DIAGNOSTIC_V1");
    expect(panel).toHaveTextContent("Intent válido");
    expect(panel).toHaveTextContent("Política aceita");
    expect(panel).toHaveTextContent("Rota determinada");
    expect(screen.getByLabelText("Objetivo, Intent, Policy, Rota, Executar e Jornada")).toBeInTheDocument();
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
    expect(panel).toHaveTextContent("COLLECTION_DIAGNOSTIC_V1");
    expect(panel).toHaveTextContent("Preview disponível · execução ainda não habilitada");
    expect(screen.queryByRole("button", { name: "Executar" })).not.toBeInTheDocument();
  });
});
