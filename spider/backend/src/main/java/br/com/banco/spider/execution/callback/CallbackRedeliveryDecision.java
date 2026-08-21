package br.com.banco.spider.execution.callback;

public enum CallbackRedeliveryDecision {
  WAIT_AND_QUERY_AGAIN,
  REDISPATCH_ALLOWED,
  FINISH_CONFIRMED_ABSENT,
  MANUAL_REVIEW_REQUIRED,
  EXPIRE
}
