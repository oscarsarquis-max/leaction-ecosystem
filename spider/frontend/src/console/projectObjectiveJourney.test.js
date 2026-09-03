import { describe, expect, it } from "vitest";
import {
  OBJECTIVE_JOURNEY_PHASE_IDS,
  projectCapabilityVisual,
  projectObjectiveJourney,
} from "./projectObjectiveJourney";

const capabilityIds = [
  "IDENTIFY_CUSTOMER",
  "GET_CUSTOMER_PROFILE",
  "CHECK_CUSTOMER_REGISTRATION",
  "GET_CREDIT_PROFILE",
  "FIND_ELIGIBLE_PRODUCTS",
  "SIMULATE_WORKING_CAPITAL",
  "PRESENT_OPTIONS",
];

function workingCapitalPreview(purpose = "INVENTORY", extra = {}) {
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
    requestedObjective: extra.requestedObjective || "Preciso de R$ 50 mil para reforçar meu estoque.",
    intentContract: {
      intent: "SEEK_WORKING_CAPITAL",
      domain: "CREDIT",
      objective: "ASSESS_WORKING_CAPITAL_OPTIONS",
      entities: {
        purpose,
        ...(extra.amount ? { amount: extra.amount } : purpose === "INVENTORY" ? { amount: "50000" } : {}),
        businessSituation: extra.businessSituation || "SALES_GROWTH",
      },
      constraints: { mutationAllowed: false, readOnly: true, confirmationRequired: true },
      provenance: { source: "NATURAL_LANGUAGE", sourceRef: "context-ai:ctxi-working" },
      confidence: 0.94,
    },
    interpretation: {
      missingContext: [],
      candidateIntents: [],
      provider: "scripted-evidence",
      model: "scripted-working-capital",
      interpretedAt: "2026-09-03T18:00:00Z",
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
    ...extra.preview,
  };
}

