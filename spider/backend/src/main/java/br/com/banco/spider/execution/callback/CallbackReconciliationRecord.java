package br.com.banco.spider.execution.callback;

import java.time.Instant;
import java.util.Objects;

public record CallbackReconciliationRecord(
    String reconciliationId,
    String outboxId,
    String executionId,
    String deliveryKeyHash,
    String policyRef,
    CallbackReconciliationState state,
    int queryCount,
    Instant nextQueryAt,
    Instant startedAt,
    Instant expiresAt,
    CallbackDeliveryStatusDisposition lastDisposition,
    String externalDeliveryRef,
    String leaseOwner,
    Instant leaseUntil,
    long version,
    Instant createdAt,
    Instant updatedAt) {

  public CallbackReconciliationRecord {
    Objects.requireNonNull(reconciliationId, "reconciliationId");
    Objects.requireNonNull(outboxId, "outboxId");
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(deliveryKeyHash, "deliveryKeyHash");
    Objects.requireNonNull(policyRef, "policyRef");
    Objects.requireNonNull(state, "state");
    Objects.requireNonNull(nextQueryAt, "nextQueryAt");
    Objects.requireNonNull(startedAt, "startedAt");
    Objects.requireNonNull(expiresAt, "expiresAt");
    Objects.requireNonNull(createdAt, "createdAt");
    Objects.requireNonNull(updatedAt, "updatedAt");
  }
}
