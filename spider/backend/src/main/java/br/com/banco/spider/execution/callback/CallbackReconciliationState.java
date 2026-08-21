package br.com.banco.spider.execution.callback;

public enum CallbackReconciliationState {
  PENDING,
  QUERYING,
  RETRY_SCHEDULED,
  CONFIRMED_DELIVERED,
  CONFIRMED_REJECTED,
  CONFIRMED_ABSENT,
  UNKNOWN,
  EXHAUSTED,
  EXPIRED,
  MANUAL_REVIEW
}
