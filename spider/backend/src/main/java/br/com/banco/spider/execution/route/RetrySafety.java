package br.com.banco.spider.execution.route;

/** Segurança de retry técnico do step. */
public enum RetrySafety {
  SAFE,
  SAFE_WITH_IDEMPOTENCY_KEY,
  UNSAFE
}
