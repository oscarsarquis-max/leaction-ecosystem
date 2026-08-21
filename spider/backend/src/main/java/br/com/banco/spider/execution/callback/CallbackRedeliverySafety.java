package br.com.banco.spider.execution.callback;

public enum CallbackRedeliverySafety {
  IDEMPOTENT_BY_DELIVERY_KEY,
  QUERY_BEFORE_REDELIVERY,
  NEVER_AUTOMATIC
}
