package br.com.banco.spider.integration.mock;

/** Cenários controlados do Mock Adapter — sem regra bancária. */
public enum MockAdapterScenario {
  SUCCESS,
  TECHNICAL_FAILURE,
  BUSINESS_NEGATIVE,
  TIMEOUT,
  INVALID_RESPONSE,
  UNKNOWN,
  ACCEPTED_ASYNC
}
