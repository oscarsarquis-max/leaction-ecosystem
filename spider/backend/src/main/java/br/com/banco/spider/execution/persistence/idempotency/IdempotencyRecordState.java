package br.com.banco.spider.execution.persistence.idempotency;

/** Estados do registro de idempotência (persistidos como string). */
public enum IdempotencyRecordState {
  RESERVED,
  IN_PROGRESS,
  COMPLETED,
  FAILED_REUSABLE,
  UNKNOWN,
  EXPIRED,
  CONFLICT
}
