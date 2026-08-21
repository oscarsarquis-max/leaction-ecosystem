package br.com.banco.spider.operational.readmodel;

import java.util.List;
import java.util.Map;

public record OperationalExecutionDetail(
    OperationalExecutionListItem summary,
    OperationalSection<PlanView> plan,
    OperationalSection<List<StepView>> steps,
    OperationalSection<List<OperationalTimelineEvent>> timeline,
    OperationalSection<WaitView> waitInfo,
    OperationalSection<SignalView> signal,
    OperationalSection<CallbackView> callback,
    OperationalSection<ReconciliationView> reconciliation,
    OperationalSection<GovernanceView> governance,
    OperationalSection<SecurityPostureView> securityPosture,
    OperationalSection<Map<String, Object>> safeRequestProjection,
    OperationalSection<Map<String, Object>> safeResultProjection) {

  public record PlanView(
      String planId,
      String routeRef,
      List<String> orderedSteps,
      String mappingKind,
      String retryPolicyRef,
      String waitPolicyRef,
      String adapterBindingRef) {}

  public record StepView(
      String stepRef,
      int order,
      String state,
      java.time.Instant startedAt,
      java.time.Instant completedAt,
      Long durationMs,
      int attemptCount,
      List<AttemptView> attempts,
      String safeDisposition,
      String safeErrorCode) {}

  public record AttemptView(
      int attemptNumber,
      String state,
      String disposition,
      String safeErrorCode,
      java.time.Instant startedAt,
      java.time.Instant completedAt) {}

  public record WaitView(
      String waitState,
      java.time.Instant expiresAt,
      String signalDefinitionRef,
      String waitType) {}

  public record SignalView(
      String inboxState,
      java.time.Instant receivedAt,
      java.time.Instant appliedAt,
      String disposition) {}

  public record CallbackView(
      String outboxState, int attemptCount, String confirmationState, String nextAction) {}

  public record ReconciliationView(
      String reconciliationState, int queryCount, String nextAction) {}

  public record GovernanceView(
      String mode,
      String bundleRef,
      String snapshotSchemaVersion,
      Long activationSequence,
      java.time.Instant fixationAt,
      boolean historical) {}

  public record SecurityPostureView(
      String authentication,
      String authorization,
      String integrity,
      String replayProtection,
      String payloadAtRest,
      String dataExposure) {}
}
