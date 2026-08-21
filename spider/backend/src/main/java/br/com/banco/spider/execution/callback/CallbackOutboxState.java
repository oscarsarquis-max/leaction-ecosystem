package br.com.banco.spider.execution.callback;

public enum CallbackOutboxState {
  PENDING,
  DISPATCHING,
  RETRY_SCHEDULED,
  DELIVERED,
  UNKNOWN,
  DEAD_LETTERED,
  EXPIRED,
  CANCELLED
}
