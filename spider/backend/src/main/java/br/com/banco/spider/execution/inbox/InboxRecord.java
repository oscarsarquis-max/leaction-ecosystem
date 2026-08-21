package br.com.banco.spider.execution.inbox;

import java.time.Instant;
import java.util.Objects;

public record InboxRecord(
    String messageId,
    String sourceRef,
    String bindingRef,
    String contractRef,
    String deduplicationKeyHash,
    String messageFingerprint,
    String fingerprintVersion,
    String executionId,
    String stepId,
    String externalOperationRef,
    Instant receivedAt,
    InboxValidationState validationState,
    InboxProcessingState processingState,
    String payloadRef,
    String errorCode,
    Instant expiresAt,
    String waitId,
    String signalDefinitionRef,
    String payloadDigest,
    int applicationAttemptCount,
    Instant nextAttemptAt,
    String leaseOwner,
    Instant leaseUntil,
    long version,
    Instant verifiedAt,
    Instant appliedAt) {

  public InboxRecord {
    Objects.requireNonNull(messageId, "messageId");
    Objects.requireNonNull(sourceRef, "sourceRef");
    Objects.requireNonNull(bindingRef, "bindingRef");
    Objects.requireNonNull(contractRef, "contractRef");
    Objects.requireNonNull(deduplicationKeyHash, "deduplicationKeyHash");
    Objects.requireNonNull(messageFingerprint, "messageFingerprint");
    Objects.requireNonNull(fingerprintVersion, "fingerprintVersion");
    Objects.requireNonNull(receivedAt, "receivedAt");
    Objects.requireNonNull(validationState, "validationState");
    Objects.requireNonNull(processingState, "processingState");
    Objects.requireNonNull(expiresAt, "expiresAt");
  }

  /** Construtor legado compatível (sem lease/aplicação). */
  public InboxRecord(
      String messageId,
      String sourceRef,
      String bindingRef,
      String contractRef,
      String deduplicationKeyHash,
      String messageFingerprint,
      String fingerprintVersion,
      String executionId,
      String stepId,
      String externalOperationRef,
      Instant receivedAt,
      InboxValidationState validationState,
      InboxProcessingState processingState,
      String payloadRef,
      String errorCode,
      Instant expiresAt) {
    this(
        messageId,
        sourceRef,
        bindingRef,
        contractRef,
        deduplicationKeyHash,
        messageFingerprint,
        fingerprintVersion,
        executionId,
        stepId,
        externalOperationRef,
        receivedAt,
        validationState,
        processingState,
        payloadRef,
        errorCode,
        expiresAt,
        null,
        null,
        null,
        0,
        null,
        null,
        null,
        0L,
        null,
        null);
  }

  public String logicalKey() {
    return sourceRef + "|" + messageId;
  }

  public InboxRecord withProcessing(
      InboxValidationState validationState,
      InboxProcessingState processingState,
      String payloadRef,
      String errorCode) {
    return new InboxRecord(
        messageId,
        sourceRef,
        bindingRef,
        contractRef,
        deduplicationKeyHash,
        messageFingerprint,
        fingerprintVersion,
        executionId,
        stepId,
        externalOperationRef,
        receivedAt,
        validationState != null ? validationState : this.validationState,
        processingState != null ? processingState : this.processingState,
        payloadRef != null ? payloadRef : this.payloadRef,
        errorCode != null ? errorCode : this.errorCode,
        expiresAt,
        waitId,
        signalDefinitionRef,
        payloadDigest,
        applicationAttemptCount,
        nextAttemptAt,
        leaseOwner,
        leaseUntil,
        version,
        verifiedAt,
        appliedAt);
  }
}
