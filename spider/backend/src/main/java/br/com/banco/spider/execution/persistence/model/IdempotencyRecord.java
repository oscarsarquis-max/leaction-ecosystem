package br.com.banco.spider.execution.persistence.model;

import br.com.banco.spider.execution.persistence.idempotency.IdempotencyRecordState;
import java.time.Instant;
import java.util.Objects;

public record IdempotencyRecord(
    String idempotencyRecordId,
    String scopeHash,
    String idempotencyKeyHash,
    String requestFingerprint,
    String fingerprintVersion,
    String executionId,
    IdempotencyRecordState state,
    String resultRef,
    Instant createdAt,
    Instant updatedAt,
    Instant expiresAt,
    long recordVersion) {

  public IdempotencyRecord {
    Objects.requireNonNull(idempotencyRecordId, "idempotencyRecordId");
    Objects.requireNonNull(scopeHash, "scopeHash");
    Objects.requireNonNull(idempotencyKeyHash, "idempotencyKeyHash");
    Objects.requireNonNull(requestFingerprint, "requestFingerprint");
    Objects.requireNonNull(fingerprintVersion, "fingerprintVersion");
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(state, "state");
    Objects.requireNonNull(createdAt, "createdAt");
    Objects.requireNonNull(updatedAt, "updatedAt");
    Objects.requireNonNull(expiresAt, "expiresAt");
  }
}
