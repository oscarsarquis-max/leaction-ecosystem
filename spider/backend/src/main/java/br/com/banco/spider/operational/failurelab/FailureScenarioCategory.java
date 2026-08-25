package br.com.banco.spider.operational.failurelab;

/** Conjunto fechado de categorias funcionais de cenário de falha. */
public enum FailureScenarioCategory {
  EXECUTION,
  RETRY,
  WAIT_RESUME,
  CALLBACK,
  SIGNAL,
  SECURITY,
  TELEMETRY,
  OPERATIONAL_HEALTH
}
