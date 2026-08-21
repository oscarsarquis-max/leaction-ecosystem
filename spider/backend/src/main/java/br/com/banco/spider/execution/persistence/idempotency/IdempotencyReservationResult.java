package br.com.banco.spider.execution.persistence.idempotency;

import br.com.banco.spider.execution.domain.ExecutionState;
import java.util.Objects;

public record IdempotencyReservationResult(
    IdempotencyReservationStatus status,
    String existingExecutionId,
    ExecutionState existingState,
    String resultRef,
    String reasonCode) {

  public IdempotencyReservationResult {
    Objects.requireNonNull(status, "status");
    Objects.requireNonNull(reasonCode, "reasonCode");
  }

  public static IdempotencyReservationResult reservedNew(String executionId) {
    return new IdempotencyReservationResult(
        IdempotencyReservationStatus.RESERVED_NEW, executionId, null, null, "IDEMPOTENCY_RESERVED");
  }

  public static IdempotencyReservationResult notApplicable() {
    return new IdempotencyReservationResult(
        IdempotencyReservationStatus.NOT_APPLICABLE, null, null, null, "IDEMPOTENCY_SKIPPED");
  }

  public boolean isReuse() {
    return status == IdempotencyReservationStatus.IN_PROGRESS_SAME_REQUEST
        || status == IdempotencyReservationStatus.COMPLETED_SAME_REQUEST
        || status == IdempotencyReservationStatus.FAILED_SAME_REQUEST
        || status == IdempotencyReservationStatus.UNKNOWN_SAME_REQUEST;
  }

  public boolean isConflict() {
    return status == IdempotencyReservationStatus.CONFLICTING_REQUEST;
  }

  public boolean isNewReservation() {
    return status == IdempotencyReservationStatus.RESERVED_NEW;
  }
}
