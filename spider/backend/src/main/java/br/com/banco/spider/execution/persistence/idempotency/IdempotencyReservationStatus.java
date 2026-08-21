package br.com.banco.spider.execution.persistence.idempotency;

/** Resultado tipado da reserva idempotente. */
public enum IdempotencyReservationStatus {
  RESERVED_NEW,
  IN_PROGRESS_SAME_REQUEST,
  COMPLETED_SAME_REQUEST,
  FAILED_SAME_REQUEST,
  UNKNOWN_SAME_REQUEST,
  CONFLICTING_REQUEST,
  EXPIRED_REUSABLE_KEY,
  NOT_APPLICABLE
}
