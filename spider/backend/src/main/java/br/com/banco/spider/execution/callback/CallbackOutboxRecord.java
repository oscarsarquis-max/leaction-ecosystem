package br.com.banco.spider.execution.callback;

import java.time.Instant;
import java.util.Objects;

public record CallbackOutboxRecord(
    String outboxId,
    String logicalCallbackId,
    String executionId,
    String callbackDefinitionRef,
    String bindingRef,
    String contractRef,
    String securityProfileRef,
    String projectionRef,
    String resultRef,
    String logicalIdempotencyKeyHash,
    CallbackOutboxState state,
    Instant createdAt,
    Instant nextAttemptAt,
    Instant expiresAt,
    int attemptCount,
    long stateVersion,
    String lastErrorCode) {

  public CallbackOutboxRecord {
    Objects.requireNonNull(outboxId, "outboxId");
    Objects.requireNonNull(logicalCallbackId, "logicalCallbackId");
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(callbackDefinitionRef, "callbackDefinitionRef");
    Objects.requireNonNull(bindingRef, "bindingRef");
    Objects.requireNonNull(contractRef, "contractRef");
    Objects.requireNonNull(securityProfileRef, "securityProfileRef");
    Objects.requireNonNull(projectionRef, "projectionRef");
    Objects.requireNonNull(resultRef, "resultRef");
    Objects.requireNonNull(logicalIdempotencyKeyHash, "logicalIdempotencyKeyHash");
    Objects.requireNonNull(state, "state");
    Objects.requireNonNull(createdAt, "createdAt");
    Objects.requireNonNull(nextAttemptAt, "nextAttemptAt");
    Objects.requireNonNull(expiresAt, "expiresAt");
  }
}