describe("projectObjectiveJourney", () => {
  it("projects the eight real phases for working capital without inventing execution", () => {
    const projection = projectObjectiveJourney({ preview: workingCapitalPreview() });
    expect(projection.phases.map((item) => item.id)).toEqual(OBJECTIVE_JOURNEY_PHASE_IDS);
    expect(projection.intent).toBe("SEEK_WORKING_CAPITAL");
    expect(projection.plan.planType).toBe("WORKING_CAPITAL_DIAGNOSTIC_V1");
    expect(projection.usedAi).toBe(true);
    expect(projection.capabilities).toHaveLength(7);
    expect(projection.capabilities[0].visual.kind).toBe("available");
    expect(projection.capabilities[1].visual.kind).toBe("required");
    expect(projection.executedCount).toBe(0);
    expect(projection.result.status).toBe("PARTIAL");
    expect(projection.result.conclusion).toBe("PLANO PARCIALMENTE DISPONÍVEL");
    expect(projection.capabilities[1].resolution.routeRef).toBe("NO_ELIGIBLE_ROUTE");
    expect(projection.capabilities[1].resolution.target).toBe("NOT_AVAILABLE");
    expect(projection.executionId).toBeNull();
  });

  it("keeps the same intent family while preserving distinct economic context", () => {
    expect(
      projectObjectiveJourney({
        preview: workingCapitalPreview("CASH_FLOW", {
          requestedObjective: "Preciso reforçar meu caixa.",
          amount: undefined,
        }),
      }).contract.entities.purpose,
    ).toBe("CASH_FLOW");
    expect(
      projectObjectiveJourney({
        preview: workingCapitalPreview("RAW_MATERIAL", {
          requestedObjective: "Preciso comprar matéria-prima para novos pedidos.",
        }),
      }).contract.entities.purpose,
    ).toBe("RAW_MATERIAL");
    expect(
      projectObjectiveJourney({
        preview: workingCapitalPreview("SEASONALITY", {
          requestedObjective: "Preciso antecipar estoque para a sazonalidade.",
        }),
      }).contract.entities.purpose,
    ).toBe("SEASONALITY");
  });

  it("interrupts missing context and ambiguity without starting plan or execution", () => {
    const missing = projectObjectiveJourney({
      preview: {
        decisionId: "ctxd-missing",
        decision: "MISSING_CONTEXT",
        policyRef: "context:read-only@1.0",
        requestedObjective: "Minha proposta ainda não foi liberada.",
        interpretationStatus: "MISSING_CONTEXT",
        intentContract: {
          intent: "INVESTIGATE_CREDIT_RELEASE",
          domain: "CREDIT",
          provenance: { source: "NATURAL_LANGUAGE" },
          constraints: { mutationAllowed: false },
          entities: {},
          confidence: 0.94,
        },
        interpretation: { missingContext: ["proposalId"], candidateIntents: [] },
      },
    });
    expect(missing.phases.find((item) => item.id === "objective").status).toBe("SUCCEEDED");
    expect(missing.phases.find((item) => item.id === "understanding").status).toBe("SUCCEEDED");
    expect(missing.phases.find((item) => item.id === "policy").status).toBe("MISSING_CONTEXT");
    expect(missing.phases.find((item) => item.id === "plan").status).toBe("NOT_STARTED");
    expect(missing.phases.find((item) => item.id === "capabilities").status).toBe("NOT_STARTED");
    expect(missing.phases.find((item) => item.id === "resolution").status).toBe("NOT_STARTED");
    expect(missing.phases.find((item) => item.id === "execution").status).toBe("NOT_STARTED");
    expect(missing.result.status).toBe("NEEDS_INFORMATION");

    const ambiguous = projectObjectiveJourney({
      preview: {
        decision: "AMBIGUOUS",
        requestedObjective: "Quero saber o que aconteceu com o cliente João.",
        interpretationStatus: "AMBIGUOUS",
        interpretation: {
          missingContext: [],
          candidateIntents: ["INVESTIGATE_CREDIT_RELEASE"],
        },
      },
    });
    expect(ambiguous.phases.find((item) => item.id === "understanding").status).toBe("AMBIGUOUS");
    expect(ambiguous.phases.find((item) => item.id === "plan").status).toBe("NOT_STARTED");
    expect(ambiguous.usedAi).toBe(true);
  });

  it("does not pretend AI for BUSINESS_CARD and only marks executed capabilities with evidence", () => {
    const card = projectObjectiveJourney({
      preview: {
        decisionId: "ctxd-card",
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
          planId: "ctxp-credit",
          planType: "CREDIT_RELEASE_INVESTIGATION_PLAN_V1",
          schemaVersion: "1.0",
          status: "READY",
          steps: [{ stepId: "credit-01", capabilityId: "CREDIT_RELEASE_DIAGNOSTIC", required: true }],
        },
        capabilities: [
          {
            stepId: "credit-01",
            capabilityId: "CREDIT_RELEASE_DIAGNOSTIC",
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
      },
    });
    expect(card.usedAi).toBe(false);
    expect(card.capabilities[0].visual.kind).toBe("available");

    const executed = projectObjectiveJourney({
      preview: {
        ...card.contract && {},
        decisionId: "ctxd-card",
        decision: "ACCEPTED",
        intentContract: card.contract,
        executionPlan: card.plan,
        capabilities: card.capabilities,
        route: {
          capabilityRef: "CREDIT_RELEASE_DIAGNOSTIC",
          routeRef: "CREDIT_RELEASE_DIAGNOSTIC_V1",
          executable: true,
        },
        executionId: "exec-credit-1",
        executionState: "SUCCEEDED",
      },
      executionEvidence: {
        executionId: "exec-credit-1",
        executionState: "SUCCEEDED",
        durationMs: 1200,
        outcome: "SUCCESS",
      },
    });
    expect(executed.capabilities[0].visual.kind).toBe("executed");
    expect(executed.result.status).toBe("SUCCEEDED");
  });

  it("never uses a green check merely because the capability is on the plan", () => {
    const visual = projectCapabilityVisual(
      { capabilityId: "GET_CREDIT_PROFILE", status: "UNAVAILABLE", availability: "NOT_AVAILABLE" },
      new Set(),
    );
    expect(visual.marker).toBe("○");
    expect(visual.kind).toBe("required");
  });
});
