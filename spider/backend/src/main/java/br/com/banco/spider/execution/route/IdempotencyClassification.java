package br.com.banco.spider.execution.route;

/** Classificação de idempotência do step. */
public enum IdempotencyClassification {
  REQUIRED,
  OPTIONAL,
  NOT_SUPPORTED
}
