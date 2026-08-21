package br.com.banco.spider.execution.callback;

public enum CallbackConfirmationMode {
  SYNCHRONOUS_ACK_IS_FINAL,
  STATUS_QUERY_REQUIRED,
  STATUS_QUERY_WHEN_UNCERTAIN,
  NO_CONFIRMATION_AVAILABLE
}
