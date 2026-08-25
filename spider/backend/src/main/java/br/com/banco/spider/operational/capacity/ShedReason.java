package br.com.banco.spider.operational.capacity;

/** Motivo fechado de descarte de carga. */
public enum ShedReason {
  BACKLOG_HARD_LIMIT,
  CONCURRENCY_EXHAUSTED,
  QUOTA_EXHAUSTED,
  CIRCUIT_OPEN
}
