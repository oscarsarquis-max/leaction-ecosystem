package br.com.banco.spider.context.application;

import br.com.banco.spider.context.contract.IntentContract;
import br.com.banco.spider.context.domain.ContextPolicyGuard;
import br.com.banco.spider.context.domain.IntentRouteResolution;
import java.time.Instant;
import java.util.List;

public record ContextDecisionRecord(
    String decisionId,
    String principalRef,
    IntentContract intentContract,
    ContextPolicyGuard.GuardResult guard,
    IntentRouteResolution route,
    Instant createdAt,
    String executionId,
    String executionState,
    Instant executedAt,
    ContextInterpretationEvidence interpretation,
    List<ContextJourneyStage> journey) {

  public ContextDecisionRecord {
    journey = journey == null ? List.of() : List.copyOf(journey);
  }

  public ContextDecisionRecord withExecution(
      String nextExecutionId, String nextExecutionState, Instant nextExecutedAt) {
    return new ContextDecisionRecord(
        decisionId,
        principalRef,
        intentContract,
        guard,
        route,
        createdAt,
        nextExecutionId,
        nextExecutionState,
        nextExecutedAt,
        interpretation,
        journey);
  }
}
