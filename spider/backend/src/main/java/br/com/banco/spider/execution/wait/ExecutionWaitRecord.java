package br.com.banco.spider.execution.wait;

import java.time.Instant;
import java.util.Objects;

public record ExecutionWaitRecord(
    String waitId,
    String executionId,
    String stepId,
    String attemptId,
    WaitType waitType,
    String waitPolicyRef,
    String externalOperationRef,
    String expectedSignalContractRef,
    String expectedSourceRef,
    WaitState state,
    long stateVersion,
    Instant createdAt,
    Instant earliestResumeAt,
    Instant expiresAt,
    String receivedMessageId,
    Instant resolvedAt,
    String resolutionReasonCode,
    String signalDefinitionRef,
    String integrityProfileRef,
    String continuationTokenFingerprint,
    String continuationTokenFingerprintVersion,
    String continuationTokenKeyRef,
    String continuationTokenKeyVersion,
    Instant continuationTokenExpiresAt,
    String dataProtectionProfileRef) {

  public ExecutionWaitRecord {
    Objects.requireNonNull(waitId, "waitId");
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(stepId, "stepId");
    Objects.requireNonNull(attemptId, "attemptId");
    Objects.requireNonNull(waitType, "waitType");
    Objects.requireNonNull(waitPolicyRef, "waitPolicyRef");
    Objects.requireNonNull(state, "state");
    Objects.requireNonNull(createdAt, "createdAt");
    Objects.requireNonNull(expiresAt, "expiresAt");
  }

  /** Compat PROMPT-013. */
  public ExecutionWaitRecord(
      String waitId,
      String executionId,
      String stepId,
      String attemptId,
      WaitType waitType,
      String waitPolicyRef,
      String externalOperationRef,
      String expectedSignalContractRef,
      String expectedSourceRef,
      WaitState state,
      long stateVersion,
      Instant createdAt,
      Instant earliestResumeAt,
      Instant expiresAt,
      String receivedMessageId,
      Instant resolvedAt,
      String resolutionReasonCode,
      String signalDefinitionRef,
      String integrityProfileRef) {
    this(
        waitId,
        executionId,
        stepId,
        attemptId,
        waitType,
        waitPolicyRef,
        externalOperationRef,
        expectedSignalContractRef,
        expectedSourceRef,
        state,
        stateVersion,
        createdAt,
        earliestResumeAt,
        expiresAt,
        receivedMessageId,
        resolvedAt,
        resolutionReasonCode,
        signalDefinitionRef,
        integrityProfileRef,
        null,
        null,
        null,
        null,
        null,
        null);
  }

  /** Compat legado. */
  public ExecutionWaitRecord(
      String waitId,
      String executionId,
      String stepId,
      String attemptId,
      WaitType waitType,
      String waitPolicyRef,
      String externalOperationRef,
      String expectedSignalContractRef,
      String expectedSourceRef,
      WaitState state,
      long stateVersion,
      Instant createdAt,
      Instant earliestResumeAt,
      Instant expiresAt,
      String receivedMessageId,
      Instant resolvedAt,
      String resolutionReasonCode) {
    this(
        waitId,
        executionId,
        stepId,
        attemptId,
        waitType,
        waitPolicyRef,
        externalOperationRef,
        expectedSignalContractRef,
        expectedSourceRef,
        state,
        stateVersion,
        createdAt,
        earliestResumeAt,
        expiresAt,
        receivedMessageId,
        resolvedAt,
        resolutionReasonCode,
        null,
        null);
  }

  public ExecutionWaitRecord withState(
      WaitState newState,
      long newVersion,
      String receivedMessageId,
      Instant resolvedAt,
      String resolutionReasonCode) {
    return new ExecutionWaitRecord(
        waitId,
        executionId,
        stepId,
        attemptId,
        waitType,
        waitPolicyRef,
        externalOperationRef,
        expectedSignalContractRef,
        expectedSourceRef,
        newState,
        newVersion,
        createdAt,
        earliestResumeAt,
        expiresAt,
        receivedMessageId != null ? receivedMessageId : this.receivedMessageId,
        resolvedAt != null ? resolvedAt : this.resolvedAt,
        resolutionReasonCode != null ? resolutionReasonCode : this.resolutionReasonCode,
        signalDefinitionRef,
        integrityProfileRef,
        continuationTokenFingerprint,
        continuationTokenFingerprintVersion,
        continuationTokenKeyRef,
        continuationTokenKeyVersion,
        continuationTokenExpiresAt,
        dataProtectionProfileRef);
  }
}
