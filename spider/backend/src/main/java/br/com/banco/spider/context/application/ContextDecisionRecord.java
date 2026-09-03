package br.com.banco.spider.context.application;

import br.com.banco.spider.context.contract.IntentContract;
import br.com.banco.spider.context.capability.CapabilityResolution;
import br.com.banco.spider.context.domain.ContextPolicyGuard;
import br.com.banco.spider.context.domain.IntentRouteResolution;
import br.com.banco.spider.context.planning.ContextExecutionPlan;
import java.time.Instant;
import java.util.List;

public record ContextDecisionRecord(
    String decisionId,
    String principalRef,
    IntentContract intentContract,
    ContextPolicyGuard.GuardResult guard,
    ContextExecutionPlan executionPlan,
    List<CapabilityResolution> capabilities,
    IntentRouteResolution route,
    Instant createdAt,
    String executionId,
    String executionState,
    Instant executedAt,
    ContextInterpretationEvidence interpretation,
    List<ContextJourneyStage> journey) {

  public ContextDecisionRecord {
    capabilities = capabilities == null ? List.of() : List.copyOf(capabilities);
    journey = journey == null ? List.of() : List.copyOf(journey);
  }

  public ContextDecisionRecord withExecution(
      String nextExecutionId, String nextExecutionState, Instant nextExecutedAt) {
    return new ContextDecisionRecord(
        decisionId,
        principalRef,
        intentContract,
        guard,
        executionPlan,
        capabilities,
        route,
        createdAt,
        nextExecutionId,
        nextExecutionState,
        nextExecutedAt,
        interpretation,
        journey);
  }
}
