package br.com.banco.spider.execution.domain;

/** Status técnico do outcome (separado de businessOutcome). */
public enum TechnicalStatus {
  SUCCESS,
  PARTIAL,
  FAILURE,
  PENDING,
  REJECTED
}
