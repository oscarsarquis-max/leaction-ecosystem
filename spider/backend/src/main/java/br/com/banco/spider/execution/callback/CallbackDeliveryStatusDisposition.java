package br.com.banco.spider.execution.callback;

public enum CallbackDeliveryStatusDisposition {
  CONFIRMED_DELIVERED,
  ACCEPTED_NOT_FINAL,
  CONFIRMED_NOT_FOUND,
  CONFIRMED_REJECTED,
  RETRYABLE_QUERY_FAILURE,
  PERMANENT_QUERY_FAILURE,
  UNKNOWN
}
