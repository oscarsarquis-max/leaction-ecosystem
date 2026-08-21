package br.com.banco.spider.execution.callback;

public enum CallbackDeliveryAttemptState {
  RUNNING,
  DELIVERED,
  FAILED,
  TIMED_OUT,
  UNKNOWN
}
