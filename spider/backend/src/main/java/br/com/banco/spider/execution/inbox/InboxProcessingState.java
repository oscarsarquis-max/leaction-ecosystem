package br.com.banco.spider.execution.inbox;

public enum InboxProcessingState {
  PENDING,
  PROCESSING,
  PROCESSED,
  DUPLICATE,
  CONFLICT,
  LATE_REJECTED,
  ORPHANED,
  FAILED,
  /** Ingress verificado; aplicação ainda não iniciada. */
  APPLY_PENDING,
  APPLYING,
  APPLIED,
  MANUAL_REVIEW
}
